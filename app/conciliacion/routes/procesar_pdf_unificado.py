#!/usr/bin/env python3
"""
Router unificado para procesamiento de PDFs bancarios

Combina en un solo endpoint:
- Verificación de empresa
- Cálculo de hash
- Detección de duplicados
- Extracción con Gemini
- Almacenamiento en BD
"""

import os
import tempfile
import logging
from typing import List
from fastapi import APIRouter, File, UploadFile, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.conciliacion.services.archivo_bancario_service import ArchivoBancarioService
from app.conciliacion.schemas import ArchivoBancarioResponse
from app.core.config import settings

logger = logging.getLogger(__name__)

# Configuración
MAX_FILE_SIZE = settings.MAX_FILE_SIZE

# Crear router
router = APIRouter(prefix="/procesar-pdf", tags=["📄 Procesamiento Unificado"])


def get_archivo_service(db: Session = Depends(get_db)) -> ArchivoBancarioService:
    """Dependency para obtener el servicio de archivos bancarios"""
    return ArchivoBancarioService(db)


@router.post("/subir", response_model=ArchivoBancarioResponse)
async def procesar_pdf_unificado(
    empresa_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    forzar_gemini: bool = False,
):
    """
    Procesa un PDF bancario de manera unificada
    
    Proceso completo:
    1. ✅ Valida empresa existe
    2. 🔐 Calcula hash del archivo
    3. 🔄 Verifica duplicados
    4. 🤖 Extrae datos con Gemini (solo si es nuevo)
    5. 💾 Almacena en BD con tracking completo
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
            
            # Proceso unificado: verificar empresa + hash + duplicados + extracción
            archivo_bancario, es_nuevo = archivo_service.verificar_y_crear_archivo_bancario(
                empresa_id=empresa_id,
                nombre_archivo=file.filename,
                file_path=temp_file_path,
                tamano_bytes=len(contenido)
            )
            
            # Siempre procesar para obtener los datos originales
            logger.info(f"🔄 Procesando archivo: {file.filename}")
            resultado = archivo_service.procesar_archivo(
                archivo_bancario,
                temp_file_path,
                forzar_gemini=forzar_gemini,
            )
            
            # Obtener movimientos originales directamente del procesamiento de Gemini
            # Usar los datos antes de cualquier filtrado o procesamiento adicional
            movimientos_originales = []
            
            # Si es un archivo nuevo, los datos están en resultado['movimientos']
            if resultado.get('exito', False):
                movimientos_originales = resultado.get('movimientos', [])
                logger.info(f"📊 Movimientos originales obtenidos: {len(movimientos_originales)}")
                
                # Debug: mostrar los primeros movimientos originales
                for i, mov in enumerate(movimientos_originales[:3]):
                    logger.info(f"  Movimiento original {i+1}: cargos={mov.get('cargos')}, abonos={mov.get('abonos')}")
            else:
                logger.warning("⚠️ No se pudieron obtener movimientos originales del procesamiento")
            
            # Convertir a formato de respuesta: si es BBVA, NO filtrar; otros bancos sí deduplican
            movimientos = []
            banco_detectado = (resultado.get('banco_detectado') or '').upper()
            logger.info(f"🏦 Banco detectado para salida: {banco_detectado}")

            if banco_detectado == 'BBVA':
                logger.info("🟦 BBVA → sin filtrado ni deduplicación; manteniendo todos los movimientos")
                for i, mov in enumerate(movimientos_originales):
                    cargos = mov.get('cargos')
                    abonos = mov.get('abonos')
                    if i < 5:
                        logger.info(f"🔄 BBVA Mov {i+1}: fecha={mov.get('fecha')}, concepto={mov.get('concepto')[:50]}, cargos={cargos}, abonos={abonos}")
                    movimientos.append({
                        'fecha': mov.get('fecha'),
                        'concepto': mov.get('concepto'),
                        'referencia': mov.get('referencia'),
                        'cargos': cargos,
                        'abonos': abonos,
                        'saldo': mov.get('saldo'),
                        'tipo': 'CARGO' if cargos and cargos > 0 else 'ABONO' if abonos and abonos > 0 else 'N/A',
                        'estado': 'PENDIENTE'
                    })
                logger.info(f"📊 BBVA: enviados {len(movimientos)} de {len(movimientos_originales)} (sin filtrado)")
            else:
                movimientos_vistos = set()
                logger.info(f"📊 Aplicando filtro anti-duplicados a {len(movimientos_originales)} movimientos")
                for i, mov in enumerate(movimientos_originales):
                    cargos = mov.get('cargos')
                    abonos = mov.get('abonos')
                    clave_unica = f"{mov.get('fecha')}_{mov.get('concepto')}_{cargos}_{abonos}"
                    if i < 5:
                        logger.info(f"🔄 Movimiento {i+1}: fecha={mov.get('fecha')}, concepto={mov.get('concepto')[:50]}, cargos={cargos}, abonos={abonos}")
                    if clave_unica not in movimientos_vistos:
                        movimientos_vistos.add(clave_unica)
                        movimientos.append({
                            'fecha': mov.get('fecha'),
                            'concepto': mov.get('concepto'),
                            'referencia': mov.get('referencia'),
                            'cargos': cargos,
                            'abonos': abonos,
                            'saldo': mov.get('saldo'),
                            'tipo': 'CARGO' if cargos and cargos > 0 else 'ABONO' if abonos and abonos > 0 else 'N/A',
                            'estado': 'PENDIENTE'
                        })
                    else:
                        logger.info(f"🔄 Duplicado encontrado: {clave_unica}")
                logger.info(f"📊 Movimientos después de filtrado: {len(movimientos)} de {len(movimientos_originales)}")
            
            # Agregar movimientos al resultado
            resultado['movimientos'] = movimientos
            
            # Log para debug: mostrar los primeros movimientos
            logger.info(f"📊 Movimientos enviados al frontend:")
            for i, mov in enumerate(movimientos[:5]):  # Solo los primeros 5
                logger.info(f"  Movimiento {i+1}: fecha={mov.get('fecha')}, concepto={mov.get('concepto')[:50]}, cargos={mov.get('cargos')}, abonos={mov.get('abonos')}")
            
            # Log para debug: mostrar la estructura completa del resultado
            logger.info(f"📊 Estructura del resultado enviado:")
            logger.info(f"  - resultado.keys(): {list(resultado.keys())}")
            logger.info(f"  - resultado['movimientos']: {len(resultado.get('movimientos', []))} movimientos")
            logger.info(f"  - Total movimientos originales: {len(movimientos_originales)}")
            logger.info(f"  - Total movimientos filtrados: {len(movimientos)}")
            
            logger.info(f"✅ Proceso completado: {file.filename}")
            
            return ArchivoBancarioResponse(
                id=archivo_bancario.id,
                empresa_id=archivo_bancario.empresa_id,
                nombre_archivo=archivo_bancario.nombre_archivo,
                banco=archivo_bancario.banco.value,
                total_movimientos=archivo_bancario.total_movimientos,
                movimientos_procesados=archivo_bancario.movimientos_procesados,
                procesado_exitosamente=archivo_bancario.procesado_exitosamente,
                fecha_creacion=archivo_bancario.fecha_creacion,
                fecha_procesamiento=archivo_bancario.fecha_procesamiento,
                tiempo_procesamiento=archivo_bancario.tiempo_procesamiento,
                resultado_procesamiento=resultado
            )
            
        finally:
            # Limpiar archivo temporal
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
    except ValueError as e:
        # Error de validación (empresa no existe, duplicado, etc.)
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


@router.get("/empresa/{empresa_id}/archivos", response_model=List[ArchivoBancarioResponse])
async def obtener_archivos_empresa(
    empresa_id: int,
    limit: int = 50,
    offset: int = 0,
    archivo_service: ArchivoBancarioService = Depends(get_archivo_service)
):
    """
    Obtiene los archivos procesados de una empresa
    """
    try:
        archivos = archivo_service.obtener_archivos_empresa(empresa_id, limit, offset)
        
        return [
            ArchivoBancarioResponse(
                id=archivo.id,
                empresa_id=archivo.empresa_id,
                nombre_archivo=archivo.nombre_archivo,
                banco=archivo.banco.value,
                total_movimientos=archivo.total_movimientos,
                movimientos_procesados=archivo.movimientos_procesados,
                procesado_exitosamente=archivo.procesado_exitosamente,
                fecha_creacion=archivo.fecha_creacion,
                fecha_procesamiento=archivo.fecha_procesamiento,
                tiempo_procesamiento=archivo.tiempo_procesamiento,
                resultado_procesamiento=None  # No incluir en lista
            )
            for archivo in archivos
        ]
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo archivos: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo archivos: {str(e)}"
        )


@router.get("/archivo/{archivo_id}", response_model=ArchivoBancarioResponse)
async def obtener_archivo_detalle(
    archivo_id: int,
    archivo_service: ArchivoBancarioService = Depends(get_archivo_service)
):
    """
    Obtiene el detalle completo de un archivo procesado
    """
    try:
        archivo = archivo_service.obtener_archivo_por_id(archivo_id)
        
        if not archivo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Archivo con ID {archivo_id} no encontrado"
            )
        
        return ArchivoBancarioResponse(
            id=archivo.id,
            empresa_id=archivo.empresa_id,
            nombre_archivo=archivo.nombre_archivo,
            banco=archivo.banco.value,
            total_movimientos=archivo.total_movimientos,
            movimientos_procesados=archivo.movimientos_procesados,
            procesado_exitosamente=archivo.procesado_exitosamente,
            fecha_creacion=archivo.fecha_creacion,
            fecha_procesamiento=archivo.fecha_procesamiento,
            tiempo_procesamiento=archivo.tiempo_procesamiento,
            resultado_procesamiento=None  # Se puede agregar si es necesario
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error obteniendo archivo {archivo_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo archivo: {str(e)}"
        )


@router.get("/empresa/{empresa_id}/movimientos")
async def obtener_movimientos_empresa(
    empresa_id: int,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    Obtiene los movimientos bancarios de una empresa
    """
    try:
        from app.conciliacion.models import MovimientoBancario
        
        movimientos = db.query(MovimientoBancario).filter(
            MovimientoBancario.empresa_id == empresa_id
        ).order_by(
            MovimientoBancario.fecha.desc()
        ).offset(offset).limit(limit).all()
        
        return [
            {
                "id": mov.id,
                "empresa_id": mov.empresa_id,
                "fecha": mov.fecha.isoformat() if mov.fecha else None,
                "concepto": mov.concepto,
                "monto": float(mov.monto) if mov.monto else 0,
                "tipo": mov.tipo.value if mov.tipo else None,
                "referencia": mov.referencia,
                "saldo": float(mov.saldo) if mov.saldo else None,
                "estado": mov.estado.value if mov.estado else None,
                "archivo_origen_id": mov.archivo_origen_id,
                "datos_ocr": mov.datos_ocr,
                "fecha_creacion": mov.fecha_creacion.isoformat() if mov.fecha_creacion else None
            }
            for mov in movimientos
        ]
        
    except Exception as e:
        logger.error(f" Error obteniendo movimientos: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo movimientos: {str(e)}"
        ) 