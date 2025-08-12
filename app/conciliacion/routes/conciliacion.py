"""
Router para Conciliación Mejorada con FuzzyWuzzy
"""

import logging
from typing import List, Dict
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.core.database import get_db
from app.conciliacion.models import MovimientoBancario, EstadoConciliacion
from app.conciliacion.conciliador import ConciliadorMejorado, TipoConciliacion
from app.models.mysql_models import ComprobanteFiscal, EmpresaContribuyente

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conciliacion", tags=["Conciliación"])

@router.post("/ejecutar/{empresa_id}")
async def ejecutar_conciliacion_mejorada(
    empresa_id: int,
    fecha_inicio: str = None,
    fecha_fin: str = None,
    solo_pue: bool = True,
    incluir_ppd: bool = False,
    umbral_fuzzy: int = 90,
    db: Session = Depends(get_db)
):
    """
    Ejecuta conciliación mejorada con FuzzyWuzzy
    
    Parámetros:
    - empresa_id: ID de la empresa
    - fecha_inicio: Fecha inicio (YYYY-MM-DD) - opcional
    - fecha_fin: Fecha fin (YYYY-MM-DD) - opcional  
    - umbral_fuzzy: Umbral para coincidencias fuzzy (0-100)
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
            umbral_fuzzy=umbral_fuzzy,
            incluir_ppd=incluir_ppd,
            usar_solo_pue=solo_pue,
            usar_fuzzy=False
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
                if resultado.tipo_conciliacion in [TipoConciliacion.EXACTA, TipoConciliacion.FUZZY]:
                    # Mapear resultado a cfdi_uuid y actualizar estado/fecha
                    cfdi = db.query(ComprobanteFiscal).filter(ComprobanteFiscal.id == resultado.cfdi_id).first() if resultado.cfdi_id else None
                    if cfdi and cfdi.uuid:
                        movimiento.cfdi_uuid = cfdi.uuid
                    movimiento.estado = EstadoConciliacion.CONCILIADO
                    movimiento.fecha_conciliacion = datetime.now()
                else:
                    movimiento.estado = EstadoConciliacion.PENDIENTE
        
        db.commit()
        
        logger.info(f"✅ Conciliación completada: {reporte['resumen']['conciliados_exactos']} exactos, {reporte['resumen']['conciliados_fuzzy']} fuzzy")
        
        return {
            "mensaje": "Conciliación ejecutada exitosamente",
            "empresa_id": empresa_id,
            "fecha_ejecucion": datetime.now().isoformat(),
            "umbral_fuzzy": umbral_fuzzy,
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
                'puntaje_fuzzy': None,  # No disponible en este endpoint
                'razon': f"Estado: {movimiento.estado.value if movimiento.estado else 'PENDIENTE'}",
                'fecha': movimiento.fecha.isoformat() if movimiento.fecha else None,
                'concepto': movimiento.concepto if movimiento.concepto else None,
                'monto': float(movimiento.monto) if movimiento.monto else 0,
                'cfdi_monto': float(cfdi_monto) if cfdi_monto else None,
                'cfdi_total': float(cfdi_total) if cfdi_total else None
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

        # CFDIs
        q_cfdi = db.query(ComprobanteFiscal).filter(
            ComprobanteFiscal.empresa_id == empresa_id,
            ComprobanteFiscal.estatus_sat == True
        )
        if fecha_inicio_dt:
            q_cfdi = q_cfdi.filter(ComprobanteFiscal.fecha >= fecha_inicio_dt)
        if fecha_fin_dt:
            q_cfdi = q_cfdi.filter(ComprobanteFiscal.fecha <= fecha_fin_dt)
        if solo_pue:
            q_cfdi = q_cfdi.filter(ComprobanteFiscal.tipo_comprobante == 'I', ComprobanteFiscal.metodo_pago == 'PUE')
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
            k = to_amount_key(c.total)
            if k is None:
                continue
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

        # CFDIs
        q_cfdi = db.query(ComprobanteFiscal).filter(
            ComprobanteFiscal.empresa_id == empresa_id,
            ComprobanteFiscal.estatus_sat == True
        )
        if fecha_inicio_dt:
            q_cfdi = q_cfdi.filter(ComprobanteFiscal.fecha >= fecha_inicio_dt)
        if fecha_fin_dt:
            q_cfdi = q_cfdi.filter(ComprobanteFiscal.fecha <= fecha_fin_dt)
        if solo_pue:
            q_cfdi = q_cfdi.filter(ComprobanteFiscal.tipo_comprobante == 'I', ComprobanteFiscal.metodo_pago == 'PUE')
        cfdis_all = q_cfdi.all()
        cfdis = [
            c for c in cfdis_all
            if (c.total is not None and abs(float(c.total) - float(monto)) <= tol)
        ]

        # Reglas estrictas (sin fuzzy): validar solo si fecha y monto coinciden y es único el monto en ese día
        # Construir contadores por fecha para movimientos y CFDIs (ya filtrados por monto ~==)
        from collections import defaultdict
        movs_por_fecha = defaultdict(int)
        for m in movimientos:
            movs_por_fecha[m.fecha] += 1

        def obtener_fecha_cfdi(c):
            f = c.fecha or c.fecha_timbrado
            if hasattr(f, 'date'):
                return f.date()
            return f

        cfdis_por_fecha = defaultdict(int)
        for c in cfdis:
            f = obtener_fecha_cfdi(c)
            cfdis_por_fecha[f] += 1

        movimientos_out = []
        for m in sorted(movimientos, key=lambda x: (x.fecha, x.id)):
            es_unico_mov_dia = movs_por_fecha.get(m.fecha, 0) == 1
            es_unico_cfdi_dia = cfdis_por_fecha.get(m.fecha, 0) == 1
            valido = es_unico_mov_dia and es_unico_cfdi_dia

            if not es_unico_mov_dia:
                razon = f"Pendiente de revisión: montos duplicados en fecha {m.fecha.isoformat()}"
            elif cfdis_por_fecha.get(m.fecha, 0) == 0:
                razon = f"Pendiente de revisión: sin CFDI de mismo monto en fecha {m.fecha.isoformat()}"
            elif not es_unico_cfdi_dia:
                razon = f"Pendiente de revisión: múltiples CFDI de mismo monto en fecha {m.fecha.isoformat()}"
            else:
                razon = f"Exacta PUE en mismo día (único)"

            movimientos_out.append({
                "fecha": m.fecha.isoformat() if m.fecha else None,
                "concepto": m.concepto,
                "referencia": m.referencia,
                "monto": float(m.monto) if m.monto is not None else None,
                "cargo_abono": m.tipo.value if m.tipo else "ABONO",
                "estado_conciliacion": "exacta" if valido else "pendiente",
                "estado": razon,
                "valido": valido
            })

        cfdis_out = []
        for c in sorted(cfdis, key=lambda x: ((x.fecha or x.fecha_timbrado), (x.uuid or ""))):
            f = obtener_fecha_cfdi(c)
            es_unico_cfdi_dia = cfdis_por_fecha.get(f, 0) == 1
            es_unico_mov_dia = movs_por_fecha.get(f, 0) == 1
            valido = es_unico_cfdi_dia and es_unico_mov_dia
            cfdis_out.append({
                "uuid": c.uuid,
                "fecha": f.isoformat() if f else None,
                "total": float(c.total) if c.total is not None else None,
                "nombre_receptor": c.nombre_receptor,
                "metodo_pago": c.metodo_pago,
                "valido": valido
            })

        return {
            "empresa_id": empresa_id,
            "monto": round(float(monto), 2),
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,
            "solo_pue": solo_pue,
            "tolerancia": tol,
            "cfdis": cfdis_out,
            "movimientos": movimientos_out
        }

    except Exception as e:
        logger.error(f"❌ Error obteniendo detalle de monto: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo detalle de monto: {str(e)}"
        )
