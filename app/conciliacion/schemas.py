"""
Schemas Pydantic para el módulo de conciliación bancaria
"""

from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel

from .models import TipoBanco


class ArchivoBancarioResponse(BaseModel):
    """Schema de respuesta para archivo bancario"""
    id: int
    empresa_id: int
    nombre_archivo: str
    banco: str
    total_movimientos: int = 0
    movimientos_procesados: int = 0
    procesado_exitosamente: bool = False
    fecha_creacion: datetime
    fecha_procesamiento: Optional[datetime] = None
    tiempo_procesamiento: Optional[int] = None
    resultado_procesamiento: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True 