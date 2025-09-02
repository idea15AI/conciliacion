# app/core/main.py
from __future__ import annotations

import os
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.core.settings import settings
from app.core.database import test_db_connection, init_db

# ===== Modelos simples =====
class HealthResponse(BaseModel):
    status: str
    db_connection: bool
    version: str
    timestamp: datetime

class ErrorResponse(BaseModel):
    error: str
    code: Optional[int] = None
    detail: Optional[str] = None

# ===== Routers =====
from app.conciliacion.routes.conciliacion import router as conciliacion_router
from app.conciliacion.routes.archivos_bancarios import router as archivos_bancarios_router
from app.conciliacion.routes.procesar_pdf_unificado import router as procesar_pdf_unificado_router
from app.conciliacion.routes.lista_negra import router as lista_negra_router

# ===== Logging =====
LOG_LEVEL = getattr(settings, "LOG_LEVEL", "INFO")
logging.basicConfig(
    level=getattr(logging, str(LOG_LEVEL).upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ===== Paths (frontend opcional) =====
# main.py está en app/core/, por eso parents[2] apunta a la raíz del repo
BASE_DIR = Path(__file__).resolve().parents[2]
FRONTEND_DIR = BASE_DIR / "frontend"

# ===== App =====
from contextlib import asynccontextmanager
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Iniciando Sistema de Conciliación Bancaria...")

    # Mostrar si hay clave de Gemini configurada (sin exponerla completa)
    try:
        gkey = settings.GEMINI_API_KEY.get_secret_value() if settings.GEMINI_API_KEY else ""
        logger.info("🔧 Verificando configuración de Gemini...")
        logger.info(f"🔑 GEMINI_API_KEY configurada: {'Sí' if gkey else 'No'}")
        if gkey:
            logger.info(f"🔑 API Key (parcial): {gkey[:10]}...{gkey[-4:]}")
    except Exception as e:
        logger.warning(f"❌ No se pudo leer GEMINI_API_KEY: {e}")

    # DB init
    try:
        init_db()
        logger.info("✅ Base de datos inicializada correctamente")
    except Exception as e:
        logger.error(f"❌ Error inicializando base de datos: {e}")

    yield
    logger.info("🔄 Cerrando Sistema de Conciliación Bancaria...")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Sistema inteligente para procesamiento y consulta de CFDIs",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ===== CORS =====
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://conciliaci-n-front.vercel.app",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "null",
        *settings.cors_origins_list,
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=[
        "Content-Type", "Authorization", "Accept", "Origin", "User-Agent", "DNT",
        "Cache-Control", "X-Mx-ReqToken", "Keep-Alive", "X-Requested-With", "If-Modified-Since",
    ],
)

# ===== Middleware de logs =====
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    logger.info(f"📥 {request.method} {request.url}")
    resp = await call_next(request)
    logger.info(f"📤 {resp.status_code} - {time.time() - start:.4f}s")
    return resp

# ===== Manejadores de errores =====
@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    logger.error(f"❌ HTTP {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(error=exc.detail, code=exc.status_code).model_dump(),
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"💥 Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Error interno del servidor",
            detail=str(exc) if settings.DEBUG else None,
        ).model_dump(),
    )

# ===== Routers =====
app.include_router(conciliacion_router,        prefix="/api/v1", tags=["🏦 Conciliación Bancaria"])
app.include_router(archivos_bancarios_router,  prefix="/api/v1", tags=["📁 Archivos Bancarios"])
app.include_router(procesar_pdf_unificado_router, prefix="/api/v1", tags=["🚀 Procesamiento Unificado"])
app.include_router(lista_negra_router,         prefix="/api/v1", tags=["🚨 Lista Negra SAT"])
# Nota: se eliminó el include duplicado de conciliación

# ===== Static (solo si existe el frontend) =====
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
    logger.info(f"🗂️ Static montado en /static desde {FRONTEND_DIR}")
else:
    logger.warning(f"⚠️ Carpeta de frontend no encontrada: {FRONTEND_DIR}. Se omite el mount.")

# ===== Helpers para servir archivos si existen =====
def serve_front_file(filename: str) -> FileResponse:
    path = FRONTEND_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Archivo no encontrado: {filename}")
    return FileResponse(path)

# ===== Endpoints =====
@app.get("/", include_in_schema=False)
async def root():
    return {
        "message": "Sistema de Conciliación Bancaria",
        "version": settings.APP_VERSION,
        "modules": {"conciliacion": "/api/v1/conciliacion"},
        "docs": "/docs",
        "redoc": "/redoc",
        "cors_enabled": True,
        "frontend_present": FRONTEND_DIR.exists(),
        "dashboard": "/static/conciliacion_dashboard.html" if FRONTEND_DIR.exists() else None,
    }

@app.get("/dashboard", include_in_schema=False)
async def dashboard():
    return serve_front_file("conciliacion_dashboard.html")

@app.get("/gemini-interface")
async def gemini_interface():
    return serve_front_file("gemini_upload.html")

@app.get("/simple-interface")
async def simple_interface():
    return serve_front_file("simple_pdf_processor.html")

@app.get("/pdf-processor")
async def pdf_processor_interface():
    return serve_front_file("simple_pdf_processor.html")

@app.get("/conciliacion-dashboard")
async def conciliacion_dashboard():
    return serve_front_file("conciliacion_dashboard.html")

@app.get("/bbva-ocr")
async def bbva_ocr_page():
    return serve_front_file("bbva_ocr_result.html")

@app.get("/health", response_model=HealthResponse)
async def health_check():
    try:
        ok = test_db_connection()
        return HealthResponse(
            status="healthy" if ok else "unhealthy",
            db_connection=ok,
            version=settings.APP_VERSION,
            timestamp=datetime.now(),
        )
    except Exception as e:
        logger.error(f"❌ Error en health: {e}")
        return JSONResponse(
            status_code=503,
            content=HealthResponse(
                status="unhealthy",
                db_connection=False,
                version=settings.APP_VERSION,
                timestamp=datetime.now(),
            ).model_dump(),
        )

@app.get("/info")
async def get_app_info():
    return {
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "debug": settings.DEBUG,
        "structure": "Módulo de conciliación bancaria",
        "modules": {
            "conciliacion": {
                "description": "Conciliación bancaria con OCR",
                "endpoints": "/api/v1/conciliacion/*",
                "features": [
                    "OCR con OpenAI/Gemini",
                    "Algoritmo de conciliación",
                    "Soporte bancos MX",
                    "Alertas y reportes",
                ],
            }
        },
        # No exponemos URL con credenciales para evitar leaks
        "max_file_size": settings.MAX_FILE_SIZE,
        "allowed_extensions": settings.allowed_extensions_list,
        "cors_origins": [
            "https://conciliaci-n-front.vercel.app",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "https://localhost:3000",
            *settings.cors_origins_list,
        ],
        "frontend_present": FRONTEND_DIR.exists(),
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.core.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=settings.DEBUG,
        log_level=str(LOG_LEVEL).lower(),
    )
