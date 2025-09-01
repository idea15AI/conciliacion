from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exception_handlers import http_exception_handler
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from contextlib import asynccontextmanager
from pydantic import BaseModel
from typing import Optional
import logging
import time
from datetime import datetime

from app.core.config import settings
from app.core.database import test_db_connection, init_db

# Simple response models
class HealthResponse(BaseModel):
    status: str
    db_connection: bool
    version: str
    timestamp: datetime

class ErrorResponse(BaseModel):
    error: str
    code: Optional[int] = None
    detail: Optional[str] = None

# Importar routers de conciliación
from app.conciliacion.routes.conciliacion import router as conciliacion_router
from app.conciliacion.routes.archivos_bancarios import router as archivos_bancarios_router
from app.conciliacion.routes.procesar_pdf_unificado import router as procesar_pdf_unificado_router
from app.conciliacion.routes.lista_negra import router as lista_negra_router


# Configurar logging
logging.basicConfig(
    level=logging.DEBUG,  # Temporalmente activar DEBUG para diagnosticar extracción
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Eventos de inicio y cierre de la aplicación"""
    
    # Inicio de la aplicación
    logger.info("🚀 Iniciando Sistema de Conciliación Bancaria...")
    
    # Verificar configuración de Gemini
    try:
        from app.core.config import settings
        gemini_key = settings.GEMINI_API_KEY
        logger.info(f"🔧 Verificando configuración de Gemini...")
        logger.info(f"🔑 GEMINI_API_KEY configurada: {'Sí' if gemini_key else 'No'}")
        if gemini_key:
            logger.info(f"🔑 API Key: {gemini_key[:10]}...{gemini_key[-4:]}")
        else:
            logger.warning("⚠️ GEMINI_API_KEY no encontrada en configuración")
    except Exception as e:
        logger.error(f"❌ Error verificando configuración de Gemini: {e}")
    
    # Inicializar base de datos
    try:
        from app.core.database import init_db
        init_db()
        logger.info("✅ Base de datos inicializada correctamente")
    except Exception as e:
        logger.error(f"❌ Error inicializando base de datos: {e}")
    
    logger.info("✅ Sistema de Conciliación Bancaria iniciado correctamente")
    
    yield
    
    # Cierre de la aplicación
    logger.info("🔄 Cerrando Sistema de Conciliación Bancaria...")

# Crear aplicación FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Sistema inteligente para procesamiento y consulta de CFDIs - Reorganizado con módulos separados",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configurar CORS para Next.js (http://localhost:3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js development
        "http://127.0.0.1:3000",  # Alternative localhost
        "https://localhost:3000", # HTTPS version
        "http://localhost:3001",  # Next.js development (alternate port)
        "http://127.0.0.1:3001",  # Alternative localhost
        "null",  # Para archivos HTML locales (file://)
        *settings.cors_origins_list  # Otros orígenes configurados
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=[
        "Content-Type", 
        "Authorization", 
        "Accept", 
        "Origin", 
        "User-Agent", 
        "DNT", 
        "Cache-Control", 
        "X-Mx-ReqToken", 
        "Keep-Alive", 
        "X-Requested-With", 
        "If-Modified-Since"
    ],
)

# Middleware para logging de requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # Log request
    logger.info(f"📥 Request: {request.method} {request.url}")
    
    response = await call_next(request)
    
    # Log response
    process_time = time.time() - start_time
    logger.info(f"📤 Response: {response.status_code} - {process_time:.4f}s")
    
    return response

# Manejador de errores global
@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    logger.error(f"❌ HTTP Exception: {exc.status_code} - {exc.detail}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail,
            code=exc.status_code
        ).dict()
    )



@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"💥 Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Error interno del servidor",
            detail=str(exc) if settings.DEBUG else None
        ).dict()
    )

# =============================================================================
# INCLUIR ROUTERS ORGANIZADOS
# =============================================================================

# Router de Conciliación Bancaria
app.include_router(
    conciliacion_router,
    prefix="/api/v1",
    tags=["🏦 Conciliación Bancaria"]
)

# Router de Archivos Bancarios
app.include_router(
    archivos_bancarios_router,
    prefix="/api/v1",
    tags=["📁 Archivos Bancarios"]
)

# Router de Procesamiento Unificado
app.include_router(
    procesar_pdf_unificado_router,
    prefix="/api/v1",
    tags=["🚀 Procesamiento Unificado"]
)

# Router de Conciliación
app.include_router(
    conciliacion_router,
    prefix="/api/v1",
    tags=["🎯 Conciliación"]
)

# Router de Lista Negra SAT
app.include_router(
    lista_negra_router,
    prefix="/api/v1",
    tags=["🚨 Lista Negra SAT"]
)

# Montar archivos estáticos
app.mount("/static", StaticFiles(directory="frontend"), name="static")

# =============================================================================
# ENDPOINTS PRINCIPALES
# =============================================================================

@app.get("/", include_in_schema=False)
async def root():
    """Endpoint raíz - redirige a documentación"""
    return JSONResponse(content={
        "message": "Sistema de Conciliación Bancaria",
        "version": settings.APP_VERSION,
        "modules": {
            "conciliacion": "/api/v1/conciliacion"
        },
        "docs": "/docs",
        "redoc": "/redoc",
        "cors_enabled": True,
        "frontend_url": "http://localhost:3000",
        "dashboard": "/static/conciliacion_dashboard.html"
    })

@app.get("/dashboard", include_in_schema=False)
async def dashboard():
    """Endpoint para el dashboard de conciliación"""
    from fastapi.responses import FileResponse
    return FileResponse("frontend/conciliacion_dashboard.html")

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Endpoint de health check global
    """
    try:
        # Verificar conexión a base de datos
        db_connection = test_db_connection()
        
        status = "healthy" if db_connection else "unhealthy"
        
        return HealthResponse(
            status=status,
            db_connection=db_connection,
            version=settings.APP_VERSION,
            timestamp=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"❌ Error en health check: {e}")
        return JSONResponse(
            status_code=503,
            content=HealthResponse(
                status="unhealthy",
                db_connection=False,
                version=settings.APP_VERSION,
                timestamp=datetime.now()
            ).dict()
        )

@app.get("/info")
async def get_app_info():
    """
    Información de la aplicación - Solo conciliación
    """
    return JSONResponse(content={
        "app_name": "Sistema de Conciliación Bancaria",
        "version": settings.APP_VERSION,
        "debug": settings.DEBUG,
        "structure": "Módulo de conciliación bancaria únicamente",
        "modules": {
            "conciliacion": {
                "description": "Sistema avanzado de conciliación bancaria con OCR",
                "endpoints": "/api/v1/conciliacion/*",
                "features": [
                    "OCR con OpenAI Vision API", 
                    "Algoritmo de conciliación ultra-preciso",
                    "Soporte para bancos mexicanos",
                    "Sistema de alertas y reportes"
                ]
            }
        },
        "database_url": settings.DATABASE_URL.replace(settings.DB_PASSWORD, "***") if settings.DATABASE_URL else None,
        "max_file_size": settings.MAX_FILE_SIZE,
        "allowed_extensions": settings.allowed_extensions_list,
        "cors_origins": [
            "http://localhost:3000",
            "http://127.0.0.1:3000", 
            "https://localhost:3000",
            *settings.cors_origins_list
        ]
    })

@app.get("/modules")
async def get_modules_info():
    """
    Información detallada del módulo de conciliación
    """
    return JSONResponse(content={
        "modules": {
            "conciliacion": {
                "name": "Sistema de Conciliación Bancaria",
                "prefix": "/api/v1/conciliacion",
                "description": "Conciliación automática de estados de cuenta bancarios con CFDIs",
                "main_endpoints": [
                    "POST /subir-estado-cuenta - Subir PDF bancario para OCR",
                    "POST /ejecutar - Ejecutar conciliación automática", 
                    "GET /reporte/{empresa_id} - Obtener reporte de conciliación",
                    "GET /movimientos/{empresa_id} - Listar movimientos bancarios",
                    "GET /health - Estado del sistema de conciliación"
                ]
            }
        },
        "cors_enabled": True,
        "frontend_support": "http://localhost:3000",
        "documentation": "/docs"
    })

@app.get("/gemini-interface")
async def gemini_interface():
    """Sirve la interfaz HTML de Gemini."""
    return FileResponse("frontend/gemini_upload.html")

@app.get("/simple-interface")
async def simple_interface():
    """Sirve la interfaz simple de procesamiento."""
    return FileResponse("frontend/simple_pdf_processor.html")

@app.get("/pdf-processor")
async def pdf_processor_interface():
    """Sirve la interfaz de procesamiento de PDFs con Gemini"""
    return FileResponse("frontend/simple_pdf_processor.html")

@app.get("/conciliacion-dashboard")
async def conciliacion_dashboard():
    """Sirve el dashboard de conciliación bancaria"""
    return FileResponse("frontend/conciliacion_dashboard.html")
@app.get("/bbva-ocr")
async def bbva_ocr_page():
    """Página para OCR de BBVA"""
    from pathlib import Path
    html_path = Path("frontend/bbva_ocr_result.html")
    return FileResponse(html_path)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.core.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    ) 