"""
Algoritmo de Conciliación Bancaria Ultra-Preciso

Implementa múltiples estrategias de conciliación con scoring inteligente
para lograr máxima precisión en la conciliación automática de movimientos
bancarios con CFDIs.
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.models.mysql_models import (
    ComprobanteFiscal, ComplementoPago, DocumentoRelacionadoPago, 
    EmpresaContribuyente
)
from .models import (
    MovimientoBancario, EstadoConciliacion, MetodoConciliacion,
    TipoMovimiento, ResultadoConciliacion
)
from .schemas import EstadisticasConciliacion, AlertaCritica, SugerenciaConciliacion
from .utils import (
    comparar_montos, esta_en_rango_fechas, calcular_similitud_texto,
    calcular_score_fecha, extraer_rfc_de_texto, extraer_folios_serie,
    normalizar_texto, limpiar_concepto_bancario
)
from .exceptions import ConciliacionError, DatosInsuficientesError

logger = logging.getLogger(__name__)


class ConciliadorAvanzado:
    """
    Conciliador bancario con múltiples estrategias y scoring inteligente
    
    Implementa 6 estrategias de conciliación:
    1. Match Exacto (confianza 0.95)
    2. Match por Referencia (confianza 0.9) 
    3. Match Aproximado (confianza 0.8)
    4. Complementos de Pago PPD (confianza 0.9)
    5. Heurística Combinada (confianza 0.85)
    6. Patrones ML (confianza 0.7)
    """
    
    def __init__(self, db: Session):
        """
        Inicializa el conciliador
        
        Args:
            db: Sesión de base de datos
        """
        self.db = db
        self.estadisticas = EstadisticasConciliacion()
        self.alertas_criticas: List[AlertaCritica] = []
        self.sugerencias: List[SugerenciaConciliacion] = []
        
        # Configuración de estrategias
        self.config = {
            "tolerancia_monto_default": Decimal('1.00'),
            "dias_tolerancia_default": 3,
            "score_minimo_confianza": 0.7,
            "max_sugerencias_por_movimiento": 3
        }
        
        # Cache para optimización
        self._cache_cfdis = {}
        self._cache_complementos = {}
        self._estadisticas_históricas = {}
    
    def conciliar_periodo(
        self, 
        empresa_id: int, 
        fecha_inicio: datetime, 
        fecha_fin: datetime,
        tolerancia_monto: Optional[Decimal] = None,
        dias_tolerancia: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Ejecuta conciliación completa para un período
        
        Args:
            empresa_id: ID de la empresa
            fecha_inicio: Inicio del período
            fecha_fin: Fin del período
            tolerancia_monto: Tolerancia para matching aproximado
            dias_tolerancia: Días de tolerancia para fechas
            
        Returns:
            Diccionario con resultados de conciliación
        """
        inicio_tiempo = datetime.now()
        
        try:
            logger.info(f"Iniciando conciliación para empresa {empresa_id}, período {fecha_inicio} - {fecha_fin}")
            
            # Configurar parámetros
            self.config["tolerancia_monto_default"] = tolerancia_monto or self.config["tolerancia_monto_default"]
            self.config["dias_tolerancia_default"] = dias_tolerancia or self.config["dias_tolerancia_default"]
            
            # 1. Precargar datos para optimización
            self._precargar_datos(empresa_id, fecha_inicio, fecha_fin)
            
            # 2. Obtener movimientos bancarios pendientes
            movimientos_pendientes = self._obtener_movimientos_pendientes(empresa_id, fecha_inicio, fecha_fin)
            self.estadisticas.total_movimientos_bancarios = len(movimientos_pendientes)
            
            if not movimientos_pendientes:
                raise DatosInsuficientesError("No hay movimientos bancarios pendientes en el período")
            
            # 3. Obtener CFDIs del período
            cfdis_periodo = self._obtener_cfdis_periodo(empresa_id, fecha_inicio, fecha_fin)
            self.estadisticas.total_cfdis_periodo = len(cfdis_periodo)
            
            if not cfdis_periodo:
                raise DatosInsuficientesError("No hay CFDIs en el período especificado")
            
            # 4. Ejecutar estrategias de conciliación
            self._ejecutar_estrategias_conciliacion(movimientos_pendientes, cfdis_periodo)
            
            # 5. Generar sugerencias para movimientos no conciliados
            self._generar_sugerencias_inteligentes(movimientos_pendientes, cfdis_periodo)
            
            # 6. Detectar alertas críticas
            self._detectar_alertas_criticas(movimientos_pendientes, cfdis_periodo)
            
            # 7. Calcular estadísticas finales
            self._calcular_estadisticas_finales(movimientos_pendientes)
            
            tiempo_total = (datetime.now() - inicio_tiempo).total_seconds()
            
            resultado = {
                "exito": True,
                "mensaje": f"Conciliación completada: {self.estadisticas.movimientos_conciliados} de {self.estadisticas.total_movimientos_bancarios} movimientos",
                "estadisticas": self.estadisticas,
                "alertas_criticas": self.alertas_criticas,
                "sugerencias": self.sugerencias,
                "tiempo_procesamiento_segundos": int(tiempo_total),
                "configuracion_utilizada": self.config
            }
            
            logger.info(f"Conciliación completada en {tiempo_total:.2f}s: {self.estadisticas.porcentaje_conciliacion:.2f}% éxito")
            return resultado
            
        except Exception as e:
            logger.error(f"Error en conciliación: {str(e)}")
            tiempo_total = (datetime.now() - inicio_tiempo).total_seconds()
            
            return {
                "exito": False,
                "mensaje": f"Error en conciliación: {str(e)}",
                "estadisticas": self.estadisticas,
                "alertas_criticas": self.alertas_criticas,
                "sugerencias": self.sugerencias,
                "tiempo_procesamiento_segundos": int(tiempo_total),
                "error": str(e)
            }
    
    def _precargar_datos(self, empresa_id: int, fecha_inicio: datetime, fecha_fin: datetime):
        """
        Precarga datos en caché para optimizar consultas
        """
        logger.debug("Precargando datos para optimización...")
        
        # Precargar CFDIs con joins para evitar consultas N+1
        cfdis = self.db.query(ComprobanteFiscal).filter(
            and_(
                ComprobanteFiscal.empresa_id == empresa_id,
                ComprobanteFiscal.fecha >= fecha_inicio,
                ComprobanteFiscal.fecha <= fecha_fin,
                ComprobanteFiscal.estatus_sat == True
            )
        ).all()
        
        self._cache_cfdis = {cfdi.uuid: cfdi for cfdi in cfdis}
        
        # Precargar complementos de pago
        complementos = self.db.query(ComplementoPago).join(ComprobanteFiscal).filter(
            and_(
                ComprobanteFiscal.empresa_id == empresa_id,
                ComprobanteFiscal.fecha >= fecha_inicio,
                ComprobanteFiscal.fecha <= fecha_fin,
                ComprobanteFiscal.tipo_comprobante == 'P'
            )
        ).all()
        
        self._cache_complementos = {comp.cfdi_id: comp for comp in complementos}
        
        logger.debug(f"Precargados: {len(cfdis)} CFDIs, {len(complementos)} complementos de pago")
    
    def _obtener_movimientos_pendientes(self, empresa_id: int, fecha_inicio: datetime, fecha_fin: datetime) -> List[MovimientoBancario]:
        """Obtiene movimientos bancarios pendientes de conciliación"""
        return self.db.query(MovimientoBancario).filter(
            and_(
                MovimientoBancario.empresa_id == empresa_id,
                MovimientoBancario.fecha >= fecha_inicio,
                MovimientoBancario.fecha <= fecha_fin,
                MovimientoBancario.estado == EstadoConciliacion.PENDIENTE
            )
        ).order_by(MovimientoBancario.fecha.desc()).all()
    
    def _obtener_cfdis_periodo(self, empresa_id: int, fecha_inicio: datetime, fecha_fin: datetime) -> List[ComprobanteFiscal]:
        """Obtiene CFDIs del período con rango extendido"""
        # Extender rango para capturar CFDIs relacionados
        fecha_inicio_ext = fecha_inicio - timedelta(days=30)
        fecha_fin_ext = fecha_fin + timedelta(days=30)
        
        return self.db.query(ComprobanteFiscal).filter(
            and_(
                ComprobanteFiscal.empresa_id == empresa_id,
                ComprobanteFiscal.fecha >= fecha_inicio_ext,
                ComprobanteFiscal.fecha <= fecha_fin_ext,
                ComprobanteFiscal.estatus_sat == True
            )
        ).order_by(ComprobanteFiscal.fecha.desc()).all()
    
    def _ejecutar_estrategias_conciliacion(self, movimientos: List[MovimientoBancario], cfdis: List[ComprobanteFiscal]):
        """
        Ejecuta todas las estrategias de conciliación en orden de precisión
        """
        logger.info("Ejecutando estrategias de conciliación...")
        
        # Estrategia 1: Match Exacto (máxima prioridad)
        self._estrategia_match_exacto(movimientos, cfdis)
        
        # Estrategia 2: Match por Referencia
        self._estrategia_match_referencia(movimientos, cfdis)
        
        # Estrategia 4: Complementos de Pago PPD (antes que aproximado por mayor precisión)
        self._estrategia_complementos_ppd(movimientos, cfdis)
        
        # Estrategia 3: Match Aproximado
        self._estrategia_match_aproximado(movimientos, cfdis)
        
        # Estrategia 5: Heurística Combinada
        self._estrategia_heuristica_combinada(movimientos, cfdis)
        
        # Estrategia 6: Patrones ML
        self._estrategia_patrones_ml(movimientos, cfdis)
    
    def _estrategia_match_exacto(self, movimientos: List[MovimientoBancario], cfdis: List[ComprobanteFiscal]):
        """
        ESTRATEGIA 1: Match exacto por monto y fecha ±3 días (confianza 0.95)
        """
        logger.debug("Ejecutando estrategia 1: Match Exacto")
        conciliados = 0
        
        for movimiento in movimientos:
            if movimiento.estado != EstadoConciliacion.PENDIENTE:
                continue
            
            for cfdi in cfdis:
                # Verificar si ya está conciliado
                if any(m.cfdi_uuid == cfdi.uuid for m in movimientos if m.estado == EstadoConciliacion.CONCILIADO):
                    continue
                
                # Match exacto de monto
                comparacion_monto = comparar_montos(movimiento.monto, cfdi.total, Decimal('0.00'))
                if not comparacion_monto["exacto"]:
                    continue
                
                # Match de fecha con tolerancia
                if not esta_en_rango_fechas(movimiento.fecha, cfdi.fecha, self.config["dias_tolerancia_default"]):
                    continue
                
                # Validar coherencia de tipo (cargo/abono vs ingreso/egreso)  
                if not self._validar_coherencia_tipo(movimiento, cfdi):
                    continue
                
                # MATCH ENCONTRADO
                self._conciliar_movimiento(
                    movimiento, 
                    cfdi, 
                    MetodoConciliacion.EXACTO, 
                    Decimal('0.95')
                )
                conciliados += 1
                logger.debug(f"Match exacto: Movimiento {movimiento.id} ↔ CFDI {cfdi.uuid}")
                break
        
        self.estadisticas.conciliados_exacto = conciliados
        logger.info(f"Estrategia Match Exacto: {conciliados} conciliaciones")
    
    def _estrategia_match_referencia(self, movimientos: List[MovimientoBancario], cfdis: List[ComprobanteFiscal]):
        """
        ESTRATEGIA 2: Match por UUID/folio/serie en referencia bancaria (confianza 0.9)
        """
        logger.debug("Ejecutando estrategia 2: Match por Referencia")
        conciliados = 0
        
        for movimiento in movimientos:
            if movimiento.estado != EstadoConciliacion.PENDIENTE:
                continue
            
            # Extraer posibles identificadores de la referencia y concepto
            texto_busqueda = f"{movimiento.referencia or ''} {movimiento.concepto}"
            
            # Buscar UUID completo
            if movimiento.referencia and len(movimiento.referencia) >= 36:
                uuid_posible = movimiento.referencia[-36:] if len(movimiento.referencia) >= 36 else movimiento.referencia
                cfdi_match = next((c for c in cfdis if c.uuid == uuid_posible), None)
                if cfdi_match:
                    score_fecha = calcular_score_fecha(movimiento.fecha, cfdi_match.fecha, 10)
                    if score_fecha >= 0.5:  # Tolerancia mayor para referencias
                        nivel_confianza = Decimal('0.9') * Decimal(str(score_fecha))
                        self._conciliar_movimiento(movimiento, cfdi_match, MetodoConciliacion.REFERENCIA, nivel_confianza)
                        conciliados += 1
                        continue
            
            # Buscar por folio/serie
            folios_series = extraer_folios_serie(texto_busqueda)
            mejor_match = None
            mejor_score = 0.0
            
            for cfdi in cfdis:
                score_total = 0.0
                matches = 0
                
                # Verificar folio
                if cfdi.folio_cfdi and folios_series["folios"]:
                    for folio in folios_series["folios"]:
                        if folio in cfdi.folio_cfdi:
                            score_total += 0.4
                            matches += 1
                
                # Verificar serie
                if cfdi.serie_cfdi and folios_series["series"]:
                    for serie in folios_series["series"]:
                        if serie in cfdi.serie_cfdi:
                            score_total += 0.3
                            matches += 1
                
                # Verificar similitud de concepto
                similitud_concepto = calcular_similitud_texto(
                    limpiar_concepto_bancario(movimiento.concepto),
                    f"{cfdi.nombre_emisor} {cfdi.nombre_receptor}"
                )
                score_total += similitud_concepto * 0.2
                
                # Score de fecha
                score_fecha = calcular_score_fecha(movimiento.fecha, cfdi.fecha, 15)
                score_total += score_fecha * 0.1
                
                if matches > 0 and score_total > mejor_score:
                    mejor_score = score_total
                    mejor_match = cfdi
            
            # Conciliar si hay un buen match
            if mejor_match and mejor_score >= 0.6:
                nivel_confianza = min(Decimal('0.9'), Decimal(str(mejor_score)))
                self._conciliar_movimiento(movimiento, mejor_match, MetodoConciliacion.REFERENCIA, nivel_confianza)
                conciliados += 1
        
        self.estadisticas.conciliados_referencia = conciliados
        logger.info(f"Estrategia Match Referencia: {conciliados} conciliaciones")
    
    def _estrategia_match_aproximado(self, movimientos: List[MovimientoBancario], cfdis: List[ComprobanteFiscal]):
        """
        ESTRATEGIA 3: Match aproximado con tolerancia configurable (confianza 0.8)
        """
        logger.debug("Ejecutando estrategia 3: Match Aproximado")
        conciliados = 0
        
        for movimiento in movimientos:
            if movimiento.estado != EstadoConciliacion.PENDIENTE:
                continue
            
            mejor_match = None
            mejor_score = 0.0
            
            for cfdi in cfdis:
                # Verificar si ya está conciliado
                if any(m.cfdi_uuid == cfdi.uuid for m in movimientos if m.estado == EstadoConciliacion.CONCILIADO):
                    continue
                
                # Comparar montos con tolerancia
                comparacion_monto = comparar_montos(
                    movimiento.monto, 
                    cfdi.total, 
                    self.config["tolerancia_monto_default"]
                )
                
                if not comparacion_monto["dentro_tolerancia"]:
                    continue
                
                # Verificar rango de fechas extendido
                if not esta_en_rango_fechas(movimiento.fecha, cfdi.fecha, 5):
                    continue
                
                # Calcular score combinado
                score_monto = 0.8 if comparacion_monto["exacto"] else 0.6
                score_fecha = calcular_score_fecha(movimiento.fecha, cfdi.fecha, 5)
                score_concepto = calcular_similitud_texto(
                    limpiar_concepto_bancario(movimiento.concepto),
                    f"{cfdi.nombre_emisor} {cfdi.nombre_receptor}"
                )
                
                score_total = (score_monto * 0.5) + (score_fecha * 0.3) + (score_concepto * 0.2)
                
                if score_total > mejor_score:
                    mejor_score = score_total
                    mejor_match = cfdi
            
            # Conciliar si supera el umbral
            if mejor_match and mejor_score >= 0.65:
                nivel_confianza = min(Decimal('0.8'), Decimal(str(mejor_score)))
                self._conciliar_movimiento(movimiento, mejor_match, MetodoConciliacion.APROXIMADO, nivel_confianza)
                conciliados += 1
        
        self.estadisticas.conciliados_aproximado = conciliados
        logger.info(f"Estrategia Match Aproximado: {conciliados} conciliaciones")
    
    def _estrategia_complementos_ppd(self, movimientos: List[MovimientoBancario], cfdis: List[ComprobanteFiscal]):
        """
        ESTRATEGIA 4: Complementos de Pago PPD - suma pagos parciales (confianza 0.9)
        """
        logger.debug("Ejecutando estrategia 4: Complementos PPD")
        conciliados = 0
        
        # Obtener CFDIs de pago (tipo P) del período
        cfdis_pago = [c for c in cfdis if c.tipo_comprobante == 'P']
        
        for movimiento in movimientos:
            if movimiento.estado != EstadoConciliacion.PENDIENTE:
                continue
            
            for cfdi_pago in cfdis_pago:
                # Obtener documentos relacionados del pago
                docs_relacionados = self.db.query(DocumentoRelacionadoPago).filter(
                    DocumentoRelacionadoPago.cfdi_id == cfdi_pago.id
                ).all()
                
                if not docs_relacionados:
                    continue
                
                # Sumar pagos parciales
                total_pagado = sum(doc.importe_pagado for doc in docs_relacionados if doc.importe_pagado)
                
                # Comparar con monto del movimiento
                comparacion = comparar_montos(movimiento.monto, total_pagado, self.config["tolerancia_monto_default"])
                
                if comparacion["dentro_tolerancia"]:
                    # Verificar fecha
                    score_fecha = calcular_score_fecha(movimiento.fecha, cfdi_pago.fecha, 7)
                    
                    if score_fecha >= 0.4:  # Más tolerante para PPD
                        nivel_confianza = Decimal('0.9') * Decimal(str(score_fecha))
                        if nivel_confianza >= Decimal('0.7'):
                            self._conciliar_movimiento(
                                movimiento, 
                                cfdi_pago, 
                                MetodoConciliacion.COMPLEMENTO_PPD, 
                                nivel_confianza
                            )
                            conciliados += 1
                            break
        
        self.estadisticas.conciliados_complemento_ppd = conciliados
        logger.info(f"Estrategia Complementos PPD: {conciliados} conciliaciones")
    
    def _estrategia_heuristica_combinada(self, movimientos: List[MovimientoBancario], cfdis: List[ComprobanteFiscal]):
        """
        ESTRATEGIA 5: Heurística combinada con scoring ponderado (confianza 0.85)
        """
        logger.debug("Ejecutando estrategia 5: Heurística Combinada")
        conciliados = 0
        
        for movimiento in movimientos:
            if movimiento.estado != EstadoConciliacion.PENDIENTE:
                continue
            
            mejor_match = None
            mejor_score = 0.0
            
            for cfdi in cfdis:
                if any(m.cfdi_uuid == cfdi.uuid for m in movimientos if m.estado == EstadoConciliacion.CONCILIADO):
                    continue
                
                # Scoring ponderado: monto (40%), fecha (30%), concepto (20%), patrón (10%)
                score_componentes = {}
                
                # 1. Score de monto (40%)
                comparacion_monto = comparar_montos(movimiento.monto, cfdi.total, self.config["tolerancia_monto_default"] * 2)
                if comparacion_monto["exacto"]:
                    score_componentes["monto"] = 1.0
                elif comparacion_monto["dentro_tolerancia"]:
                    score_componentes["monto"] = 0.7
                elif comparacion_monto["porcentaje_diferencia"] and comparacion_monto["porcentaje_diferencia"] < 5:
                    score_componentes["monto"] = 0.5
                else:
                    continue  # Skip si la diferencia es muy grande
                
                # 2. Score de fecha (30%)
                score_componentes["fecha"] = calcular_score_fecha(movimiento.fecha, cfdi.fecha, 10)
                
                # 3. Score de concepto (20%)
                concepto_limpio = limpiar_concepto_bancario(movimiento.concepto)
                nombres_cfdi = f"{cfdi.nombre_emisor} {cfdi.nombre_receptor}".lower()
                score_componentes["concepto"] = calcular_similitud_texto(concepto_limpio, nombres_cfdi)
                
                # 4. Score de patrón (10%) - buscar patrones recurrentes
                score_componentes["patron"] = self._calcular_score_patron(movimiento, cfdi)
                
                # Score total ponderado
                score_total = (
                    score_componentes["monto"] * 0.4 +
                    score_componentes["fecha"] * 0.3 +
                    score_componentes["concepto"] * 0.2 +
                    score_componentes["patron"] * 0.1
                )
                
                if score_total > mejor_score:
                    mejor_score = score_total
                    mejor_match = cfdi
            
            # Conciliar si supera umbral
            if mejor_match and mejor_score >= 0.75:
                nivel_confianza = min(Decimal('0.85'), Decimal(str(mejor_score)))
                self._conciliar_movimiento(movimiento, mejor_match, MetodoConciliacion.HEURISTICA, nivel_confianza)
                conciliados += 1
        
        self.estadisticas.conciliados_heuristica = conciliados
        logger.info(f"Estrategia Heurística Combinada: {conciliados} conciliaciones")
    
    def _estrategia_patrones_ml(self, movimientos: List[MovimientoBancario], cfdis: List[ComprobanteFiscal]):
        """
        ESTRATEGIA 6: Patrones ML basados en historial (confianza 0.7)
        """
        logger.debug("Ejecutando estrategia 6: Patrones ML")
        conciliados = 0
        
        # Analizar patrones históricos exitosos
        patrones_exitosos = self._analizar_patrones_historicos()
        
        for movimiento in movimientos:
            if movimiento.estado != EstadoConciliacion.PENDIENTE:
                continue
            
            mejor_match = None
            mejor_score = 0.0
            
            for cfdi in cfdis:
                if any(m.cfdi_uuid == cfdi.uuid for m in movimientos if m.estado == EstadoConciliacion.CONCILIADO):
                    continue
                
                # Buscar similitud con patrones exitosos
                score_patron = self._evaluar_patron_ml(movimiento, cfdi, patrones_exitosos)
                
                if score_patron > mejor_score:
                    mejor_score = score_patron
                    mejor_match = cfdi
            
            # Conciliar con umbral más bajo pero confianza menor
            if mejor_match and mejor_score >= 0.6:
                nivel_confianza = min(Decimal('0.7'), Decimal(str(mejor_score)))
                self._conciliar_movimiento(movimiento, mejor_match, MetodoConciliacion.ML_PATRON, nivel_confianza)
                conciliados += 1
        
        self.estadisticas.conciliados_ml_patron = conciliados
        logger.info(f"Estrategia Patrones ML: {conciliados} conciliaciones")
    
    # === MÉTODOS AUXILIARES ===
    
    def _conciliar_movimiento(self, movimiento: MovimientoBancario, cfdi: ComprobanteFiscal, 
                             metodo: MetodoConciliacion, nivel_confianza: Decimal):
        """
        Marca un movimiento como conciliado
        """
        movimiento.estado = EstadoConciliacion.CONCILIADO
        movimiento.cfdi_uuid = cfdi.uuid
        movimiento.metodo_conciliacion = metodo
        movimiento.nivel_confianza = nivel_confianza
        movimiento.fecha_conciliacion = datetime.now()
        
        self.db.commit()
        
        logger.debug(f"CONCILIADO: Mov {movimiento.id} ↔ CFDI {cfdi.uuid} ({metodo.value}, {nivel_confianza})")
    
    def _validar_coherencia_tipo(self, movimiento: MovimientoBancario, cfdi: ComprobanteFiscal) -> bool:
        """
        Valida coherencia entre tipo de movimiento y tipo de CFDI
        
        Lógica contable correcta:
        - ABONO (entrada de dinero) ↔ CFDI Ingreso ('I') - Tú vendes, recibes dinero
        - CARGO (salida de dinero) ↔ CFDI Egreso ('E') - Tú compras, pagas dinero  
        - Pagos ('P') pueden ser ambos según el contexto
        """
        
        if movimiento.tipo == TipoMovimiento.CARGO:
            # Cargos: salida de dinero - corresponde a gastos/pagos
            return cfdi.tipo_comprobante in ['E', 'P']  # Egreso, Pago
        elif movimiento.tipo == TipoMovimiento.ABONO:
            # Abonos: entrada de dinero - corresponde a ingresos/cobros  
            return cfdi.tipo_comprobante in ['I', 'P']  # Ingreso, Pago
        
        return True  # Si no se puede determinar, permitir
    
    def _calcular_score_patron(self, movimiento: MovimientoBancario, cfdi: ComprobanteFiscal) -> float:
        """
        Calcula score basado en patrones recurrentes
        """
        score = 0.0
        
        # Patrón 1: Mismo emisor/receptor recurrente
        concepto_normalizado = normalizar_texto(movimiento.concepto)
        if cfdi.nombre_emisor.lower() in concepto_normalizado:
            score += 0.3
        if cfdi.nombre_receptor.lower() in concepto_normalizado:
            score += 0.3
        
        # Patrón 2: RFCs en concepto
        rfcs_concepto = extraer_rfc_de_texto(movimiento.concepto)
        if cfdi.rfc_emisor in rfcs_concepto or cfdi.rfc_receptor in rfcs_concepto:
            score += 0.4
        
        return min(score, 1.0)
    
    def _analizar_patrones_historicos(self) -> Dict[str, Any]:
        """
        Analiza conciliaciones históricas exitosas para encontrar patrones
        """
        # Query para obtener conciliaciones exitosas de los últimos 6 meses
        fecha_limite = datetime.now() - timedelta(days=180)
        
        conciliaciones_exitosas = self.db.query(MovimientoBancario).filter(
            and_(
                MovimientoBancario.estado == EstadoConciliacion.CONCILIADO,
                MovimientoBancario.fecha_conciliacion >= fecha_limite,
                MovimientoBancario.nivel_confianza >= Decimal('0.8')
            )
        ).limit(1000).all()
        
        patrones = {
            "conceptos_comunes": {},
            "emisores_recurrentes": {},
            "patrones_monto": {},
            "patrones_fecha": {}
        }
        
        for mov in conciliaciones_exitosas:
            # Analizar conceptos
            concepto_limpio = limpiar_concepto_bancario(mov.concepto)
            palabras = concepto_limpio.split()[:3]  # Primeras 3 palabras
            clave_concepto = " ".join(palabras)
            patrones["conceptos_comunes"][clave_concepto] = patrones["conceptos_comunes"].get(clave_concepto, 0) + 1
        
        return patrones
    
    def _evaluar_patron_ml(self, movimiento: MovimientoBancario, cfdi: ComprobanteFiscal, 
                          patrones: Dict[str, Any]) -> float:
        """
        Evalúa similitud con patrones ML históricos
        """
        score = 0.0
        
        concepto_limpio = limpiar_concepto_bancario(movimiento.concepto)
        palabras = concepto_limpio.split()[:3]
        clave_concepto = " ".join(palabras)
        
        # Score basado en frecuencia de patrones similares
        if clave_concepto in patrones["conceptos_comunes"]:
            frecuencia = patrones["conceptos_comunes"][clave_concepto]
            score += min(frecuencia / 10.0, 0.5)  # Max 0.5 por frecuencia
        
        # Score por similitud de emisor/receptor
        if cfdi.nombre_emisor.lower() in concepto_limpio:
            score += 0.3
        
        return min(score, 1.0)
    
    def _generar_sugerencias_inteligentes(self, movimientos: List[MovimientoBancario], cfdis: List[ComprobanteFiscal]):
        """
        Genera sugerencias para movimientos no conciliados
        """
        logger.debug("Generando sugerencias inteligentes...")
        
        for movimiento in movimientos:
            if movimiento.estado != EstadoConciliacion.PENDIENTE:
                continue
            
            candidatos = []
            
            for cfdi in cfdis:
                if any(m.cfdi_uuid == cfdi.uuid for m in movimientos if m.estado == EstadoConciliacion.CONCILIADO):
                    continue
                
                # Calcular score de sugerencia
                score_sugerencia = self._calcular_score_sugerencia(movimiento, cfdi)
                
                if score_sugerencia >= 0.4:  # Umbral para sugerencias
                    candidatos.append({
                        "cfdi": cfdi,
                        "score": score_sugerencia,
                        "razon": self._generar_razon_sugerencia(movimiento, cfdi)
                    })
            
            # Ordenar por score y tomar mejores
            candidatos.sort(key=lambda x: x["score"], reverse=True)
            
            for candidato in candidatos[:self.config["max_sugerencias_por_movimiento"]]:
                sugerencia = SugerenciaConciliacion(
                    movimiento_id=movimiento.id,
                    cfdi_uuid=candidato["cfdi"].uuid,
                    nivel_confianza=Decimal(str(candidato["score"])),
                    razon=candidato["razon"],
                    datos_comparacion={
                        "monto_movimiento": float(movimiento.monto),
                        "monto_cfdi": float(candidato["cfdi"].total),
                        "fecha_movimiento": movimiento.fecha.isoformat(),
                        "fecha_cfdi": candidato["cfdi"].fecha.isoformat(),
                        "concepto_movimiento": movimiento.concepto[:100]
                    }
                )
                self.sugerencias.append(sugerencia)
    
    def _calcular_score_sugerencia(self, movimiento: MovimientoBancario, cfdi: ComprobanteFiscal) -> float:
        """Calcula score para sugerencias (más permisivo que conciliación)"""
        scores = []
        
        # Score de monto con mayor tolerancia
        comparacion = comparar_montos(movimiento.monto, cfdi.total, self.config["tolerancia_monto_default"] * 3)
        if comparacion["dentro_tolerancia"]:
            scores.append(0.8 if comparacion["exacto"] else 0.5)
        
        # Score de fecha con mayor tolerancia
        score_fecha = calcular_score_fecha(movimiento.fecha, cfdi.fecha, 15)
        scores.append(score_fecha * 0.6)
        
        # Score de concepto
        score_concepto = calcular_similitud_texto(
            limpiar_concepto_bancario(movimiento.concepto),
            f"{cfdi.nombre_emisor} {cfdi.nombre_receptor}"
        )
        scores.append(score_concepto * 0.4)
        
        return sum(scores) / len(scores) if scores else 0.0
    
    def _generar_razon_sugerencia(self, movimiento: MovimientoBancario, cfdi: ComprobanteFiscal) -> str:
        """Genera explicación de por qué se sugiere esta conciliación"""
        razones = []
        
        comparacion = comparar_montos(movimiento.monto, cfdi.total, self.config["tolerancia_monto_default"])
        if comparacion["exacto"]:
            razones.append("monto exacto")
        elif comparacion["dentro_tolerancia"]:
            razones.append(f"monto similar (diff: ${comparacion['diferencia']})")
        
        dias_diferencia = abs((movimiento.fecha - cfdi.fecha).days)
        if dias_diferencia <= 3:
            razones.append(f"fecha cercana ({dias_diferencia} días)")
        
        if cfdi.nombre_emisor.lower() in movimiento.concepto.lower():
            razones.append("emisor en concepto")
        
        return "; ".join(razones) if razones else "similitud general"
    
    def _detectar_alertas_criticas(self, movimientos: List[MovimientoBancario], cfdis: List[ComprobanteFiscal]):
        """
        Detecta alertas críticas en el proceso de conciliación
        """
        logger.debug("Detectando alertas críticas...")
        
        # Alerta 1: Movimientos grandes sin conciliar
        umbral_grande = Decimal('10000.00')
        movimientos_grandes = [m for m in movimientos 
                             if m.estado == EstadoConciliacion.PENDIENTE and m.monto >= umbral_grande]
        
        for mov in movimientos_grandes:
            self.alertas_criticas.append(AlertaCritica(
                tipo="MOVIMIENTO_GRANDE_PENDIENTE",
                mensaje=f"Movimiento de ${mov.monto:,.2f} sin conciliar del {mov.fecha.strftime('%d/%m/%Y')}",
                gravedad="alto",
                datos_adicionales={"movimiento_id": mov.id, "monto": float(mov.monto)}
            ))
        
        # Alerta 2: Baja tasa de conciliación
        if self.estadisticas.total_movimientos_bancarios > 0:
            tasa_conciliacion = self.estadisticas.movimientos_conciliados / self.estadisticas.total_movimientos_bancarios
            if tasa_conciliacion < 0.7:  # Menos del 70%
                self.alertas_criticas.append(AlertaCritica(
                    tipo="BAJA_TASA_CONCILIACION",
                    mensaje=f"Tasa de conciliación baja: {tasa_conciliacion:.1%}",
                    gravedad="medio",
                    datos_adicionales={"tasa_conciliacion": tasa_conciliacion}
                ))
        
        # Alerta 3: CFDIs sin movimientos bancarios correspondientes
        cfdis_sin_movimiento = []
        for cfdi in cfdis:
            if cfdi.total >= Decimal('1000.00'):  # Solo CFDIs significativos
                tiene_movimiento = any(m.cfdi_uuid == cfdi.uuid for m in movimientos)
                if not tiene_movimiento:
                    cfdis_sin_movimiento.append(cfdi)
        
        if len(cfdis_sin_movimiento) > len(cfdis) * 0.3:  # Más del 30%
            self.alertas_criticas.append(AlertaCritica(
                tipo="CFDIS_SIN_MOVIMIENTO",
                mensaje=f"{len(cfdis_sin_movimiento)} CFDIs sin movimiento bancario correspondiente",
                gravedad="medio",
                datos_adicionales={"cantidad": len(cfdis_sin_movimiento)}
            ))
    
    def _calcular_estadisticas_finales(self, movimientos: List[MovimientoBancario]):
        """
        Calcula estadísticas finales del proceso
        """
        # Contar por estado
        for mov in movimientos:
            if mov.estado == EstadoConciliacion.CONCILIADO:
                self.estadisticas.movimientos_conciliados += 1
                self.estadisticas.monto_total_conciliado += mov.monto
            elif mov.estado == EstadoConciliacion.PENDIENTE:
                self.estadisticas.movimientos_pendientes += 1
                self.estadisticas.monto_total_pendiente += mov.monto
            elif mov.estado == EstadoConciliacion.MANUAL:
                self.estadisticas.movimientos_manuales += 1
            elif mov.estado == EstadoConciliacion.DESCARTADO:
                self.estadisticas.movimientos_descartados += 1
        
        # Calcular porcentaje
        if self.estadisticas.total_movimientos_bancarios > 0:
            self.estadisticas.porcentaje_conciliacion = (
                self.estadisticas.movimientos_conciliados / 
                self.estadisticas.total_movimientos_bancarios * 100
            )
        
        # Calcular confianza promedio
        movimientos_conciliados = [m for m in movimientos if m.estado == EstadoConciliacion.CONCILIADO and m.nivel_confianza]
        if movimientos_conciliados:
            suma_confianzas = sum(m.nivel_confianza for m in movimientos_conciliados)
            self.estadisticas.nivel_confianza_promedio = suma_confianzas / len(movimientos_conciliados)
        
        logger.info(f"Estadísticas finales: {self.estadisticas.porcentaje_conciliacion:.2f}% conciliado") 