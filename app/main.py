# ARCHIVO DEPRECATED - Usar app/core/main.py
# Este archivo se mantiene por compatibilidad pero se recomienda usar la nueva estructura

from fastapi import FastAPI
from fastapi.responses import JSONResponse
import logging

# Importar la aplicación desde la nueva estructura
from app.core.main import app as new_app

logger = logging.getLogger(__name__)

# Redirigir a la nueva aplicación
app = new_app

# Endpoint de compatibilidad
@app.get("/legacy", include_in_schema=False)
async def legacy_info():
    """Información sobre la migración"""
    return JSONResponse(content={
        "message": "⚠️ Este archivo ha sido reorganizado",
        "new_structure": {
            "main_app": "app/core/main.py",
            "conciliacion_module": "app/conciliacion/"
        },
        "recommendation": "Usar la nueva estructura modular",
        "migration_date": "2024",
        "status": "deprecated_but_functional"
    })

if __name__ == "__main__":
    import uvicorn
    logger.info("🔄 Redirecting to new structure: app.core.main:app")
    uvicorn.run(
        "app.core.main:app",  # Usar la nueva estructura
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 