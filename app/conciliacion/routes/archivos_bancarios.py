#!/usr/bin/env python3
"""
Router para gestión de archivos bancarios

Endpoints para subir, procesar y gestionar archivos bancarios
con hash y tracking completo del proceso.
"""

import os
import tempfile
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.conciliacion.services.archivo_bancario_service import ArchivoBancarioService
from app.conciliacion.schemas import ArchivoBancarioResponse
from app.conciliacion.models import ArchivoBancario

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/archivos-bancarios",
    tags=["Archivos Bancarios"],
    responses={
        404: {"description": "Archivo no encontrado"},
        422: {"description": "Error de validación"},
        500: {"description": "Error interno del servidor"}
    }
)

# Constantes
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = {".pdf"}


def get_archivo_service(db: Session = Depends(get_db)) -> ArchivoBancarioService:
    """Dependency para obtener el servicio de archivos bancarios"""
    return ArchivoBancarioService(db)


@router.post("/subir", response_model=ArchivoBancarioResponse)
async def subir_archivo_bancario(
    empresa_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Sube y procesa un archivo bancario
    
    - Valida el archivo PDF
    - Calcula hash para evitar duplicados
    - Procesa con Gemini
    - Almacena en BD con tracking completo
    """
    try:
        # Validar archivo
        if not file.filename or not file.filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Solo se permiten archivos PDF"
            )
        
        # Leer contenido
        contenido = await file.read()
        
        # Validar tamaño
        if len(contenido) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Archivo demasiado grande. Tamaño máximo: {MAX_FILE_SIZE // (1024*1024)}MB"
            )
        
        # Crear archivo temporal
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            temp_file.write(contenido)
            temp_file_path = temp_file.name
        
        try:
            # Inicializar servicio
            archivo_service = ArchivoBancarioService(db)
            
            # Verificar si ya existe y crear si es necesario
            archivo_bancario, es_nuevo = archivo_service.verificar_y_crear_archivo_bancario(
                empresa_id=empresa_id,
                nombre_archivo=file.filename,
                file_path=temp_file_path,
                tamano_bytes=len(contenido)
            )
            
            # Solo procesar si es un archivo nuevo
            if es_nuevo:
                logger.info(f"🆕 Procesando archivo nuevo: {file.filename}")
                resultado = archivo_service.procesar_archivo(archivo_bancario, temp_file_path)
            else:
                logger.info(f"✅ Archivo ya existe, retornando datos existentes: {file.filename}")
                resultado = {
                    'exito': archivo_bancario.procesado_exitosamente,
                    'mensaje': 'Archivo ya procesado anteriormente',
                    'total_movimientos_extraidos': archivo_bancario.total_movimientos,
                    'banco_detectado': archivo_bancario.banco.value if archivo_bancario.banco else 'OTRO',
                    'tiempo_procesamiento_segundos': archivo_bancario.tiempo_procesamiento or 0
                }
            
            logger.info(f"✅ Archivo procesado exitosamente: {file.filename}")
            
            return ArchivoBancarioResponse(
                id=archivo_bancario.id,
                empresa_id=archivo_bancario.empresa_id,
                nombre_archivo=archivo_bancario.nombre_archivo,
                banco=archivo_bancario.banco.value,
                total_movimientos=archivo_bancario.total_movimientos,
                procesado_exitosamente=archivo_bancario.procesado_exitosamente,
                tiempo_procesamiento=archivo_bancario.tiempo_procesamiento,
                fecha_creacion=archivo_bancario.fecha_creacion,
                fecha_procesamiento=archivo_bancario.fecha_procesamiento,
                resultado_procesamiento=resultado
            )
            
        finally:
            # Limpiar archivo temporal
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
    except ValueError as e:
        # Error de validación (duplicado, etc.)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"❌ Error procesando archivo: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error procesando archivo: {str(e)}"
        )


@router.get("/empresa/{empresa_id}", response_model=List[ArchivoBancarioResponse])
async def obtener_archivos_empresa(
    empresa_id: int,
    limit: int = 50,
    offset: int = 0,
    archivo_service: ArchivoBancarioService = Depends(get_archivo_service)
):
    """
    Obtiene los archivos bancarios de una empresa
    
    - Paginación incluida
    - Ordenados por fecha de creación (más recientes primero)
    """
    try:
        archivos = archivo_service.obtener_archivos_empresa(
            empresa_id=empresa_id,
            limit=limit,
            offset=offset
        )
        
        return [
            ArchivoBancarioResponse(
                id=archivo.id,
                empresa_id=archivo.empresa_id,
                nombre_archivo=archivo.nombre_archivo,
                banco=archivo.banco.value,
                total_movimientos=archivo.total_movimientos,
                procesado_exitosamente=archivo.procesado_exitosamente,
                tiempo_procesamiento=archivo.tiempo_procesamiento,
                fecha_creacion=archivo.fecha_creacion,
                fecha_procesamiento=archivo.fecha_procesamiento
            )
            for archivo in archivos
        ]
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo archivos de empresa {empresa_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo archivos: {str(e)}"
        )


@router.get("/{archivo_id}", response_model=ArchivoBancarioResponse)
async def obtener_archivo(
    archivo_id: int,
    archivo_service: ArchivoBancarioService = Depends(get_archivo_service)
):
    """
    Obtiene un archivo bancario específico por ID
    """
    try:
        archivo = archivo_service.obtener_archivo_por_id(archivo_id)
        
        if not archivo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Archivo no encontrado"
            )
        
        return ArchivoBancarioResponse(
            id=archivo.id,
            empresa_id=archivo.empresa_id,
            nombre_archivo=archivo.nombre_archivo,
            banco=archivo.banco.value,
            total_movimientos=archivo.total_movimientos,
            procesado_exitosamente=archivo.procesado_exitosamente,
            tiempo_procesamiento=archivo.tiempo_procesamiento,
            fecha_creacion=archivo.fecha_creacion,
            fecha_procesamiento=archivo.fecha_procesamiento
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error obteniendo archivo {archivo_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo archivo: {str(e)}"
        )


@router.delete("/{archivo_id}")
async def eliminar_archivo(
    archivo_id: int,
    archivo_service: ArchivoBancarioService = Depends(get_archivo_service)
):
    """
    Elimina un archivo bancario
    """
    try:
        eliminado = archivo_service.eliminar_archivo(archivo_id)
        
        if not eliminado:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Archivo no encontrado"
            )
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Archivo eliminado exitosamente"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error eliminando archivo {archivo_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error eliminando archivo: {str(e)}"
        )


@router.get("/empresa/{empresa_id}/estadisticas")
async def obtener_estadisticas_empresa(
    empresa_id: int,
    archivo_service: ArchivoBancarioService = Depends(get_archivo_service)
):
    """
    Obtiene estadísticas de archivos bancarios de una empresa
    """
    try:
        archivos = archivo_service.obtener_archivos_empresa(empresa_id, limit=1000)
        
        # Calcular estadísticas
        total_archivos = len(archivos)
        archivos_exitosos = len([a for a in archivos if a.procesado_exitosamente])
        total_movimientos = sum(a.total_movimientos or 0 for a in archivos)
        tiempo_total = sum(a.tiempo_procesamiento or 0 for a in archivos)
        
        # Estadísticas por banco
        bancos = {}
        for archivo in archivos:
            banco = archivo.banco.value
            if banco not in bancos:
                bancos[banco] = 0
            bancos[banco] += 1
        
        return {
            "empresa_id": empresa_id,
            "total_archivos": total_archivos,
            "archivos_exitosos": archivos_exitosos,
            "archivos_fallidos": total_archivos - archivos_exitosos,
            "porcentaje_exito": (archivos_exitosos / total_archivos * 100) if total_archivos > 0 else 0,
            "total_movimientos": total_movimientos,
            "tiempo_total_procesamiento": tiempo_total,
            "archivos_por_banco": bancos
        }
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo estadísticas de empresa {empresa_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo estadísticas: {str(e)}"
        ) 