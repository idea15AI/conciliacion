"""
Conciliador Mejorado con FuzzyWuzzy
Implementa el enfoque de 3 pasos: exacto, fuzzy, manual
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from fuzzywuzzy import fuzz
from fuzzywuzzy import process

from app.models.mysql_models import ComprobanteFiscal, DocumentoRelacionadoPago, ComplementoPago
from app.conciliacion.models import MovimientoBancario, TipoMovimiento, EstadoConciliacion

logger = logging.getLogger(__name__)

class TipoConciliacion(Enum):
    EXACTA = "exacta"
    FUZZY = "fuzzy"
    PENDIENTE = "pendiente"
    REVISION_DUPLICADOS = "revision_duplicados"

@dataclass
class ResultadoConciliacion:
    movimiento_id: int
    cfdi_id: Optional[int]
    tipo_conciliacion: TipoConciliacion
    puntaje_fuzzy: Optional[float] = None
    razon: str = ""
    fecha_conciliacion: datetime = None

class ConciliadorMejorado:
    """
    Conciliador que implementa el enfoque de 3 pasos:
    1. Filtro Estricto: Coincidencia Exacta
    2. Filtro Flexible: Fuzzy Matching
    3. Clasificación para Revisión Manual
    """
    
    def __init__(self, db: Session, empresa_id: int, *, umbral_fuzzy: int = 90, incluir_ppd: bool = False, usar_solo_pue: bool = True, usar_fuzzy: bool = False):
        self.db = db
        self.empresa_id = empresa_id
        # Modo más estricto por defecto: umbral alto y sólo PUE
        self.umbral_fuzzy = umbral_fuzzy
        self.ventana_dias = 7   # Búsqueda ±7 días
        self.incluir_ppd = incluir_ppd
        self.usar_solo_pue = usar_solo_pue
        self.usar_fuzzy = usar_fuzzy
        # Evita asignar el mismo CFDI a múltiples movimientos
        self.cfdi_usados: Set[int] = set()
        # Para detectar movimientos duplicados
        self.movimientos_por_fecha_monto: Dict[Tuple[str, float], List[int]] = {}
        
    def conciliar_movimientos(self, movimientos: List[MovimientoBancario]) -> List[ResultadoConciliacion]:
        """
        Proceso principal de conciliación con 3 pasos
        """
        resultados = []
        
        for movimiento in movimientos:
            logger.info(f"🔍 Conciliando movimiento {movimiento.id}: {movimiento.concepto}")
            
            # Paso 1: Búsqueda Exacta
            resultado_exacto = self._buscar_coincidencia_exacta(movimiento)
            if resultado_exacto:
                resultados.append(resultado_exacto)
                continue
                
            # Paso 2 (opcional): Complementos de pago (PPD)
            if self.incluir_ppd:
                resultado_pago = self._buscar_complementos_pago(movimiento)
                if resultado_pago:
                    resultados.append(resultado_pago)
                    continue

            # Paso 3: Búsqueda Fuzzy (desactivado por defecto)
            if self.usar_fuzzy:
                resultado_fuzzy = self._buscar_coincidencia_fuzzy(movimiento)
                if resultado_fuzzy:
                    resultados.append(resultado_fuzzy)
                    continue
                
            # Paso 4: Marcar como Pendiente
            resultado_pendiente = ResultadoConciliacion(
                movimiento_id=movimiento.id,
                cfdi_id=None,
                tipo_conciliacion=TipoConciliacion.PENDIENTE,
                razon="No se encontró coincidencia automática",
                fecha_conciliacion=datetime.now()
            )
            resultados.append(resultado_pendiente)
        
        # Paso 5: Detectar y marcar movimientos duplicados para revisión
        self._detectar_movimientos_duplicados(resultados)

        # Paso 6: Marcar como revisión si existen múltiples CFDI del mismo monto en el mismo día
        self._marcar_cfdi_no_unico_por_dia(resultados)
        
        return resultados
    
    def _buscar_coincidencia_exacta(self, movimiento: MovimientoBancario) -> Optional[ResultadoConciliacion]:
        """
        Paso 1: Filtro Estricto - Coincidencia Exacta
        Busca CFDI con fecha y monto exactos
        """
        # 1) Mismo día (00:00-23:59)
        # Convertir date a datetime para poder usar replace con hora
        if hasattr(movimiento.fecha, 'date'):  # Es datetime
            day_start = movimiento.fecha.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1) - timedelta(microseconds=1)
        else:  # Es date
            day_start = datetime.combine(movimiento.fecha, datetime.min.time())
            day_end = datetime.combine(movimiento.fecha + timedelta(days=1), datetime.min.time())

        candidatos = self.db.query(ComprobanteFiscal).filter(
            and_(
                ComprobanteFiscal.empresa_id == self.empresa_id,
                ComprobanteFiscal.fecha.between(day_start, day_end),
                ComprobanteFiscal.estatus_sat == True
            )
        ).all()
        cfdis_validos = [c for c in self._filtrar_cfdis_validos(candidatos) if c.tipo_comprobante == 'I']
        cfdis_validos = [c for c in cfdis_validos if c.id not in self.cfdi_usados]

        # Filtrar por monto exacto (tolerancia 1 centavo)
        cfdis_monto = [c for c in cfdis_validos if abs(float(c.total) - float(movimiento.monto)) < 0.01]

        if cfdis_monto:
            elegido = self._seleccionar_cfdi_mas_cercano_por_fecha(movimiento.fecha, cfdis_monto)
            if elegido:
                self.cfdi_usados.add(elegido.id)
                receptor = f"; Receptor: {elegido.nombre_receptor}" if getattr(elegido, 'nombre_receptor', None) else ""
                return ResultadoConciliacion(
                    movimiento_id=movimiento.id,
                    cfdi_id=elegido.id,
                    tipo_conciliacion=TipoConciliacion.EXACTA,
                    razon=f"Exacta PUE en mismo día: CFDI {elegido.uuid} - Monto: ${elegido.total}{receptor}",
                    fecha_conciliacion=datetime.now()
                )

        # 2) Fallback ±1 día (estricto)
        # Asegurar que ambas fechas sean del mismo tipo
        if hasattr(movimiento.fecha, 'date'):  # Es datetime
            fecha_inicio = movimiento.fecha - timedelta(days=1)
            fecha_fin = movimiento.fecha + timedelta(days=1)
        else:  # Es date
            fecha_inicio = datetime.combine(movimiento.fecha - timedelta(days=1), datetime.min.time())
            fecha_fin = datetime.combine(movimiento.fecha + timedelta(days=1), datetime.min.time())
        candidatos2 = self.db.query(ComprobanteFiscal).filter(
            and_(
                ComprobanteFiscal.empresa_id == self.empresa_id,
                ComprobanteFiscal.fecha.between(fecha_inicio, fecha_fin),
                ComprobanteFiscal.estatus_sat == True
            )
        ).all()
        cfdis_validos2 = [c for c in self._filtrar_cfdis_validos(candidatos2) if c.tipo_comprobante == 'I']
        cfdis_validos2 = [c for c in cfdis_validos2 if c.id not in self.cfdi_usados]
        cfdis_monto2 = [c for c in cfdis_validos2 if abs(float(c.total) - float(movimiento.monto)) < 0.01]
        if cfdis_monto2:
            elegido = self._seleccionar_cfdi_mas_cercano_por_fecha(movimiento.fecha, cfdis_monto2)
            if elegido:
                self.cfdi_usados.add(elegido.id)
                receptor = f"; Receptor: {elegido.nombre_receptor}" if getattr(elegido, 'nombre_receptor', None) else ""
                return ResultadoConciliacion(
                    movimiento_id=movimiento.id,
                    cfdi_id=elegido.id,
                    tipo_conciliacion=TipoConciliacion.EXACTA,
                    razon=f"Exacta PUE ±1 día: CFDI {elegido.uuid} - Monto: ${elegido.total}{receptor}",
                    fecha_conciliacion=datetime.now()
                )
        
        return None
    
    def _filtrar_cfdis_validos(self, cfdis: List[ComprobanteFiscal]) -> List[ComprobanteFiscal]:
        """
        Filtra CFDIs válidos para conciliación:
        - Ignora CFDIs de PPD (pago en parcialidades o diferido)
        - Solo CFDIs tipo 'I' (Ingreso) con método de pago 'PUE'
        - O CFDIs tipo 'P' (Pago) electrónicos
        """
        cfdis_validos = []
        
        for cfdi in cfdis:
            # Método de pago
            if self.usar_solo_pue and cfdi.metodo_pago != 'PUE':
                continue
            if not self.usar_solo_pue and cfdi.metodo_pago == 'PPD':
                # si aceptamos todo excepto PPD
                continue

            # Tipos de comprobante válidos para conciliación directa: Ingreso (I)
            if cfdi.tipo_comprobante == 'I':
                cfdis_validos.append(cfdi)
            # Complementos de pago (P) solo si está habilitado
            elif cfdi.tipo_comprobante == 'P' and self.incluir_ppd:
                cfdis_validos.append(cfdi)
        
        return cfdis_validos
    
    def _buscar_coincidencia_fuzzy(self, movimiento: MovimientoBancario) -> Optional[ResultadoConciliacion]:
        """
        Paso 2: Filtro Flexible - Fuzzy Matching
        Usa FuzzyWuzzy para encontrar coincidencias probables
        """
        # Asegurar que ambas fechas sean del mismo tipo
        if hasattr(movimiento.fecha, 'date'):  # Es datetime
            fecha_inicio = movimiento.fecha - timedelta(days=self.ventana_dias)
            fecha_fin = movimiento.fecha + timedelta(days=self.ventana_dias)
        else:  # Es date
            fecha_inicio = datetime.combine(movimiento.fecha - timedelta(days=self.ventana_dias), datetime.min.time())
            fecha_fin = datetime.combine(movimiento.fecha + timedelta(days=self.ventana_dias), datetime.min.time())
        
        # Obtener CFDIs del período (filtrados ya por PUE si aplica)
        cfdis = self.db.query(ComprobanteFiscal).filter(
            and_(
                ComprobanteFiscal.empresa_id == self.empresa_id,
                ComprobanteFiscal.fecha.between(fecha_inicio, fecha_fin),
                ComprobanteFiscal.estatus_sat == True
            )
        ).all()
        
        # Filtrar CFDIs válidos
        cfdis_validos = [c for c in self._filtrar_cfdis_validos(cfdis) if c.id not in self.cfdi_usados]
        
        if not cfdis_validos:
            return None
        
        # Preparar textos para comparación
        texto_movimiento = self._normalizar_texto(movimiento.concepto)
        mejores_coincidencias = []
        
        for cfdi in cfdis_validos:
            # Comparar con diferentes campos del CFDI
            textos_cfdi = [
                cfdi.serie_cfdi or "",
                cfdi.folio_cfdi or "",
                cfdi.nombre_emisor or "",
                cfdi.nombre_receptor or "",
                cfdi.uuid or ""
            ]
            
            for texto_cfdi in textos_cfdi:
                if not texto_cfdi:
                    continue
                    
                texto_cfdi_norm = self._normalizar_texto(texto_cfdi)
                
                # Usar partial_ratio para subcadenas (mejor para referencias)
                puntaje = fuzz.partial_ratio(texto_movimiento, texto_cfdi_norm)
                
                if puntaje >= self.umbral_fuzzy:
                    mejores_coincidencias.append({
                        'cfdi': cfdi,
                        'puntaje': puntaje,
                        'texto_comparado': texto_cfdi_norm
                    })
        
        # Tomar la mejor coincidencia
        if mejores_coincidencias:
            # Si hay empate por puntaje, elegir por proximidad de fecha
            def calcular_distancia_fecha(cfdi):
                cfdi_fecha = getattr(cfdi['cfdi'], 'fecha_timbrado', None) or getattr(cfdi['cfdi'], 'fecha', None) or fecha_inicio
                # Normalizar ambas fechas a datetime para la comparación
                if hasattr(cfdi_fecha, 'date'):  # Es datetime
                    cfdi_dt = cfdi_fecha
                else:  # Es date
                    cfdi_dt = datetime.combine(cfdi_fecha, datetime.min.time())
                
                if hasattr(movimiento.fecha, 'date'):  # Es datetime
                    mov_dt = movimiento.fecha
                else:  # Es date
                    mov_dt = datetime.combine(movimiento.fecha, datetime.min.time())
                
                return abs(cfdi_dt - mov_dt)
            
            mejores_coincidencias.sort(key=lambda x: (
                -x['puntaje'],
                calcular_distancia_fecha(x)
            ))
            mejor = mejores_coincidencias[0]
            self.cfdi_usados.add(mejor['cfdi'].id)
            
            return ResultadoConciliacion(
                movimiento_id=movimiento.id,
                cfdi_id=mejor['cfdi'].id,
                tipo_conciliacion=TipoConciliacion.FUZZY,
                puntaje_fuzzy=mejor['puntaje'],
                razon=f"Fuzzy PUE: {mejor['puntaje']}% CFDI {mejor['cfdi'].uuid} - Texto: {mejor['texto_comparado']}" + (f"; Receptor: {mejor['cfdi'].nombre_receptor}" if getattr(mejor['cfdi'], 'nombre_receptor', None) else ""),
                fecha_conciliacion=datetime.now()
            )
        
        return None
    
    def _normalizar_texto(self, texto: str) -> str:
        """
        Normaliza texto para mejor comparación fuzzy
        """
        if not texto:
            return ""
        
        # Convertir a minúsculas
        texto = texto.lower()
        
        # Remover caracteres especiales comunes
        caracteres_especiales = ['-', '_', '.', ',', '(', ')', '[', ']']
        for char in caracteres_especiales:
            texto = texto.replace(char, ' ')
        
        # Remover espacios múltiples
        texto = ' '.join(texto.split())
        
        return texto
    
    def _buscar_complementos_pago(self, movimiento: MovimientoBancario) -> Optional[ResultadoConciliacion]:
        """
        Búsqueda especial para complementos de pago (PPD)
        """
        # Asegurar que ambas fechas sean del mismo tipo
        if hasattr(movimiento.fecha, 'date'):  # Es datetime
            fecha_inicio = movimiento.fecha - timedelta(days=self.ventana_dias)
            fecha_fin = movimiento.fecha + timedelta(days=self.ventana_dias)
        else:  # Es date
            fecha_inicio = datetime.combine(movimiento.fecha - timedelta(days=self.ventana_dias), datetime.min.time())
            fecha_fin = datetime.combine(movimiento.fecha + timedelta(days=self.ventana_dias), datetime.min.time())
        
        # Buscar complementos de pago
        complementos = self.db.query(ComplementoPago).join(ComprobanteFiscal).filter(
            and_(
                ComprobanteFiscal.empresa_id == self.empresa_id,
                ComprobanteFiscal.fecha.between(fecha_inicio, fecha_fin),
                ComprobanteFiscal.estatus_sat == True
            )
        ).all()
        
        for complemento in complementos:
            if abs(complemento.monto_pago - movimiento.monto) < 0.01:
                return ResultadoConciliacion(
                    movimiento_id=movimiento.id,
                    cfdi_id=complemento.cfdi_id,
                    tipo_conciliacion=TipoConciliacion.EXACTA,
                    razon=f"Complemento de pago (PPD): Monto ${complemento.monto_pago}",
                    fecha_conciliacion=datetime.now()
                )
        
        return None
    
    def generar_reporte(self, resultados: List[ResultadoConciliacion]) -> Dict:
        """
        Genera reporte de conciliación
        """
        total_movimientos = len(resultados)
        exactos = len([r for r in resultados if r.tipo_conciliacion == TipoConciliacion.EXACTA])
        fuzzy = len([r for r in resultados if r.tipo_conciliacion == TipoConciliacion.FUZZY])
        pendientes = len([r for r in resultados if r.tipo_conciliacion == TipoConciliacion.PENDIENTE])
        duplicados = len([r for r in resultados if r.tipo_conciliacion == TipoConciliacion.REVISION_DUPLICADOS])
        
        detalles = []
        for r in resultados:
            # Obtener datos del movimiento
            movimiento = self.db.query(MovimientoBancario).filter(
                MovimientoBancario.id == r.movimiento_id
            ).first()
            
            # Obtener datos del CFDI si existe
            cfdi_monto = None
            cfdi_total = None
            cfdi_receptor = None
            if r.cfdi_id:
                cfdi = self.db.query(ComprobanteFiscal).filter(
                    ComprobanteFiscal.id == r.cfdi_id
                ).first()
                if cfdi:
                    cfdi_monto = cfdi.total
                    cfdi_total = cfdi.total
                    cfdi_receptor = cfdi.nombre_receptor
            
            detalle = {
                'movimiento_id': r.movimiento_id,
                'cfdi_id': r.cfdi_id,
                'tipo': r.tipo_conciliacion.value,
                'puntaje_fuzzy': r.puntaje_fuzzy,
                'razon': r.razon,
                'fecha': movimiento.fecha.isoformat() if movimiento and hasattr(movimiento.fecha, 'isoformat') else str(movimiento.fecha) if movimiento else None,
                'concepto': movimiento.concepto if movimiento else None,
                'monto': float(movimiento.monto) if movimiento else 0,
                'cfdi_monto': float(cfdi_monto) if cfdi_monto else None,
                'cfdi_total': float(cfdi_total) if cfdi_total else None,
                'cfdi_receptor': cfdi_receptor
            }
            detalles.append(detalle)

        
        return {
            'resumen': {
                'total_movimientos': total_movimientos,
                'conciliados_exactos': exactos,
                'conciliados_fuzzy': fuzzy,
                'pendientes_revision': pendientes,
                'duplicados_revision': duplicados,
                'porcentaje_automatizado': ((exactos + fuzzy) / total_movimientos * 100) if total_movimientos > 0 else 0
            },
            'detalles': detalles
        } 

    def _seleccionar_cfdi_mas_cercano_por_fecha(self, fecha_mov, cfdis: List[ComprobanteFiscal]) -> Optional[ComprobanteFiscal]:
        if not cfdis:
            return None
        
        # Normalizar fecha_mov a datetime si es date
        if hasattr(fecha_mov, 'date'):  # Es datetime
            fecha_mov_dt = fecha_mov
        else:  # Es date
            fecha_mov_dt = datetime.combine(fecha_mov, datetime.min.time())
        
        # Orden por cercanía absoluta al movimiento, luego por fecha más antigua
        def cfdi_datetime(c):
            cfdi_fecha = getattr(c, 'fecha_timbrado', None) or getattr(c, 'fecha', None) or fecha_mov_dt
            # Normalizar CFDI fecha también
            if hasattr(cfdi_fecha, 'date'):  # Es datetime
                return cfdi_fecha
            else:  # Es date
                return datetime.combine(cfdi_fecha, datetime.min.time())
        
        cfdis_ordenados = sorted(cfdis, key=lambda c: (abs(cfdi_datetime(c) - fecha_mov_dt), cfdi_datetime(c)))
        return cfdis_ordenados[0]
    
    def _detectar_movimientos_duplicados(self, resultados: List[ResultadoConciliacion]) -> None:
        """
        Detecta movimientos con el mismo monto en la misma fecha y los marca para revisión
        """
        # Agrupar movimientos por fecha y monto
        movimientos_por_fecha_monto = {}
        
        for resultado in resultados:
            movimiento = self.db.query(MovimientoBancario).filter(
                MovimientoBancario.id == resultado.movimiento_id
            ).first()
            
            if movimiento:
                # Crear clave única: (fecha_exacta, monto) - solo mismo día exacto
                if hasattr(movimiento.fecha, 'date'):
                    fecha_exacta = movimiento.fecha.date()
                else:
                    fecha_exacta = movimiento.fecha
                monto = float(movimiento.monto)
                clave = (fecha_exacta, monto)
                
                if clave not in movimientos_por_fecha_monto:
                    movimientos_por_fecha_monto[clave] = []
                movimientos_por_fecha_monto[clave].append(resultado.movimiento_id)
        
        # Marcar como revisión los grupos con más de 1 movimiento
        for (fecha_exacta, monto), mov_ids in movimientos_por_fecha_monto.items():
            if len(mov_ids) > 1:
                fecha_str = fecha_exacta.strftime("%Y-%m-%d") if hasattr(fecha_exacta, 'strftime') else str(fecha_exacta)
                logger.info(f"🔍 Detectados {len(mov_ids)} movimientos duplicados: fecha {fecha_str}, monto ${monto}")
                
                # Ordenar por ID para mantener consistencia
                mov_ids_ordenados = sorted(mov_ids)
                
                # Marcar TODOS como revisión requerida cuando hay duplicados (mismo día, mismo monto)
                for mov_id in mov_ids_ordenados:
                    for resultado in resultados:
                        if resultado.movimiento_id == mov_id:
                            resultado.tipo_conciliacion = TipoConciliacion.REVISION_DUPLICADOS
                            resultado.razon = f"REVISIÓN REQUERIDA: {len(mov_ids)} movimientos con mismo monto ${monto} en {fecha_str}. Grupo: {', '.join(map(str, mov_ids_ordenados))}"
                            break

    def _marcar_cfdi_no_unico_por_dia(self, resultados: List[ResultadoConciliacion]) -> None:
        """
        Marca como revisión los resultados que usan un CFDI cuyo monto NO es único en ese día.
        La validación se hace por (fecha_del_cfdi, monto_redondeado_a_centavos).
        """
        if not resultados:
            return

        # Recolectar rango de fechas de movimientos para acotar consulta de CFDIs
        dias_movimientos = []
        for r in resultados:
            mov = self.db.query(MovimientoBancario).filter(MovimientoBancario.id == r.movimiento_id).first()
            if not mov or not mov.fecha:
                continue
            dia = mov.fecha.date() if hasattr(mov.fecha, 'date') else mov.fecha
            dias_movimientos.append(dia)
        if not dias_movimientos:
            return
        min_dia, max_dia = min(dias_movimientos), max(dias_movimientos)

        # Construir ventana [min_dia 00:00, max_dia 23:59]
        inicio = datetime.combine(min_dia, datetime.min.time())
        fin = datetime.combine(max_dia, datetime.max.time())

        # Obtener CFDIs del rango
        cfdi_query = self.db.query(ComprobanteFiscal).filter(
            and_(
                ComprobanteFiscal.empresa_id == self.empresa_id,
                ComprobanteFiscal.estatus_sat == True,
                ComprobanteFiscal.fecha.between(inicio, fin)
            )
        )
        # Restringir a PUE/Ingreso si corresponde
        if self.usar_solo_pue:
            cfdi_query = cfdi_query.filter(ComprobanteFiscal.tipo_comprobante == 'I', ComprobanteFiscal.metodo_pago == 'PUE')
        else:
            cfdi_query = cfdi_query.filter(ComprobanteFiscal.tipo_comprobante == 'I')

        cfdis_rango = cfdi_query.all()

        # Conteo por (día, monto)
        conteo_por_dia_monto = {}
        for c in cfdis_rango:
            f = getattr(c, 'fecha', None) or getattr(c, 'fecha_timbrado', None)
            if not f:
                continue
            dia_c = f.date() if hasattr(f, 'date') else f
            monto_c = round(float(c.total), 2) if getattr(c, 'total', None) is not None else None
            if monto_c is None:
                continue
            clave = (dia_c, monto_c)
            conteo_por_dia_monto[clave] = conteo_por_dia_monto.get(clave, 0) + 1

        if not conteo_por_dia_monto:
            return

        # Marcar resultados cuya pareja (día, monto) no sea única
        for r in resultados:
            if r.tipo_conciliacion != TipoConciliacion.EXACTA or not r.cfdi_id:
                continue
            cfdi = self.db.query(ComprobanteFiscal).filter(ComprobanteFiscal.id == r.cfdi_id).first()
            if not cfdi:
                continue
            f = getattr(cfdi, 'fecha', None) or getattr(cfdi, 'fecha_timbrado', None)
            if not f:
                continue
            dia_c = f.date() if hasattr(f, 'date') else f
            monto_c = round(float(cfdi.total), 2) if getattr(cfdi, 'total', None) is not None else None
            if monto_c is None:
                continue
            if conteo_por_dia_monto.get((dia_c, monto_c), 0) > 1:
                r.tipo_conciliacion = TipoConciliacion.REVISION_DUPLICADOS
                r.razon = f"REVISIÓN REQUERIDA: múltiples CFDIs con monto ${monto_c} en fecha {dia_c}. Validación estricta requiere monto único en el día."