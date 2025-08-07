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
from app.models.mysql_models import ComprobanteFiscal

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conciliacion", tags=["Conciliación"])

@router.post("/ejecutar/{empresa_id}")
async def ejecutar_conciliacion_mejorada(
    empresa_id: int,
    fecha_inicio: str = None,
    fecha_fin: str = None,
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
        # Validar empresa
        empresa = db.query(ComprobanteFiscal).filter(
            ComprobanteFiscal.empresa_id == empresa_id
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
            fecha_inicio_dt = datetime.strptime(fecha_inicio, "%Y-%m-%d")
            query = query.filter(MovimientoBancario.fecha >= fecha_inicio_dt)
            
        if fecha_fin:
            fecha_fin_dt = datetime.strptime(fecha_fin, "%Y-%m-%d")
            query = query.filter(MovimientoBancario.fecha <= fecha_fin_dt)
        
        movimientos = query.all()
        
        if not movimientos:
            return {
                "mensaje": "No se encontraron movimientos bancarios para conciliar",
                "empresa_id": empresa_id,
                "total_movimientos": 0
            }
        
        # Crear conciliador
        conciliador = ConciliadorMejorado(db, empresa_id)
        
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
                    movimiento.estado = EstadoConciliacion.CONCILIADO
                    movimiento.comprobante_fiscal_id = resultado.cfdi_id
                else:
                    movimiento.estado = EstadoConciliacion.PENDIENTE
        
        db.commit()
        
        logger.info(f"✅ Conciliación completada: {reporte['resumen']['conciliados_exactos']} exactos, {reporte['resumen']['conciliados_fuzzy']} fuzzy")
        
        return {
            "mensaje": "Conciliación ejecutada exitosamente",
            "empresa_id": empresa_id,
            "fecha_ejecucion": datetime.now().isoformat(),
            "umbral_fuzzy": 85,  # Umbral fijo
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
        
        # Aplicar filtros de fecha
        if fecha_inicio:
            fecha_inicio_dt = datetime.strptime(fecha_inicio, "%Y-%m-%d")
            query = query.filter(MovimientoBancario.fecha >= fecha_inicio_dt)
            
        if fecha_fin:
            fecha_fin_dt = datetime.strptime(fecha_fin, "%Y-%m-%d")
            query = query.filter(MovimientoBancario.fecha <= fecha_fin_dt)
        
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