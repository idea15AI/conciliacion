"""
Router para Conciliación Exacta con CFDIs PUE y P
"""

import logging
from typing import List, Dict
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.core.database import get_db
from app.conciliacion.models import MovimientoBancario, EstadoConciliacion
from app.conciliacion.conciliador import ConciliadorMejorado, TipoConciliacion
from app.models.mysql_models import ComprobanteFiscal, EmpresaContribuyente, ComplementoPago

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conciliacion", tags=["Conciliación"])
@router.get("/empresas")
async def listar_empresas(db: Session = Depends(get_db)):
    """
    Devuelve la lista de empresas contribuyentes disponibles para seleccionar en el frontend.
    """
    empresas = db.query(EmpresaContribuyente).order_by(EmpresaContribuyente.razon_social.asc()).all()
    return [
        {
            "id": e.id,
            "rfc": e.rfc,
            "razon_social": e.razon_social,
        }
        for e in empresas
    ]

@router.post("/ejecutar/{empresa_id}")
async def ejecutar_conciliacion_mejorada(
    empresa_id: int,
    fecha_inicio: str = None,
    fecha_fin: str = None,
    solo_pue: bool = True,
    incluir_ppd: bool = False,
    db: Session = Depends(get_db)
):
    """
    Ejecuta conciliación exacta con CFDIs PUE y P
    
    Parámetros:
    - empresa_id: ID de la empresa
    - fecha_inicio: Fecha inicio (YYYY-MM-DD) - opcional
    - fecha_fin: Fecha fin (YYYY-MM-DD) - opcional  
    - solo_pue: Filtro para solo PUE (incluye P siempre)
    - incluir_ppd: Incluir complementos de pago PPD
    """
    try:
        # Validar empresa por catálogo principal, no por existencia de CFDI
        empresa = db.query(EmpresaContribuyente).filter(
            EmpresaContribuyente.id == empresa_id
        ).first()
        if not empresa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Empresa {empresa_id} no encontrada"
            )
        
        # Obtener movimientos bancarios
        query = db.query(MovimientoBancario).filter(
            MovimientoBancario.empresa_id == empresa_id
        )
        
        # Aplicar filtros de fecha si se proporcionan
        if fecha_inicio:
            fecha_inicio_dt = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
            query = query.filter(MovimientoBancario.fecha >= fecha_inicio_dt)
            
        if fecha_fin:
            fecha_fin_dt = datetime.strptime(fecha_fin, "%Y-%m-%d").date()
            query = query.filter(MovimientoBancario.fecha <= fecha_fin_dt)
        
        movimientos = query.all()
        
        if not movimientos:
            return {
                "mensaje": "No se encontraron movimientos bancarios para conciliar",
                "empresa_id": empresa_id,
                "total_movimientos": 0
            }
        
        # Crear conciliador
        conciliador = ConciliadorMejorado(
            db,
            empresa_id,
            incluir_ppd=incluir_ppd,
            usar_solo_pue=solo_pue
        )
        
        # Ejecutar conciliación
        logger.info(f"🚀 Iniciando conciliación para empresa {empresa_id} con {len(movimientos)} movimientos")
        
        resultados = conciliador.conciliar_movimientos(movimientos)
        reporte = conciliador.generar_reporte(resultados)
        
        # Actualizar estado de movimientos en BD
        for resultado in resultados:
            movimiento = db.query(MovimientoBancario).filter(
                MovimientoBancario.id == resultado.movimiento_id
            ).first()
            
            if movimiento:
                if resultado.tipo_conciliacion == TipoConciliacion.EXACTA:
                    # Mapear resultado a cfdi_uuid y actualizar estado/fecha
                    cfdi = db.query(ComprobanteFiscal).filter(ComprobanteFiscal.id == resultado.cfdi_id).first() if resultado.cfdi_id else None
                    if cfdi and cfdi.uuid:
                        movimiento.cfdi_uuid = cfdi.uuid
                    movimiento.estado = EstadoConciliacion.CONCILIADO
                    movimiento.fecha_conciliacion = datetime.now()
                else:
                    movimiento.estado = EstadoConciliacion.PENDIENTE
        
        db.commit()
        
        logger.info(f"✅ Conciliación completada: {reporte['resumen']['conciliados_exactos']} exactos, {reporte['resumen']['pendientes_revision']} pendientes")
        
        return {
            "mensaje": "Conciliación ejecutada exitosamente",
            "empresa_id": empresa_id,
            "fecha_ejecucion": datetime.now().isoformat(),
            "solo_pue": solo_pue,
            "incluir_ppd": incluir_ppd,
            **reporte
        }
        
    except Exception as e:
        logger.error(f"❌ Error en conciliación: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error ejecutando conciliación: {str(e)}"
        )

@router.get("/reporte/{empresa_id}")
async def obtener_reporte_conciliacion(
    empresa_id: int,
    fecha_inicio: str = None,
    fecha_fin: str = None,
    db: Session = Depends(get_db)
):
    """
    Obtiene reporte de conciliación por empresa
    """
    try:
        # Construir query base
        query = db.query(MovimientoBancario).filter(
            MovimientoBancario.empresa_id == empresa_id
        )
        
        # Aplicar filtros de fecha (usar date, no datetime)
        if fecha_inicio:
            fecha_inicio_d = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
            query = query.filter(MovimientoBancario.fecha >= fecha_inicio_d)
            
        if fecha_fin:
            fecha_fin_d = datetime.strptime(fecha_fin, "%Y-%m-%d").date()
            query = query.filter(MovimientoBancario.fecha <= fecha_fin_d)
        
        movimientos = query.all()
        
        # Contar por estado
        estados = {}
        for movimiento in movimientos:
            estado = movimiento.estado.value if movimiento.estado else "PENDIENTE"
            estados[estado] = estados.get(estado, 0) + 1
        
        return {
            "empresa_id": empresa_id,
            "total_movimientos": len(movimientos),
            "estados": estados,
            "fecha_reporte": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo reporte: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo reporte: {str(e)}"
        )

@router.get("/movimientos-pendientes/{empresa_id}")
async def obtener_movimientos_pendientes(
    empresa_id: int,
    db: Session = Depends(get_db)
):
    """
    Obtiene movimientos pendientes de conciliación
    """
    try:
        movimientos = db.query(MovimientoBancario).filter(
            and_(
                MovimientoBancario.empresa_id == empresa_id,
                MovimientoBancario.estado == EstadoConciliacion.PENDIENTE
            )
        ).all()
        
        return {
            "empresa_id": empresa_id,
            "total_pendientes": len(movimientos),
            "movimientos": [
                {
                    "id": m.id,
                    "fecha": m.fecha.isoformat(),
                    "concepto": m.concepto,
                    "monto": float(m.monto),
                    "tipo": m.tipo.value if m.tipo else None,
                    "referencia": m.referencia
                }
                for m in movimientos
            ]
        }
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo movimientos pendientes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo movimientos pendientes: {str(e)}"
        ) 

@router.get("/detalles/{empresa_id}")
async def obtener_detalles_conciliacion(
    empresa_id: int,
    fecha_inicio: str = None,
    fecha_fin: str = None,
    db: Session = Depends(get_db)
):
    """
    Obtiene detalles de conciliación con montos de CFDI
    """
    try:
        # Construir query base
        query = db.query(MovimientoBancario).filter(
            MovimientoBancario.empresa_id == empresa_id
        )
        
        # Aplicar filtros de fecha
        if fecha_inicio:
            fecha_inicio_dt = datetime.strptime(fecha_inicio, "%Y-%m-%d")
            query = query.filter(MovimientoBancario.fecha >= fecha_inicio_dt)
            
        if fecha_fin:
            fecha_fin_dt = datetime.strptime(fecha_fin, "%Y-%m-%d")
            query = query.filter(MovimientoBancario.fecha <= fecha_fin_dt)
        
        movimientos = query.all()
        
        detalles = []
        for movimiento in movimientos:
            # Obtener datos del CFDI si existe
            cfdi_monto = None
            cfdi_total = None
            cfdi_id = None
            
            if movimiento.comprobante_fiscal_id:
                cfdi = db.query(ComprobanteFiscal).filter(
                    ComprobanteFiscal.id == movimiento.comprobante_fiscal_id
                ).first()
                if cfdi:
                    cfdi_monto = cfdi.total
                    cfdi_total = cfdi.total
                    cfdi_id = cfdi.id
            
            detalle = {
                'movimiento_id': movimiento.id,
                'cfdi_id': cfdi_id,
                'tipo': movimiento.estado.value if movimiento.estado else 'pendiente',
                'razon': f"Estado: {movimiento.estado.value if movimiento.estado else 'PENDIENTE'}",
                'fecha': movimiento.fecha.isoformat() if movimiento.fecha else None,
                'concepto': movimiento.concepto if movimiento.concepto else None,
                'monto': float(movimiento.monto) if movimiento.monto else 0,
                'cfdi_monto': float(cfdi_monto) if cfdi_monto else None,
                'cfdi_total': float(cfdi_total) if cfdi_monto else None
            }
            detalles.append(detalle)
        
        return {
            "empresa_id": empresa_id,
            "total_movimientos": len(movimientos),
            "detalles": detalles,
            "fecha_reporte": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo detalles: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo detalles: {str(e)}"
        ) 

@router.get("/montos/{empresa_id}")
async def obtener_montos_por_rango(
    empresa_id: int,
    fecha_inicio: str = None,
    fecha_fin: str = None,
    solo_pue: bool = True,
    db: Session = Depends(get_db)
):
    """
    Devuelve montos agregados dentro del rango de fechas con conteos de CFDIs y Movimientos.
    Estructura por fila: { monto, cfdi_count, movimientos_count }
    """
    try:
        # Rango de fechas
        fecha_inicio_dt = datetime.strptime(fecha_inicio, "%Y-%m-%d").date() if fecha_inicio else None
        fecha_fin_dt = datetime.strptime(fecha_fin, "%Y-%m-%d").date() if fecha_fin else None

        # Movimientos
        q_mov = db.query(MovimientoBancario).filter(MovimientoBancario.empresa_id == empresa_id)
        if fecha_inicio_dt:
            q_mov = q_mov.filter(MovimientoBancario.fecha >= fecha_inicio_dt)
        if fecha_fin_dt:
            q_mov = q_mov.filter(MovimientoBancario.fecha <= fecha_fin_dt)
        movimientos = q_mov.all()

        # CFDIs - Siempre permitir tanto PUE como P, excluyendo PPD (permitir NULL en metodo para tipo P)
        q_cfdi = db.query(ComprobanteFiscal).filter(
            ComprobanteFiscal.empresa_id == empresa_id,
            ComprobanteFiscal.estatus_sat == True
        )
        if fecha_inicio_dt:
            q_cfdi = q_cfdi.filter(
                or_(
                    ComprobanteFiscal.fecha >= fecha_inicio_dt,
                    ComprobanteFiscal.fecha_timbrado >= fecha_inicio_dt
                )
            )
        if fecha_fin_dt:
            q_cfdi = q_cfdi.filter(
                or_(
                    ComprobanteFiscal.fecha <= fecha_fin_dt,
                    ComprobanteFiscal.fecha_timbrado <= fecha_fin_dt
                )
            )
        # Permitir tanto PUE como P, excluyendo PPD (pero aceptar NULL en metodo_pago)
        q_cfdi = q_cfdi.filter(
            and_(
                ComprobanteFiscal.tipo_comprobante.in_(['I', 'P']),
                or_(
                    ComprobanteFiscal.metodo_pago != 'PPD',
                    ComprobanteFiscal.metodo_pago.is_(None)
                )
            )
        )
        cfdis = q_cfdi.all()

        # Agregar por monto (redondeo a 2 decimales)
        def to_amount_key(x: float) -> float:
            try:
                return round(float(x), 2)
            except Exception:
                return None

        mov_by_amount: Dict[float, int] = {}
        for m in movimientos:
            k = to_amount_key(m.monto)
            if k is None:
                continue
            mov_by_amount[k] = mov_by_amount.get(k, 0) + 1

        cfdi_by_amount: Dict[float, int] = {}
        for c in cfdis:
            # Para tipo P usar monto_pago de complementos_pago, para tipo I usar total
            if c.tipo_comprobante == 'P':
                complemento = db.query(ComplementoPago).filter(
                    ComplementoPago.cfdi_id == c.id
                ).first()
                if complemento and complemento.monto_pago:
                    k = to_amount_key(complemento.monto_pago)
                    if k is not None:
                        cfdi_by_amount[k] = cfdi_by_amount.get(k, 0) + 1
            else:  # tipo I
                k = to_amount_key(c.total)
                if k is not None:
                    cfdi_by_amount[k] = cfdi_by_amount.get(k, 0) + 1

        # Agrupar montos cercanos (<= 0.01) y mostrarlos como el mínimo del grupo
        all_amounts_sorted = sorted(set(list(mov_by_amount.keys()) + list(cfdi_by_amount.keys())))
        grupos: List[List[float]] = []
        for amt in all_amounts_sorted:
            if not grupos:
                grupos.append([amt])
            else:
                ultimo = grupos[-1][-1]
                if abs(amt - ultimo) <= 0.01:
                    grupos[-1].append(amt)
                else:
                    grupos.append([amt])

        rows = []
        for grupo in grupos:
            key = round(min(grupo), 2)
            cfdi_sum = sum(cfdi_by_amount.get(a, 0) for a in grupo)
            mov_sum = sum(mov_by_amount.get(a, 0) for a in grupo)
            rows.append({
                "monto": key,
                "cfdi_count": cfdi_sum,
                "movimientos_count": mov_sum,
                "_rangos": grupo,
            })

        # Ordenar por montos con mayor actividad primero
        rows.sort(key=lambda r: (-(r["cfdi_count"] + r["movimientos_count"]), -r["monto"]))

        return {
            "empresa_id": empresa_id,
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,
            "solo_pue": solo_pue,
            "total_rows": len(rows),
            "rows": rows
        }

    except Exception as e:
        logger.error(f"❌ Error obteniendo montos: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo montos: {str(e)}"
        )

@router.get("/montos/{empresa_id}/detalle")
async def obtener_detalle_monto(
    empresa_id: int,
    monto: float,
    fecha_inicio: str = None,
    fecha_fin: str = None,
    solo_pue: bool = True,
    db: Session = Depends(get_db)
):
    """
    Devuelve listas lado a lado para un monto: CFDIs y Movimientos dentro del rango de fechas.
    """
    try:
        fecha_inicio_dt = datetime.strptime(fecha_inicio, "%Y-%m-%d").date() if fecha_inicio else None
        fecha_fin_dt = datetime.strptime(fecha_fin, "%Y-%m-%d").date() if fecha_fin else None

        # Movimientos
        q_mov = db.query(MovimientoBancario).filter(MovimientoBancario.empresa_id == empresa_id)
        if fecha_inicio_dt:
            q_mov = q_mov.filter(MovimientoBancario.fecha >= fecha_inicio_dt)
        if fecha_fin_dt:
            q_mov = q_mov.filter(MovimientoBancario.fecha <= fecha_fin_dt)
        movs_all = q_mov.all()
        tol = 0.01  # Tolerancia fija de 0.01 para agrupar montos cercanos
        movimientos = [
            m for m in movs_all
            if (m.monto is not None and abs(float(m.monto) - float(monto)) <= tol)
        ]

        # CFDIs - Siempre permitir tanto PUE como P, excluyendo PPD
        q_cfdi = db.query(ComprobanteFiscal).filter(
            ComprobanteFiscal.empresa_id == empresa_id,
            ComprobanteFiscal.estatus_sat == True
        )
        if fecha_inicio_dt:
            q_cfdi = q_cfdi.filter(
                or_(
                    ComprobanteFiscal.fecha >= fecha_inicio_dt,
                    ComprobanteFiscal.fecha_timbrado >= fecha_inicio_dt
                )
            )
        if fecha_fin_dt:
            q_cfdi = q_cfdi.filter(
                or_(
                    ComprobanteFiscal.fecha <= fecha_fin_dt,
                    ComprobanteFiscal.fecha_timbrado <= fecha_fin_dt
                )
            )
        # Permitir tanto PUE como P, excluyendo PPD
        q_cfdi = q_cfdi.filter(
            and_(
                ComprobanteFiscal.tipo_comprobante.in_(['I', 'P']),
                or_(
                    ComprobanteFiscal.metodo_pago != 'PPD',
                    ComprobanteFiscal.metodo_pago.is_(None)
                )
            )
        )
        cfdis_all = q_cfdi.all()
        cfdis = []
        for c in cfdis_all:
            # Para tipo P usar monto_pago de complementos_pago, para tipo I usar total
            if c.tipo_comprobante == 'P':
                complemento = db.query(ComplementoPago).filter(
                    ComplementoPago.cfdi_id == c.id
                ).first()
                if complemento and complemento.monto_pago:
                    if abs(float(complemento.monto_pago) - float(monto)) <= tol:
                        cfdis.append(c)
            else:  # tipo I
                if c.total is not None and abs(float(c.total) - float(monto)) <= tol:
                    cfdis.append(c)

        # Reglas estrictas (sin fuzzy): validar solo si fecha y monto coinciden y es único el monto en ese día
        # Construir contadores por fecha para movimientos y CFDIs (ya filtrados por monto ~==)
        from collections import defaultdict
        
        def normalizar_fecha(fecha):
            """Normaliza fecha a tipo date para comparación consistente"""
            if hasattr(fecha, 'date'):
                return fecha.date()
            return fecha
        
        movs_por_fecha = defaultdict(int)
        for m in movimientos:
            fecha_normalizada = normalizar_fecha(m.fecha)
            movs_por_fecha[fecha_normalizada] += 1

        def obtener_fecha_cfdi(c):
            f = c.fecha or c.fecha_timbrado
            return normalizar_fecha(f)

        cfdis_por_fecha = defaultdict(int)
        for c in cfdis:
            f = obtener_fecha_cfdi(c)
            cfdis_por_fecha[f] += 1

        movimientos_out = []
        for m in sorted(movimientos, key=lambda x: (x.fecha, x.id)):
            fecha_normalizada = normalizar_fecha(m.fecha)
            count_movs = movs_por_fecha.get(fecha_normalizada, 0)
            count_cfdis = cfdis_por_fecha.get(fecha_normalizada, 0)
            es_unico_mov_dia = count_movs == 1
            es_unico_cfdi_dia = count_cfdis == 1
            valido = es_unico_mov_dia and es_unico_cfdi_dia

            if not es_unico_mov_dia:
                razon = f"Pendiente de revisión: {count_movs} movimientos con mismo monto en fecha {fecha_normalizada}"
            elif count_cfdis == 0:
                razon = f"Pendiente de revisión: sin CFDI de mismo monto en fecha {fecha_normalizada}"
            elif not es_unico_cfdi_dia:
                razon = f"Pendiente de revisión: {count_cfdis} CFDIs con mismo monto en fecha {fecha_normalizada}"
            else:
                razon = f"Exacta en mismo día (único): 1 mov + 1 CFDI"

            movimientos_out.append({
                "fecha": m.fecha.isoformat() if m.fecha else None,
                "concepto": m.concepto,
                "referencia": m.referencia,
                "monto": float(m.monto) if m.monto is not None else None,
                "cargo_abono": m.tipo.value if m.tipo else "abono",
                "estado_conciliacion": "exacta" if valido else "pendiente",
                "estado": razon,
                "valido": valido
            })

        # Obtener RFC de la empresa para comparar con emisor/receptor
        empresa = db.query(EmpresaContribuyente).filter(
            EmpresaContribuyente.id == empresa_id
        ).first()
        empresa_rfc = empresa.rfc if empresa else None

        # Separar CFDIs por Ingreso (empresa como emisor) y Egreso (empresa como receptor)
        cfdis_ingreso = []
        cfdis_egreso = []
        
        for c in sorted(cfdis, key=lambda x: ((x.fecha or x.fecha_timbrado), (x.uuid or ""))):
            f = obtener_fecha_cfdi(c)
            es_unico_cfdi_dia = cfdis_por_fecha.get(f, 0) == 1
            es_unico_mov_dia = movs_por_fecha.get(f, 0) == 1
            valido = es_unico_cfdi_dia and es_unico_mov_dia
            
            # Debug: log CFDI tipo P
            if c.tipo_comprobante == 'P':
                logger.info(f"🔍 Procesando CFDI P: UUID={c.uuid}, metodo_pago={c.metodo_pago}, total={c.total}")
            
            # Obtener monto de complemento de pago si es tipo P
            monto_pago = None
            if c.tipo_comprobante == 'P':
                complemento = db.query(ComplementoPago).filter(
                    ComplementoPago.cfdi_id == c.id
                ).first()
                if complemento and complemento.monto_pago:
                    monto_pago = float(complemento.monto_pago)
                    logger.info(f"✅ CFDI P {c.uuid}: monto_pago={monto_pago}")
                else:
                    logger.warning(f"⚠️ CFDI P {c.uuid}: sin complemento o monto_pago")
            
            # Determinar método de pago a mostrar (normalizar P y PUE)
            metodo_mostrar = c.metodo_pago
            if c.tipo_comprobante == 'P':
                # En CFDI P el metodo puede venir NULL; mostrar PUE por claridad de cobro inmediato
                metodo_mostrar = c.metodo_pago or 'PUE'
                logger.info(f"🔧 CFDI P {c.uuid}: metodo_pago original={c.metodo_pago}, normalizado={metodo_mostrar}")
            
            cfdi_data = {
                "uuid": c.uuid,
                "fecha": f.isoformat() if f else None,
                "total": float(c.total) if c.total is not None else None,
                "monto_pago": monto_pago,  # Para pagos tipo P
                "nombre_receptor": c.nombre_receptor,
                "nombre_emisor": c.nombre_emisor,
                "rfc_emisor": c.rfc_emisor,
                "rfc_receptor": c.rfc_receptor,
                "metodo_pago": metodo_mostrar,
                "tipo_comprobante": c.tipo_comprobante,
                "valido": valido
            }
            
            # Si la empresa es emisor -> Ingreso, si es receptor -> Egreso
            if c.rfc_emisor == empresa_rfc:  # La empresa es el emisor
                cfdis_ingreso.append(cfdi_data)
            elif c.rfc_receptor == empresa_rfc:  # La empresa es el receptor
                cfdis_egreso.append(cfdi_data)
            else:
                # En caso de que no coincida ninguno, agregarlo a ingreso por defecto
                cfdis_ingreso.append(cfdi_data)

        # Separar movimientos por CARGO/ABONO y normalizar según rol de la empresa
        # Regla: si la empresa es emisor (Ingreso), deben ser ABONOS; si es receptor (Egreso), deben ser CARGOS.
        movimientos_cargo = [m for m in movimientos_out if m.get("cargo_abono") == "cargo"]
        movimientos_abono = [m for m in movimientos_out if m.get("cargo_abono") == "abono"]

        # Si hay CFDIs ingreso, filtrar movimientos a solo abonos; si hay CFDIs egreso, solo cargos
        if cfdis_ingreso and not cfdis_egreso:
            movimientos_cargo = []
        elif cfdis_egreso and not cfdis_ingreso:
            movimientos_abono = []

        # Debug: contar CFDI tipo P
        cfdis_p_ingreso = [c for c in cfdis_ingreso if c.get('tipo_comprobante') == 'P']
        cfdis_p_egreso = [c for c in cfdis_egreso if c.get('tipo_comprobante') == 'P']
        logger.info(f"📊 CFDI tipo P enviados: {len(cfdis_p_ingreso)} ingreso + {len(cfdis_p_egreso)} egreso = {len(cfdis_p_ingreso) + len(cfdis_p_egreso)} total")

        return {
            "empresa_id": empresa_id,
            "monto": round(float(monto), 2),
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,
            "solo_pue": solo_pue,
            "tolerancia": tol,
            "cfdis_ingreso": cfdis_ingreso,
            "cfdis_egreso": cfdis_egreso,
            "movimientos_cargo": movimientos_cargo,
            "movimientos_abono": movimientos_abono,
            # Mantener compatibilidad con versión anterior
            "cfdis": cfdis_ingreso + cfdis_egreso,
            "movimientos": movimientos_out
        }

    except Exception as e:
        logger.error(f"❌ Error obteniendo detalle de monto: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo detalle de monto: {str(e)}"
        )
