"""
Conciliador Mejorado - Solo Conciliación Exacta
Implementa el enfoque de 2 pasos: exacto y manual
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.models.mysql_models import ComprobanteFiscal, DocumentoRelacionadoPago, ComplementoPago
from app.conciliacion.models import MovimientoBancario, TipoMovimiento, EstadoConciliacion

logger = logging.getLogger(__name__)

class TipoConciliacion(Enum):
    EXACTA = "exacta"
    PENDIENTE = "pendiente"
    REVISION_DUPLICADOS = "revision_duplicados"

@dataclass
class ResultadoConciliacion:
    movimiento_id: int
    cfdi_id: Optional[int]
    tipo_conciliacion: TipoConciliacion
    razon: str = ""
    fecha_conciliacion: datetime = None

class ConciliadorMejorado:
    """
    Conciliador que implementa el enfoque de 2 pasos:
    1. Filtro Estricto: Coincidencia Exacta (PUE y P)
    2. Clasificación para Revisión Manual
    """
    
    def __init__(self, db: Session, empresa_id: int, *, incluir_ppd: bool = False, usar_solo_pue: bool = True):
        self.db = db
        self.empresa_id = empresa_id
        self.ventana_dias = 7   # Búsqueda ±7 días
        self.incluir_ppd = incluir_ppd
        self.usar_solo_pue = usar_solo_pue
        # Evita asignar el mismo CFDI a múltiples movimientos
        self.cfdi_usados: Set[int] = set()
        # Para detectar movimientos duplicados
        self.movimientos_por_fecha_monto: Dict[Tuple[str, float], List[int]] = {}
        
    def conciliar_movimientos(self, movimientos: List[MovimientoBancario]) -> List[ResultadoConciliacion]:
        """
        Proceso principal de conciliación con 2 pasos
        """
        resultados = []
        
        for movimiento in movimientos:
            logger.info(f"🔍 Conciliando movimiento {movimiento.id}: {movimiento.concepto}")
            
            # Paso 1: Búsqueda Exacta (PUE y P, excluyendo PPD)
            resultado_exacto = self._buscar_coincidencia_exacta(movimiento)
            if resultado_exacto:
                resultados.append(resultado_exacto)
                continue
                
            # Paso 2: Marcar como Pendiente
            resultado_pendiente = ResultadoConciliacion(
                movimiento_id=movimiento.id,
                cfdi_id=None,
                tipo_conciliacion=TipoConciliacion.PENDIENTE,
                razon="No se encontró coincidencia automática",
                fecha_conciliacion=datetime.now()
            )
            resultados.append(resultado_pendiente)
        
        # Paso 3: Detectar y marcar movimientos duplicados para revisión
        self._detectar_movimientos_duplicados(resultados)

        # Paso 4: Marcar como revisión si existen múltiples CFDI del mismo monto en el mismo día
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
        cfdis_validos = [c for c in self._filtrar_cfdis_validos(candidatos) if c.tipo_comprobante in ['I', 'P']]
        cfdis_validos = [c for c in cfdis_validos if c.id not in self.cfdi_usados]

        # Filtrar por monto exacto (tolerancia 1 centavo)
        # Para tipo P usar monto_pago de complementos_pago, para tipo I usar total
        cfdis_monto = []
        for c in cfdis_validos:
            if c.tipo_comprobante == 'P':
                # Obtener monto de complemento de pago
                complemento = self.db.query(ComplementoPago).filter(
                    ComplementoPago.cfdi_id == c.id
                ).first()
                if complemento and complemento.monto_pago:
                    if abs(float(complemento.monto_pago) - float(movimiento.monto)) < 0.01:
                        cfdis_monto.append(c)
            else:  # tipo I
                if abs(float(c.total) - float(movimiento.monto)) < 0.01:
                    cfdis_monto.append(c)

        if cfdis_monto:
            elegido = self._seleccionar_cfdi_mas_cercano_por_fecha(movimiento.fecha, cfdis_monto)
            if elegido:
                self.cfdi_usados.add(elegido.id)
                receptor = f"; Receptor: {elegido.nombre_receptor}" if getattr(elegido, 'nombre_receptor', None) else ""
                tipo_cfdi = f"({elegido.tipo_comprobante}-{elegido.metodo_pago})"
                
                # Mostrar el monto correcto según el tipo
                monto_mostrar = elegido.total
                if elegido.tipo_comprobante == 'P':
                    complemento = self.db.query(ComplementoPago).filter(
                        ComplementoPago.cfdi_id == elegido.id
                    ).first()
                    if complemento and complemento.monto_pago:
                        monto_mostrar = complemento.monto_pago
                
                return ResultadoConciliacion(
                    movimiento_id=movimiento.id,
                    cfdi_id=elegido.id,
                    tipo_conciliacion=TipoConciliacion.EXACTA,
                    razon=f"Exacta {tipo_cfdi} en mismo día: CFDI {elegido.uuid} - Monto: ${monto_mostrar}{receptor}",
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
        cfdis_validos2 = [c for c in self._filtrar_cfdis_validos(candidatos2) if c.tipo_comprobante in ['I', 'P']]
        cfdis_validos2 = [c for c in cfdis_validos2 if c.id not in self.cfdi_usados]
        
        # Filtrar por monto exacto (tolerancia 1 centavo)
        # Para tipo P usar monto_pago de complementos_pago, para tipo I usar total
        cfdis_monto2 = []
        for c in cfdis_validos2:
            if c.tipo_comprobante == 'P':
                # Obtener monto de complemento de pago
                complemento = self.db.query(ComplementoPago).filter(
                    ComplementoPago.cfdi_id == c.id
                ).first()
                if complemento and complemento.monto_pago:
                    if abs(float(complemento.monto_pago) - float(movimiento.monto)) < 0.01:
                        cfdis_monto2.append(c)
            else:  # tipo I
                if abs(float(c.total) - float(movimiento.monto)) < 0.01:
                    cfdis_monto2.append(c)
        if cfdis_monto2:
            elegido = self._seleccionar_cfdi_mas_cercano_por_fecha(movimiento.fecha, cfdis_monto2)
            if elegido:
                self.cfdi_usados.add(elegido.id)
                receptor = f"; Receptor: {elegido.nombre_receptor}" if getattr(elegido, 'nombre_receptor', None) else ""
                tipo_cfdi = f"({elegido.tipo_comprobante}-{elegido.metodo_pago})"
                
                # Mostrar el monto correcto según el tipo
                monto_mostrar = elegido.total
                if elegido.tipo_comprobante == 'P':
                    complemento = self.db.query(ComplementoPago).filter(
                        ComplementoPago.cfdi_id == elegido.id
                    ).first()
                    if complemento and complemento.monto_pago:
                        monto_mostrar = complemento.monto_pago
                
                return ResultadoConciliacion(
                    movimiento_id=movimiento.id,
                    cfdi_id=elegido.id,
                    tipo_conciliacion=TipoConciliacion.EXACTA,
                    razon=f"Exacta {tipo_cfdi} ±1 día: CFDI {elegido.uuid} - Monto: ${monto_mostrar}{receptor}",
                    fecha_conciliacion=datetime.now()
                )
        
        return None
    
    def _filtrar_cfdis_validos(self, cfdis: List[ComprobanteFiscal]) -> List[ComprobanteFiscal]:
        """
        Filtra CFDIs válidos para conciliación:
        - Permite CFDIs tipo 'I' (Ingreso) con método de pago 'PUE'
        - Permite CFDIs tipo 'P' (Pago) 
        - Excluye CFDIs con método de pago 'PPD'
        """
        cfdis_validos = []
        
        for cfdi in cfdis:
            # Excluir PPD (pago en parcialidades o diferido)
            if cfdi.metodo_pago == 'PPD':
                continue

            # Tipos de comprobante válidos para conciliación directa: Ingreso (I) y Pago (P)
            if cfdi.tipo_comprobante == 'I':
                cfdis_validos.append(cfdi)
            elif cfdi.tipo_comprobante == 'P':
                cfdis_validos.append(cfdi)
        
        return cfdis_validos
    
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
                'pendientes_revision': pendientes,
                'duplicados_revision': duplicados,
                'porcentaje_automatizado': ((exactos) / total_movimientos * 100) if total_movimientos > 0 else 0
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
        Marca como revisión los resultados cuando NO hay unicidad entre movimientos y CFDIs.
        La lógica es: 1 movimiento + 1 CFDI del mismo monto en la misma fecha = EXACTA
        Múltiples movimientos o múltiples CFDIs del mismo monto en la misma fecha = REVISIÓN
        """
        if not resultados:
            return

        # Recolectar rango de fechas de movimientos para acotar consulta
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
        cfdi_query = cfdi_query.filter(
            and_(
                ComprobanteFiscal.tipo_comprobante.in_(['I', 'P']),
                or_(
                    ComprobanteFiscal.metodo_pago != 'PPD',
                    ComprobanteFiscal.metodo_pago.is_(None)
                )
            )
        )
        cfdis_rango = cfdi_query.all()

        # Obtener movimientos del rango
        movimientos_query = self.db.query(MovimientoBancario).filter(
            and_(
                MovimientoBancario.empresa_id == self.empresa_id,
                MovimientoBancario.fecha.between(inicio, fin)
            )
        )
        movimientos_rango = movimientos_query.all()

        # Conteo de CFDIs por (día, monto)
        conteo_cfdis_por_dia_monto = {}
        for c in cfdis_rango:
            f = getattr(c, 'fecha', None) or getattr(c, 'fecha_timbrado', None)
            if not f:
                continue
            dia_c = f.date() if hasattr(f, 'date') else f
            
            # Para tipo P usar monto_pago, para tipo I usar total
            if c.tipo_comprobante == 'P':
                complemento = self.db.query(ComplementoPago).filter(
                    ComplementoPago.cfdi_id == c.id
                ).first()
                if complemento and complemento.monto_pago:
                    monto_c = round(float(complemento.monto_pago), 2)
                else:
                    continue
            else:
                monto_c = round(float(c.total), 2) if getattr(c, 'total', None) is not None else None
                if monto_c is None:
                    continue
            
            clave = (dia_c, monto_c)
            conteo_cfdis_por_dia_monto[clave] = conteo_cfdis_por_dia_monto.get(clave, 0) + 1

        # Conteo de movimientos por (día, monto)
        conteo_movs_por_dia_monto = {}
        for m in movimientos_rango:
            if not m.fecha or not m.monto:
                continue
            dia_m = m.fecha.date() if hasattr(m.fecha, 'date') else m.fecha
            monto_m = round(float(m.monto), 2)
            clave = (dia_m, monto_m)
            conteo_movs_por_dia_monto[clave] = conteo_movs_por_dia_monto.get(clave, 0) + 1

        # Marcar resultados según la lógica de unicidad
        for r in resultados:
            if r.tipo_conciliacion != TipoConciliacion.EXACTA or not r.cfdi_id:
                continue
            
            # Obtener datos del movimiento y CFDI
            mov = self.db.query(MovimientoBancario).filter(MovimientoBancario.id == r.movimiento_id).first()
            cfdi = self.db.query(ComprobanteFiscal).filter(ComprobanteFiscal.id == r.cfdi_id).first()
            if not mov or not cfdi:
                continue
            
            # Obtener fecha y monto del movimiento
            dia_mov = mov.fecha.date() if hasattr(mov.fecha, 'date') else mov.fecha
            monto_mov = round(float(mov.monto), 2)
            
            # Obtener fecha y monto del CFDI
            f_cfdi = getattr(cfdi, 'fecha', None) or getattr(cfdi, 'fecha_timbrado', None)
            if not f_cfdi:
                continue
            dia_cfdi = f_cfdi.date() if hasattr(f_cfdi, 'date') else f_cfdi
            
            # Para tipo P usar monto_pago, para tipo I usar total
            if cfdi.tipo_comprobante == 'P':
                complemento = self.db.query(ComplementoPago).filter(
                    ComplementoPago.cfdi_id == cfdi.id
                ).first()
                if complemento and complemento.monto_pago:
                    monto_cfdi = round(float(complemento.monto_pago), 2)
                else:
                    continue
            else:
                monto_cfdi = round(float(cfdi.total), 2) if getattr(cfdi, 'total', None) is not None else None
                if monto_cfdi is None:
                    continue
            
            # Verificar unicidad
            clave_mov = (dia_mov, monto_mov)
            clave_cfdi = (dia_cfdi, monto_cfdi)
            
            count_movs = conteo_movs_por_dia_monto.get(clave_mov, 0)
            count_cfdis = conteo_cfdis_por_dia_monto.get(clave_cfdi, 0)
            
            # Si hay múltiples movimientos o múltiples CFDIs del mismo monto en la misma fecha, marcar como revisión
            if count_movs > 1 or count_cfdis > 1:
                r.tipo_conciliacion = TipoConciliacion.REVISION_DUPLICADOS
                if count_movs > 1 and count_cfdis > 1:
                    r.razon = f"REVISIÓN REQUERIDA: {count_movs} movimientos y {count_cfdis} CFDIs con monto ${monto_mov} en fecha {dia_mov}. Validación requiere unicidad."
                elif count_movs > 1:
                    r.razon = f"REVISIÓN REQUERIDA: {count_movs} movimientos con monto ${monto_mov} en fecha {dia_mov}. Validación requiere unicidad."
                else:
                    r.razon = f"REVISIÓN REQUERIDA: {count_cfdis} CFDIs con monto ${monto_cfdi} en fecha {dia_cfdi}. Validación requiere unicidad."