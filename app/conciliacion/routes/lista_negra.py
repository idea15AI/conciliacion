#!/usr/bin/env python3
"""
Router para consultas de Lista Negra SAT
Endpoints para consultar contribuyentes en lista negra con CTEs optimizados
"""

import logging
from typing import List, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.database import get_db
from app.conciliacion.lista_negra_service import ListaNegraService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/lista-negra",
    tags=["Lista Negra SAT"],
    responses={
        404: {"description": "Datos no encontrados"},
        422: {"description": "Error de validación"},
        500: {"description": "Error interno del servidor"}
    }
)


def get_lista_negra_service(db: Session = Depends(get_db)) -> ListaNegraService:
    """Dependency para obtener el servicio de lista negra"""
    return ListaNegraService(db)


@router.get("/clientes/{rfc_empresa}")
async def obtener_clientes_lista_negra(
    rfc_empresa: str,
    fecha_inicio: Optional[str] = Query(None, description="Fecha inicio (YYYY-MM-DD)"),
    fecha_fin: Optional[str] = Query(None, description="Fecha fin (YYYY-MM-DD)"),
    lista_negra_service: ListaNegraService = Depends(get_lista_negra_service)
):
    """
    Obtiene clientes en lista negra para una empresa
    
    - RFC de la empresa (requerido)
    - Fecha inicio y fin opcionales
    - Retorna clientes con nivel de riesgo y montos
    """
    try:
        logger.info(f"Consultando clientes en lista negra para empresa {rfc_empresa}")
        
        clientes = lista_negra_service.obtener_clientes_lista_negra(
            rfc_empresa=rfc_empresa,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin
        )
        
        return {
            "empresa_rfc": rfc_empresa,
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,
            "total_clientes": len(clientes),
            "clientes": clientes
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo clientes en lista negra: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo clientes en lista negra: {str(e)}"
        )


@router.get("/proveedores/{rfc_empresa}")
async def obtener_proveedores_lista_negra(
    rfc_empresa: str,
    fecha_inicio: Optional[str] = Query(None, description="Fecha inicio (YYYY-MM-DD)"),
    fecha_fin: Optional[str] = Query(None, description="Fecha fin (YYYY-MM-DD)"),
    lista_negra_service: ListaNegraService = Depends(get_lista_negra_service)
):
    """
    Obtiene proveedores en lista negra para una empresa
    
    - RFC de la empresa (requerido)
    - Fecha inicio y fin opcionales
    - Retorna proveedores con nivel de riesgo y montos
    """
    try:
        logger.info(f"Consultando proveedores en lista negra para empresa {rfc_empresa}")
        
        proveedores = lista_negra_service.obtener_proveedores_lista_negra(
            rfc_empresa=rfc_empresa,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin
        )
        
        return {
            "empresa_rfc": rfc_empresa,
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,
            "total_proveedores": len(proveedores),
            "proveedores": proveedores
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo proveedores en lista negra: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo proveedores en lista negra: {str(e)}"
        )


@router.get("/kpis/{rfc_empresa}")
async def obtener_kpis_lista_negra(
    rfc_empresa: str,
    fecha_inicio: Optional[str] = Query(None, description="Fecha inicio (YYYY-MM-DD)"),
    fecha_fin: Optional[str] = Query(None, description="Fecha fin (YYYY-MM-DD)"),
    lista_negra_service: ListaNegraService = Depends(get_lista_negra_service)
):
    """
    Obtiene KPIs resumen de lista negra para una empresa
    
    - RFC de la empresa (requerido)
    - Fecha inicio y fin opcionales
    - Retorna métricas agregadas de riesgo
    """
    try:
        logger.info(f"Consultando KPIs de lista negra para empresa {rfc_empresa}")
        
        kpis = lista_negra_service.obtener_kpis_resumen(
            rfc_empresa=rfc_empresa,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin
        )
        
        return {
            "empresa_rfc": rfc_empresa,
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,
            "kpis": kpis
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo KPIs de lista negra: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo KPIs de lista negra: {str(e)}"
        )


@router.get("/distribucion-riesgo/{rfc_empresa}")
async def obtener_distribucion_riesgo(
    rfc_empresa: str,
    fecha_inicio: Optional[str] = Query(None, description="Fecha inicio (YYYY-MM-DD)"),
    fecha_fin: Optional[str] = Query(None, description="Fecha fin (YYYY-MM-DD)"),
    lista_negra_service: ListaNegraService = Depends(get_lista_negra_service)
):
    """
    Obtiene distribución por nivel de riesgo para una empresa
    
    - RFC de la empresa (requerido)
    - Fecha inicio y fin opcionales
    - Retorna conteo y montos por nivel de riesgo
    """
    try:
        logger.info(f"Consultando distribución de riesgo para empresa {rfc_empresa}")
        
        distribucion = lista_negra_service.obtener_distribucion_riesgo(
            rfc_empresa=rfc_empresa,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin
        )
        
        return {
            "empresa_rfc": rfc_empresa,
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,
            "distribucion": distribucion
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo distribución de riesgo: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo distribución de riesgo: {str(e)}"
        )


@router.get("/montos-por-nivel/{rfc_empresa}")
async def obtener_montos_por_nivel_riesgo(
    rfc_empresa: str,
    fecha_inicio: Optional[str] = Query(None, description="Fecha inicio (YYYY-MM-DD)"),
    fecha_fin: Optional[str] = Query(None, description="Fecha fin (YYYY-MM-DD)"),
    lista_negra_service: ListaNegraService = Depends(get_lista_negra_service)
):
    """
    Obtiene montos por nivel de riesgo para una empresa
    """
    try:
        logger.info(f"Consultando montos por nivel de riesgo para empresa {rfc_empresa}")
        
        montos = lista_negra_service.obtener_montos_por_nivel_riesgo(
            rfc_empresa=rfc_empresa,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin
        )
        
        return {
            "empresa_rfc": rfc_empresa,
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,
            "montos_por_nivel": montos
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo montos por nivel: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo montos por nivel: {str(e)}"
        )


@router.get("/debug-distribucion/{rfc_empresa}")
async def debug_distribucion_riesgo(
    rfc_empresa: str,
    fecha_inicio: Optional[str] = Query(None, description="Fecha inicio (YYYY-MM-DD)"),
    fecha_fin: Optional[str] = Query(None, description="Fecha fin (YYYY-MM-DD)"),
    lista_negra_service: ListaNegraService = Depends(get_lista_negra_service)
):
    """
    Función de debug para distribución de riesgo
    """
    try:
        logger.info(f"Debug distribución de riesgo para empresa {rfc_empresa}")
        
        debug_info = lista_negra_service.debug_distribucion_riesgo(
            rfc_empresa=rfc_empresa,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin
        )
        
        return {
            "empresa_rfc": rfc_empresa,
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,
            "debug": debug_info
        }
        
    except Exception as e:
        logger.error(f"Error en debug distribución: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error en debug distribución: {str(e)}"
        )


@router.get("/agregados-fiscal/{rfc_empresa}")
async def obtener_agregados_riesgo_fiscal(
    rfc_empresa: str,
    fecha_inicio: Optional[str] = Query(None, description="Fecha inicio (YYYY-MM-DD)"),
    fecha_fin: Optional[str] = Query(None, description="Fecha fin (YYYY-MM-DD)"),
    lista_negra_service: ListaNegraService = Depends(get_lista_negra_service)
):
    """
    Obtiene agregados de riesgo fiscal (IVA/ISR) para una empresa
    
    - RFC de la empresa (requerido)
    - Fecha inicio y fin opcionales
    - Retorna montos de IVA e ISR por nivel de riesgo
    """
    try:
        logger.info(f"Consultando agregados de riesgo fiscal para empresa {rfc_empresa}")
        
        agregados = lista_negra_service.obtener_agregados_riesgo_fiscal(
            rfc_empresa=rfc_empresa,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin
        )
        
        return {
            "empresa_rfc": rfc_empresa,
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,
            "agregados_fiscal": agregados
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo agregados de riesgo fiscal: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo agregados de riesgo fiscal: {str(e)}"
        )


@router.get("/reporte-completo/{rfc_empresa}")
async def generar_reporte_completo(
    rfc_empresa: str,
    fecha_inicio: Optional[str] = Query(None, description="Fecha inicio (YYYY-MM-DD)"),
    fecha_fin: Optional[str] = Query(None, description="Fecha fin (YYYY-MM-DD)"),
    lista_negra_service: ListaNegraService = Depends(get_lista_negra_service)
):
    """
    Genera reporte completo de lista negra para una empresa
    
    - RFC de la empresa (requerido)
    - Fecha inicio y fin opcionales
    - Retorna todos los datos consolidados
    """
    try:
        logger.info(f"Generando reporte completo de lista negra para empresa {rfc_empresa}")
        
        reporte = lista_negra_service.generar_reporte_completo(
            rfc_empresa=rfc_empresa,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin
        )
        
        return reporte
        
    except Exception as e:
        logger.error(f"Error generando reporte completo: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generando reporte completo: {str(e)}"
        )


@router.get("/empresas-disponibles")
async def obtener_empresas_disponibles(
    db: Session = Depends(get_db)
):
    """
    Obtiene lista de empresas disponibles para consultar lista negra
    """
    try:
        # Consulta simple para obtener empresas con CFDIs
        query = """
        SELECT DISTINCT 
            ec.rfc,
            ec.razon_social,
            ec.id
        FROM empresas_contribuyentes ec
        WHERE EXISTS (
            SELECT 1 FROM comprobantes_fiscales cf 
            WHERE cf.rfc_emisor = ec.rfc OR cf.rfc_receptor = ec.rfc
        )
        ORDER BY ec.razon_social
        """
        
        result = db.execute(text(query))
        empresas = [
            {
                "rfc": row.rfc,
                "razon_social": row.razon_social,
                "id": row.id
            }
            for row in result
        ]
        
        return {
            "total_empresas": len(empresas),
            "empresas": empresas
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo empresas disponibles: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo empresas disponibles: {str(e)}"
        )
