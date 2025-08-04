from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exception_handlers import http_exception_handler
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

# Importar solo el router de conciliación
from app.conciliacion.router import router as conciliacion_router
from app.conciliacion.exceptions import ConciliacionError, get_http_status_code

# Configurar logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Eventos de inicio y cierre de la aplicación
    """
    # Startup
    logger.info("🚀 Iniciando Sistema de Conciliación Bancaria...")
    
    # Probar conexión a base de datos
    if not test_db_connection():
        logger.error("❌ No se pudo conectar a la base de datos")
        raise Exception("Error de conexión a la base de datos")
    
    # Inicializar base de datos
    try:
        init_db()
        logger.info("✅ Base de datos inicializada correctamente")
    except Exception as e:
        logger.error(f"❌ Error inicializando base de datos: {e}")
        raise
    
    # Verificar configuración de OpenAI para OCR
    if not settings.OPENAI_API_KEY:
        logger.warning("⚠️  OpenAI API Key no configurada - El OCR no funcionará")
    
    logger.info("✅ Sistema de Conciliación Bancaria iniciado correctamente")
    yield
    
    # Shutdown
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

@app.exception_handler(ConciliacionError)
async def conciliacion_exception_handler(request: Request, exc: ConciliacionError):
    """Manejador específico para excepciones de conciliación"""
    logger.error(f"❌ Conciliación Error: {exc}")
    
    status_code = get_http_status_code(exc)
    return JSONResponse(
        status_code=status_code,
        content=exc.to_dict()
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
        "frontend_url": "http://localhost:3000"
    })

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.core.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    ) 