"""
Router FastAPI para el módulo de conciliación bancaria avanzada

Define todos los endpoints para el procesamiento OCR, conciliación automática,
reportes y gestión de movimientos bancarios.
"""

import os
import time
import logging
import json
from typing import List, Optional, Any, Dict
from datetime import datetime
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func

from app.core.database import get_db
from app.models.mysql_models import EmpresaContribuyente, ComprobanteFiscal
from .models import (
    MovimientoBancario, ArchivoBancario, ResultadoConciliacion,
    EstadoConciliacion, MetodoConciliacion, TipoMovimiento
)
from .schemas import (
    # Requests
    SubirEstadoCuentaRequest, ConciliacionRequest, FiltrosMovimientos, PaginacionRequest,
    # Responses
    ResultadoOCR, ResumenConciliacion, ReporteConciliacion, MovimientoBancarioResponse,
    ArchivoBancarioResponse, PaginacionResponse
)
from .ocr_processor import OCRProcessor
from .conciliador import ConciliadorAvanzado
from .utils import calcular_hash_archivo, calcular_rango_fechas
from .exceptions import (
    ConciliacionError, OCRError, EmpresaNoEncontradaError, 
    ArchivoYaProcesadoError, get_http_status_code
)

logger = logging.getLogger(__name__)

# Crear router
router = APIRouter(
    prefix="/conciliacion",
    tags=["Conciliación Bancaria"],
    responses={
        404: {"description": "Recurso no encontrado"},
        422: {"description": "Error de validación"},
        500: {"description": "Error interno del servidor"}
    }
)

# Constantes
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = {".pdf"}


# === UTILIDADES ===

def serializar_para_json(obj: Any) -> Any:
    """
    Convierte objetos con Decimal y datetime a tipos serializables por JSON
    """
    if isinstance(obj, Decimal):
        return str(obj)
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: serializar_para_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [serializar_para_json(item) for item in obj]
    else:
        return obj


# === DEPENDENCIAS ===

def get_ocr_processor() -> OCRProcessor:
    """Dependency para obtener procesador OCR"""
    try:
        return OCRProcessor()
    except Exception as e:
        logger.error(f"Error inicializando OCR processor: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error de configuración del procesador OCR"
        )


def get_conciliador(db: Session = Depends(get_db)) -> ConciliadorAvanzado:
    """Dependency para obtener conciliador"""
    return ConciliadorAvanzado(db)


def validar_empresa_existe(rfc_empresa: str, db: Session) -> EmpresaContribuyente:
    """Valida que la empresa exista y la retorna"""
    empresa = db.query(EmpresaContribuyente).filter(
        EmpresaContribuyente.rfc == rfc_empresa.upper()
    ).first()
    
    if not empresa:
        raise EmpresaNoEncontradaError(rfc_empresa)
    
    return empresa


def validar_archivo_pdf(file: UploadFile) -> bytes:
    """Valida archivo PDF y retorna contenido"""
    # Validar extensión
    if not file.filename or not any(file.filename.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Solo se permiten archivos PDF"
        )
    
    # Leer contenido
    try:
        contenido = file.file.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Error leyendo archivo: {str(e)}"
        )
    
    # Validar tamaño
    if len(contenido) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Archivo muy grande. Máximo: {MAX_FILE_SIZE // (1024*1024)}MB"
        )
    
    # Validar que sea PDF
    if not contenido.startswith(b'%PDF'):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El archivo no es un PDF válido"
        )
    
    return contenido


# === EXCEPTION HANDLERS ===
# Nota: Los manejadores de excepciones se definen a nivel de aplicación en main.py


# === ENDPOINTS ===

@router.post("/subir-estado-cuenta", response_model=ResultadoOCR)
async def subir_estado_cuenta(
    rfc_empresa: str = Query(..., description="RFC de la empresa"),
    file: UploadFile = File(..., description="Archivo PDF del estado de cuenta"),
    db: Session = Depends(get_db),
    ocr_processor: OCRProcessor = Depends(get_ocr_processor)
):
    """
    Procesa un estado de cuenta bancario usando OCR avanzado
    
    - **rfc_empresa**: RFC de la empresa (requerido)
    - **file**: Archivo PDF del estado de cuenta (máximo 50MB)
    
    Retorna información extraída del estado de cuenta y movimientos bancarios.
    """
    inicio_tiempo = time.time()
    
    try:
        logger.info(f"Iniciando procesamiento OCR para empresa {rfc_empresa}")
        
        # Validar empresa
        empresa = validar_empresa_existe(rfc_empresa, db)
        
        # Validar archivo
        contenido_pdf = validar_archivo_pdf(file)
        hash_archivo = calcular_hash_archivo(contenido_pdf)
        
        # Verificar si el archivo ya fue procesado
        archivo_existente = db.query(ArchivoBancario).filter(
            ArchivoBancario.hash_archivo == hash_archivo
        ).first()
        
        if archivo_existente:
            raise ArchivoYaProcesadoError(hash_archivo, archivo_existente.id)
        
        # Procesar con OCR
        resultado_ocr = ocr_processor.procesar_estado_cuenta(contenido_pdf, empresa.id)
        
        if not resultado_ocr["exito"]:
            raise OCRError("Error en procesamiento OCR")
        
        # Crear registro del archivo
        metadatos = resultado_ocr["metadatos"]
        
        # Convertir fechas de string ISO a datetime para las columnas de BD
        periodo_inicio = None
        periodo_fin = None
        if metadatos.get("periodo_inicio"):
            try:
                periodo_inicio = datetime.fromisoformat(metadatos["periodo_inicio"])
            except (ValueError, TypeError):
                periodo_inicio = None
        
        if metadatos.get("periodo_fin"):
            try:
                periodo_fin = datetime.fromisoformat(metadatos["periodo_fin"])
            except (ValueError, TypeError):
                periodo_fin = None
        
        # Convertir montos de string a Decimal para las columnas de BD
        saldo_inicial = None
        saldo_final = None
        if metadatos.get("saldo_inicial"):
            try:
                saldo_inicial = Decimal(metadatos["saldo_inicial"])
            except (ValueError, TypeError):
                saldo_inicial = None
        
        if metadatos.get("saldo_final"):
            try:
                saldo_final = Decimal(metadatos["saldo_final"])
            except (ValueError, TypeError):
                saldo_final = None
        
        archivo_bancario = ArchivoBancario(
            empresa_id=empresa.id,
            nombre_archivo=file.filename,
            hash_archivo=hash_archivo,
            tamano_bytes=len(contenido_pdf),
            banco=resultado_ocr["banco_detectado"],
            numero_cuenta=metadatos.get("numero_cuenta"),
            periodo_inicio=periodo_inicio,
            periodo_fin=periodo_fin,
            saldo_inicial=saldo_inicial,
            saldo_final=saldo_final,
            total_movimientos=resultado_ocr["total_movimientos"],
            movimientos_procesados=resultado_ocr["total_movimientos"],
            paginas_procesadas=resultado_ocr["paginas_procesadas"],
            datos_metadata=metadatos,  # Ahora contiene fechas como strings ISO
            procesado_exitosamente=True,
            tiempo_procesamiento=resultado_ocr["tiempo_procesamiento"],
            fecha_procesamiento=datetime.now(),
            errores_ocr=resultado_ocr["errores"]
        )
        
        db.add(archivo_bancario)
        db.flush()  # Para obtener el ID
        
        # Crear movimientos bancarios
        movimientos_creados = 0
        for mov_data in resultado_ocr["movimientos"]:
            try:
                movimiento = MovimientoBancario(
                    empresa_id=empresa.id,
                    fecha=mov_data["fecha"],
                    concepto=mov_data["concepto"],
                    monto=mov_data["monto"],
                    tipo=mov_data["tipo"],
                    referencia=mov_data.get("referencia"),
                    saldo=mov_data.get("saldo"),
                    archivo_origen_id=archivo_bancario.id,
                    datos_ocr=mov_data.get("datos_ocr"),
                    estado=EstadoConciliacion.PENDIENTE
                )
                db.add(movimiento)
                movimientos_creados += 1
            except Exception as e:
                logger.warning(f"Error creando movimiento: {str(e)}")
                continue
        
        archivo_bancario.movimientos_procesados = movimientos_creados
        db.commit()
        
        tiempo_total = time.time() - inicio_tiempo
        
        return ResultadoOCR(
            exito=True,
            mensaje=f"Estado de cuenta procesado exitosamente: {movimientos_creados} movimientos extraídos",
            archivo_id=archivo_bancario.id,
            banco_detectado=resultado_ocr["banco_detectado"],
            periodo_detectado={
                "inicio": periodo_inicio,
                "fin": periodo_fin
            } if periodo_inicio else None,
            total_movimientos_extraidos=movimientos_creados,
            errores=resultado_ocr["errores"],
            tiempo_procesamiento_segundos=int(tiempo_total)
        )
        
    except ConciliacionError:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error inesperado en OCR: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno: {str(e)}"
        )


@router.post("/ejecutar", response_model=ResumenConciliacion)
async def ejecutar_conciliacion(
    request: ConciliacionRequest,
    db: Session = Depends(get_db),
    conciliador: ConciliadorAvanzado = Depends(get_conciliador)
):
    """
    Ejecuta el proceso de conciliación automática para un período específico
    
    - **rfc_empresa**: RFC de la empresa a conciliar
    - **mes**: Mes a conciliar (1-12)
    - **anio**: Año a conciliar
    - **tolerancia_monto**: Tolerancia en pesos para matching aproximado (opcional)
    - **dias_tolerancia**: Días de tolerancia para matching de fechas (opcional)
    - **forzar_reproceso**: Forzar reproceso aunque ya exista conciliación (opcional)
    
    Ejecuta todas las estrategias de conciliación y retorna estadísticas detalladas.
    """
    inicio_tiempo = time.time()
    
    try:
        logger.info(f"Iniciando conciliación para {request.rfc_empresa}, {request.mes}/{request.anio}")
        
        # Validar empresa
        empresa = validar_empresa_existe(request.rfc_empresa, db)
        
        # Calcular fechas del período
        fecha_inicio, fecha_fin = calcular_rango_fechas(request.mes, request.anio)
        
        # Verificar si ya existe conciliación para el período (si no se fuerza reproceso)
        if not request.forzar_reproceso:
            conciliacion_existente = db.query(ResultadoConciliacion).filter(
                and_(
                    ResultadoConciliacion.empresa_id == empresa.id,
                    ResultadoConciliacion.periodo_inicio == fecha_inicio,
                    ResultadoConciliacion.periodo_fin == fecha_fin
                )
            ).first()
            
            if conciliacion_existente:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Ya existe conciliación para el período {request.mes}/{request.anio}. Use forzar_reproceso=true para reprocesar."
                )
        
        # Ejecutar conciliación
        resultado = conciliador.conciliar_periodo(
            empresa_id=empresa.id,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            tolerancia_monto=request.tolerancia_monto,
            dias_tolerancia=request.dias_tolerancia
        )
        
        # Guardar resultado en base de datos
        if resultado["exito"]:
            estadisticas = resultado["estadisticas"]
            
            resultado_conciliacion = ResultadoConciliacion(
                empresa_id=empresa.id,
                periodo_inicio=fecha_inicio,
                periodo_fin=fecha_fin,
                total_movimientos_bancarios=estadisticas.total_movimientos_bancarios,
                total_cfdis_periodo=estadisticas.total_cfdis_periodo,
                movimientos_conciliados=estadisticas.movimientos_conciliados,
                movimientos_pendientes=estadisticas.movimientos_pendientes,
                movimientos_descartados=estadisticas.movimientos_descartados,
                movimientos_manuales=estadisticas.movimientos_manuales,
                conciliados_exacto=estadisticas.conciliados_exacto,
                conciliados_referencia=estadisticas.conciliados_referencia,
                conciliados_aproximado=estadisticas.conciliados_aproximado,
                conciliados_complemento_ppd=estadisticas.conciliados_complemento_ppd,
                conciliados_heuristica=estadisticas.conciliados_heuristica,
                conciliados_ml_patron=estadisticas.conciliados_ml_patron,
                monto_total_conciliado=estadisticas.monto_total_conciliado,
                monto_total_pendiente=estadisticas.monto_total_pendiente,
                nivel_confianza_promedio=estadisticas.nivel_confianza_promedio,
                tiempo_procesamiento_segundos=resultado["tiempo_procesamiento_segundos"],
                alertas_criticas=serializar_para_json([alerta.dict() for alerta in resultado["alertas_criticas"]]),
                sugerencias=serializar_para_json([sug.dict() for sug in resultado["sugerencias"]]),
                configuracion_utilizada=serializar_para_json(resultado["configuracion_utilizada"])
            )
            
            db.add(resultado_conciliacion)
            db.commit()
        
        tiempo_total = time.time() - inicio_tiempo
        
        return ResumenConciliacion(
            exito=resultado["exito"],
            mensaje=resultado["mensaje"],
            estadisticas=resultado["estadisticas"],
            alertas_criticas=resultado["alertas_criticas"],
            sugerencias=resultado["sugerencias"],
            fecha_proceso=datetime.now(),
            tiempo_total_segundos=int(tiempo_total)
        )
        
    except HTTPException:
        raise
    except ConciliacionError:
        raise
    except Exception as e:
        logger.error(f"Error ejecutando conciliación: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno: {str(e)}"
        )


@router.get("/reporte/{empresa_id}", response_model=ReporteConciliacion)
async def obtener_reporte_conciliacion(
    empresa_id: int,
    mes: Optional[int] = Query(None, ge=1, le=12, description="Mes del reporte"),
    anio: Optional[int] = Query(None, ge=2000, le=2030, description="Año del reporte"),
    db: Session = Depends(get_db)
):
    """
    Genera reporte detallado de conciliación para una empresa
    
    - **empresa_id**: ID de la empresa
    - **mes**: Mes del reporte (opcional, por defecto mes actual)
    - **anio**: Año del reporte (opcional, por defecto año actual)
    
    Retorna reporte con estadísticas, movimientos pendientes y alertas.
    """
    try:
        # Validar empresa
        empresa = db.query(EmpresaContribuyente).filter(
            EmpresaContribuyente.id == empresa_id
        ).first()
        
        if not empresa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Empresa con ID {empresa_id} no encontrada"
            )
        
        # Determinar período
        if mes and anio:
            fecha_inicio, fecha_fin = calcular_rango_fechas(mes, anio)
        else:
            # Usar mes/año actual
            now = datetime.now()
            fecha_inicio, fecha_fin = calcular_rango_fechas(now.month, now.year)
        
        # Obtener último resultado de conciliación
        resultado_conciliacion = db.query(ResultadoConciliacion).filter(
            and_(
                ResultadoConciliacion.empresa_id == empresa_id,
                ResultadoConciliacion.periodo_inicio == fecha_inicio,
                ResultadoConciliacion.periodo_fin == fecha_fin
            )
        ).order_by(desc(ResultadoConciliacion.fecha_proceso)).first()
        
        # Estadísticas
        if resultado_conciliacion:
            estadisticas = EstadisticasConciliacion(
                total_movimientos_bancarios=resultado_conciliacion.total_movimientos_bancarios,
                total_cfdis_periodo=resultado_conciliacion.total_cfdis_periodo,
                movimientos_conciliados=resultado_conciliacion.movimientos_conciliados,
                movimientos_pendientes=resultado_conciliacion.movimientos_pendientes,
                movimientos_descartados=resultado_conciliacion.movimientos_descartados,
                movimientos_manuales=resultado_conciliacion.movimientos_manuales,
                conciliados_exacto=resultado_conciliacion.conciliados_exacto,
                conciliados_referencia=resultado_conciliacion.conciliados_referencia,
                conciliados_aproximado=resultado_conciliacion.conciliados_aproximado,
                conciliados_complemento_ppd=resultado_conciliacion.conciliados_complemento_ppd,
                conciliados_heuristica=resultado_conciliacion.conciliados_heuristica,
                conciliados_ml_patron=resultado_conciliacion.conciliados_ml_patron,
                monto_total_conciliado=resultado_conciliacion.monto_total_conciliado or 0,
                monto_total_pendiente=resultado_conciliacion.monto_total_pendiente or 0,
                porcentaje_conciliacion=(
                    resultado_conciliacion.movimientos_conciliados / 
                    resultado_conciliacion.total_movimientos_bancarios * 100
                    if resultado_conciliacion.total_movimientos_bancarios > 0 else 0
                ),
                nivel_confianza_promedio=resultado_conciliacion.nivel_confianza_promedio,
                tiempo_procesamiento_segundos=resultado_conciliacion.tiempo_procesamiento_segundos
            )
            
            alertas_criticas = [
                AlertaCritica(**alerta) for alerta in (resultado_conciliacion.alertas_criticas or [])
            ]
        else:
            estadisticas = EstadisticasConciliacion()
            alertas_criticas = []
        
        # Obtener movimientos pendientes
        movimientos_pendientes = db.query(MovimientoBancario).filter(
            and_(
                MovimientoBancario.empresa_id == empresa_id,
                MovimientoBancario.fecha >= fecha_inicio,
                MovimientoBancario.fecha <= fecha_fin,
                MovimientoBancario.estado == EstadoConciliacion.PENDIENTE
            )
        ).order_by(desc(MovimientoBancario.monto)).limit(50).all()
        
        # Obtener movimientos con alertas (confianza baja)
        movimientos_alertas = db.query(MovimientoBancario).filter(
            and_(
                MovimientoBancario.empresa_id == empresa_id,
                MovimientoBancario.fecha >= fecha_inicio,
                MovimientoBancario.fecha <= fecha_fin,
                MovimientoBancario.estado == EstadoConciliacion.CONCILIADO,
                MovimientoBancario.nivel_confianza < 0.8
            )
        ).order_by(MovimientoBancario.nivel_confianza).limit(20).all()
        
        # Generar sugerencias de mejora
        sugerencias_mejora = []
        if estadisticas.porcentaje_conciliacion < 80:
            sugerencias_mejora.append("Revisar configuración de tolerancias de monto y fecha")
        if estadisticas.movimientos_pendientes > 10:
            sugerencias_mejora.append(f"Hay {estadisticas.movimientos_pendientes} movimientos pendientes que requieren revisión manual")
        if len(alertas_criticas) > 0:
            sugerencias_mejora.append(f"Atender {len(alertas_criticas)} alertas críticas identificadas")
        
        return ReporteConciliacion(
            empresa_id=empresa_id,
            rfc_empresa=empresa.rfc,
            periodo_inicio=fecha_inicio,
            periodo_fin=fecha_fin,
            estadisticas=estadisticas,
            movimientos_pendientes=[
                MovimientoBancarioResponse.from_orm(mov) for mov in movimientos_pendientes
            ],
            movimientos_con_alertas=[
                MovimientoBancarioResponse.from_orm(mov) for mov in movimientos_alertas
            ],
            alertas_criticas=alertas_criticas,
            sugerencias_mejora=sugerencias_mejora,
            fecha_generacion=datetime.now()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generando reporte: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno: {str(e)}"
        )


@router.get("/movimientos/{empresa_id}", response_model=PaginacionResponse)
async def listar_movimientos(
    empresa_id: int,
    filtros: FiltrosMovimientos = Depends(),
    paginacion: PaginacionRequest = Depends(),
    db: Session = Depends(get_db)
):
    """
    Lista movimientos bancarios con filtros y paginación
    
    - **empresa_id**: ID de la empresa
    - **estado**: Filtrar por estado de conciliación (opcional)
    - **tipo**: Filtrar por tipo de movimiento (opcional)
    - **metodo_conciliacion**: Filtrar por método de conciliación (opcional)
    - **fecha_inicio**: Fecha de inicio para filtrar (opcional)
    - **fecha_fin**: Fecha de fin para filtrar (opcional)
    - **monto_minimo**: Monto mínimo para filtrar (opcional)
    - **monto_maximo**: Monto máximo para filtrar (opcional)
    - **concepto_like**: Buscar en concepto (opcional)
    - **referencia_like**: Buscar en referencia (opcional)
    
    Parámetros de paginación:
    - **page**: Número de página (por defecto 1)
    - **size**: Tamaño de página (por defecto 50, máximo 1000)
    - **sort_by**: Campo de ordenamiento (por defecto "fecha")
    - **sort_order**: Orden ascendente (asc) o descendente (desc)
    """
    try:
        # Validar empresa
        empresa = db.query(EmpresaContribuyente).filter(
            EmpresaContribuyente.id == empresa_id
        ).first()
        
        if not empresa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Empresa con ID {empresa_id} no encontrada"
            )
        
        # Construir query base
        query = db.query(MovimientoBancario).filter(
            MovimientoBancario.empresa_id == empresa_id
        )
        
        # Aplicar filtros
        if filtros.estado:
            query = query.filter(MovimientoBancario.estado == filtros.estado)
        
        if filtros.tipo:
            query = query.filter(MovimientoBancario.tipo == filtros.tipo)
        
        if filtros.metodo_conciliacion:
            query = query.filter(MovimientoBancario.metodo_conciliacion == filtros.metodo_conciliacion)
        
        if filtros.fecha_inicio:
            query = query.filter(MovimientoBancario.fecha >= filtros.fecha_inicio)
        
        if filtros.fecha_fin:
            query = query.filter(MovimientoBancario.fecha <= filtros.fecha_fin)
        
        if filtros.monto_minimo:
            query = query.filter(MovimientoBancario.monto >= filtros.monto_minimo)
        
        if filtros.monto_maximo:
            query = query.filter(MovimientoBancario.monto <= filtros.monto_maximo)
        
        if filtros.concepto_like:
            query = query.filter(MovimientoBancario.concepto.like(f"%{filtros.concepto_like}%"))
        
        if filtros.referencia_like:
            query = query.filter(MovimientoBancario.referencia.like(f"%{filtros.referencia_like}%"))
        
        # Contar total
        total = query.count()
        
        # Aplicar ordenamiento
        if hasattr(MovimientoBancario, paginacion.sort_by):
            orden_campo = getattr(MovimientoBancario, paginacion.sort_by)
            if paginacion.sort_order == "desc":
                orden_campo = desc(orden_campo)
            query = query.order_by(orden_campo)
        else:
            # Ordenamiento por defecto
            query = query.order_by(desc(MovimientoBancario.fecha))
        
        # Aplicar paginación
        offset = (paginacion.page - 1) * paginacion.size
        movimientos = query.offset(offset).limit(paginacion.size).all()
        
        # Calcular metadatos de paginación
        pages = (total + paginacion.size - 1) // paginacion.size
        has_next = paginacion.page < pages
        has_prev = paginacion.page > 1
        
        return PaginacionResponse(
            items=[MovimientoBancarioResponse.from_orm(mov) for mov in movimientos],
            total=total,
            page=paginacion.page,
            size=paginacion.size,
            pages=pages,
            has_next=has_next,
            has_prev=has_prev
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listando movimientos: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno: {str(e)}"
        )


@router.get("/archivos/{empresa_id}", response_model=List[ArchivoBancarioResponse])
async def listar_archivos_bancarios(
    empresa_id: int,
    limit: int = Query(50, ge=1, le=200, description="Límite de resultados"),
    db: Session = Depends(get_db)
):
    """
    Lista archivos bancarios procesados para una empresa
    
    - **empresa_id**: ID de la empresa
    - **limit**: Límite de resultados (por defecto 50, máximo 200)
    
    Retorna lista de archivos bancarios con metadatos de procesamiento.
    """
    try:
        # Validar empresa
        empresa = db.query(EmpresaContribuyente).filter(
            EmpresaContribuyente.id == empresa_id
        ).first()
        
        if not empresa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Empresa con ID {empresa_id} no encontrada"
            )
        
        # Obtener archivos
        archivos = db.query(ArchivoBancario).filter(
            ArchivoBancario.empresa_id == empresa_id
        ).order_by(desc(ArchivoBancario.fecha_creacion)).limit(limit).all()
        
        return [ArchivoBancarioResponse.from_orm(archivo) for archivo in archivos]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listando archivos: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno: {str(e)}"
        )


@router.get("/estadisticas/{empresa_id}")
async def obtener_estadisticas_generales(
    empresa_id: int,
    db: Session = Depends(get_db)
):
    """
    Obtiene estadísticas generales de conciliación para una empresa
    
    - **empresa_id**: ID de la empresa
    
    Retorna estadísticas resumidas de todos los períodos procesados.
    """
    try:
        # Validar empresa
        empresa = db.query(EmpresaContribuyente).filter(
            EmpresaContribuyente.id == empresa_id
        ).first()
        
        if not empresa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Empresa con ID {empresa_id} no encontrada"
            )
        
        # Estadísticas de movimientos - usando subconsultas para compatibilidad con MySQL
        total_movimientos = db.query(func.count(MovimientoBancario.id)).filter(
            MovimientoBancario.empresa_id == empresa_id
        ).scalar() or 0
        
        conciliados = db.query(func.count(MovimientoBancario.id)).filter(
            and_(
                MovimientoBancario.empresa_id == empresa_id,
                MovimientoBancario.estado == EstadoConciliacion.CONCILIADO
            )
        ).scalar() or 0
        
        pendientes = db.query(func.count(MovimientoBancario.id)).filter(
            and_(
                MovimientoBancario.empresa_id == empresa_id,
                MovimientoBancario.estado == EstadoConciliacion.PENDIENTE
            )
        ).scalar() or 0
        
        monto_total = db.query(func.sum(MovimientoBancario.monto)).filter(
            MovimientoBancario.empresa_id == empresa_id
        ).scalar() or 0
        
        # Estadísticas de archivos - usando subconsultas para compatibilidad con MySQL
        total_archivos = db.query(func.count(ArchivoBancario.id)).filter(
            ArchivoBancario.empresa_id == empresa_id
        ).scalar() or 0
        
        archivos_exitosos = db.query(func.count(ArchivoBancario.id)).filter(
            and_(
                ArchivoBancario.empresa_id == empresa_id,
                ArchivoBancario.procesado_exitosamente == True
            )
        ).scalar() or 0
        
        # Últimos resultados de conciliación
        ultimos_resultados = db.query(ResultadoConciliacion).filter(
            ResultadoConciliacion.empresa_id == empresa_id
        ).order_by(desc(ResultadoConciliacion.fecha_proceso)).limit(5).all()
        
        return {
            "empresa": {
                "id": empresa.id,
                "rfc": empresa.rfc,
                "razon_social": empresa.razon_social
            },
            "movimientos": {
                "total": total_movimientos,
                "conciliados": conciliados,
                "pendientes": pendientes,
                "porcentaje_conciliacion": (
                    (conciliados / total_movimientos * 100) if total_movimientos > 0 else 0
                ),
                "monto_total": float(monto_total)
            },
            "archivos": {
                "total_procesados": total_archivos,
                "exitosos": archivos_exitosos,
                "tasa_exito": (
                    (archivos_exitosos / total_archivos * 100) if total_archivos > 0 else 0
                )
            },
            "ultimos_procesos": [
                {
                    "fecha": resultado.fecha_proceso.isoformat(),
                    "periodo": f"{resultado.periodo_inicio.strftime('%m/%Y')}",
                    "movimientos_conciliados": resultado.movimientos_conciliados,
                    "total_movimientos": resultado.total_movimientos_bancarios,
                    "porcentaje": (
                        resultado.movimientos_conciliados / resultado.total_movimientos_bancarios * 100
                        if resultado.total_movimientos_bancarios > 0 else 0
                    )
                }
                for resultado in ultimos_resultados
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno: {str(e)}"
        )


@router.get("/empresas", response_model=List[Dict[str, Any]])
async def obtener_empresas_contribuyentes(db: Session = Depends(get_db)):
    """
    Obtener lista de empresas/contribuyentes disponibles
    """
    try:
        empresas = db.query(EmpresaContribuyente).all()
        
        return [
            {
                "id": empresa.id,
                "rfc": empresa.rfc,
                "razon_social": empresa.razon_social,
                "correo_electronico": getattr(empresa, 'correo_electronico', None),
                "fecha_expiracion": getattr(empresa, 'fecha_expiracion', None)
            }
            for empresa in empresas
        ]
    except Exception as e:
        logger.error(f"Error obteniendo empresas: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo empresas: {str(e)}"
        )


# === ENDPOINTS ADICIONALES PARA GESTIÓN ===

@router.patch("/movimientos/{movimiento_id}")
async def actualizar_movimiento(
    movimiento_id: int,
    estado: Optional[EstadoConciliacion] = None,
    notas: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Actualiza un movimiento bancario específico
    
    Permite cambiar el estado y agregar notas manualmente.
    """
    try:
        movimiento = db.query(MovimientoBancario).filter(
            MovimientoBancario.id == movimiento_id
        ).first()
        
        if not movimiento:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Movimiento con ID {movimiento_id} no encontrado"
            )
        
        if estado:
            movimiento.estado = estado
            if estado == EstadoConciliacion.MANUAL:
                movimiento.metodo_conciliacion = MetodoConciliacion.MANUAL
                movimiento.fecha_conciliacion = datetime.now()
        
        if notas is not None:
            movimiento.notas = notas
        
        db.commit()
        
        return {"mensaje": "Movimiento actualizado exitosamente"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error actualizando movimiento: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno: {str(e)}"
        ) 