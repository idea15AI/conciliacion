"""
Schemas Pydantic para el módulo de conciliación bancaria avanzada

Define los esquemas de entrada y salida para las APIs de conciliación
"""

from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, validator, constr
from enum import Enum
import re

from .models import TipoMovimiento, EstadoConciliacion, MetodoConciliacion, TipoBanco


# === VALIDATORS REUTILIZABLES ===

def validar_rfc(rfc: str) -> str:
    """Validador de RFC mexicano"""
    if not rfc:
        raise ValueError("RFC es requerido")
    
    rfc = rfc.upper().strip()
    
    # Patrón RFC persona física: 4 letras + 6 dígitos + 3 caracteres
    patron_fisica = r'^[A-Z&Ñ]{4}[0-9]{6}[A-Z0-9]{3}$'
    # Patrón RFC persona moral: 3 letras + 6 dígitos + 3 caracteres  
    patron_moral = r'^[A-Z&Ñ]{3}[0-9]{6}[A-Z0-9]{3}$'
    
    if not (re.match(patron_fisica, rfc) or re.match(patron_moral, rfc)):
        raise ValueError("Formato de RFC inválido")
    
    return rfc


# === SCHEMAS BASE ===

class MovimientoBancarioBase(BaseModel):
    """Schema base para movimientos bancarios"""
    fecha: datetime = Field(..., description="Fecha del movimiento bancario")
    concepto: str = Field(..., min_length=1, max_length=2000, description="Concepto del movimiento")
    monto: Decimal = Field(..., gt=0, description="Monto del movimiento (positivo)")
    tipo: TipoMovimiento = Field(..., description="Tipo de movimiento (cargo/abono)")
    referencia: Optional[str] = Field(None, max_length=255, description="Referencia bancaria")
    saldo: Optional[Decimal] = Field(None, description="Saldo después del movimiento")
    
    @validator('concepto')
    def validar_concepto(cls, v):
        if not v or not v.strip():
            raise ValueError("Concepto no puede estar vacío")
        return v.strip()
    
    @validator('monto')
    def validar_monto(cls, v):
        if v <= 0:
            raise ValueError("Monto debe ser mayor a 0")
        # Limitar a 2 decimales
        return round(v, 2)


class MovimientoBancarioCreate(MovimientoBancarioBase):
    """Schema para crear movimiento bancario"""
    empresa_id: int = Field(..., gt=0, description="ID de la empresa")
    datos_ocr: Optional[Dict[str, Any]] = Field(None, description="Datos raw del OCR")
    archivo_origen_id: Optional[int] = Field(None, description="ID del archivo de origen")
    
    class Config:
        json_schema_extra = {
            "example": {
                "empresa_id": 1,
                "fecha": "2024-01-15T10:30:00",
                "concepto": "PAGO FACTURA A1234 EMPRESA XYZ SA DE CV",
                "monto": 1250.50,
                "tipo": "cargo",
                "referencia": "REF123456789",
                "saldo": 45320.75
            }
        }


class MovimientoBancarioUpdate(BaseModel):
    """Schema para actualizar movimiento bancario"""
    estado: Optional[EstadoConciliacion] = None
    cfdi_uuid: Optional[str] = Field(None, min_length=36, max_length=36)
    nivel_confianza: Optional[Decimal] = Field(None, ge=0, le=1)
    metodo_conciliacion: Optional[MetodoConciliacion] = None
    notas: Optional[str] = Field(None, max_length=2000)
    
    @validator('cfdi_uuid')
    def validar_uuid(cls, v):
        if v and len(v) != 36:
            raise ValueError("UUID debe tener exactamente 36 caracteres")
        return v


class MovimientoBancarioResponse(MovimientoBancarioBase):
    """Schema de respuesta para movimiento bancario"""
    id: int
    empresa_id: int
    estado: EstadoConciliacion
    cfdi_uuid: Optional[str] = None
    nivel_confianza: Optional[Decimal] = None
    metodo_conciliacion: Optional[MetodoConciliacion] = None
    notas: Optional[str] = None
    fecha_creacion: datetime
    fecha_actualizacion: datetime
    fecha_conciliacion: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# === SCHEMAS PARA ARCHIVOS BANCARIOS ===

class ArchivoBancarioCreate(BaseModel):
    """Schema para crear archivo bancario"""
    empresa_id: int = Field(..., gt=0)
    nombre_archivo: str = Field(..., min_length=1, max_length=255)
    hash_archivo: str = Field(..., min_length=64, max_length=64)
    tamano_bytes: int = Field(..., gt=0)
    banco: TipoBanco
    numero_cuenta: Optional[str] = Field(None, max_length=50)
    periodo_inicio: Optional[datetime] = None
    periodo_fin: Optional[datetime] = None
    saldo_inicial: Optional[Decimal] = None
    saldo_final: Optional[Decimal] = None


class ArchivoBancarioResponse(ArchivoBancarioCreate):
    """Schema de respuesta para archivo bancario"""
    id: int
    total_movimientos: int = 0
    movimientos_procesados: int = 0
    procesado_exitosamente: bool = False
    fecha_creacion: datetime
    fecha_procesamiento: Optional[datetime] = None
    tiempo_procesamiento: Optional[int] = None
    
    class Config:
        from_attributes = True


# === SCHEMAS PARA CONCILIACIÓN ===

class ConciliacionRequest(BaseModel):
    """Schema para solicitud de conciliación"""
    rfc_empresa: constr(pattern=r'^[A-Z&Ñ]{3,4}[0-9]{6}[A-Z0-9]{3}$') = Field(
        ..., description="RFC de la empresa a conciliar"
    )
    mes: int = Field(..., ge=1, le=12, description="Mes a conciliar (1-12)")
    anio: int = Field(..., ge=2000, le=2030, description="Año a conciliar")
    tolerancia_monto: Optional[Decimal] = Field(
        Decimal('1.00'), ge=0, description="Tolerancia en pesos para matching aproximado"
    )
    dias_tolerancia: Optional[int] = Field(
        3, ge=0, le=30, description="Días de tolerancia para matching de fechas"
    )
    forzar_reproceso: Optional[bool] = Field(
        False, description="Forzar reproceso aunque ya exista conciliación"
    )
    
    @validator('rfc_empresa')
    def validar_rfc_empresa(cls, v):
        return validar_rfc(v)
    
    class Config:
        json_schema_extra = {
            "example": {
                "rfc_empresa": "ABC123456789",
                "mes": 1,
                "anio": 2024,
                "tolerancia_monto": 1.0,
                "dias_tolerancia": 3,
                "forzar_reproceso": False
            }
        }


class EstadisticasConciliacion(BaseModel):
    """Estadísticas detalladas de conciliación"""
    total_movimientos_bancarios: int = 0
    total_cfdis_periodo: int = 0
    movimientos_conciliados: int = 0
    movimientos_pendientes: int = 0
    movimientos_descartados: int = 0
    movimientos_manuales: int = 0
    
    # Por método
    conciliados_exacto: int = 0
    conciliados_referencia: int = 0
    conciliados_aproximado: int = 0
    conciliados_complemento_ppd: int = 0
    conciliados_heuristica: int = 0
    conciliados_ml_patron: int = 0
    
    # Montos
    monto_total_conciliado: Decimal = Decimal('0.00')
    monto_total_pendiente: Decimal = Decimal('0.00')
    monto_total_descartado: Decimal = Decimal('0.00')
    
    # Métricas
    porcentaje_conciliacion: float = 0.0
    nivel_confianza_promedio: Optional[Decimal] = None
    tiempo_procesamiento_segundos: Optional[int] = None


class AlertaCritica(BaseModel):
    """Schema para alertas críticas"""
    tipo: str = Field(..., description="Tipo de alerta")
    mensaje: str = Field(..., description="Mensaje descriptivo")
    gravedad: str = Field(..., description="Nivel de gravedad: bajo, medio, alto")
    datos_adicionales: Optional[Dict[str, Any]] = None


class SugerenciaConciliacion(BaseModel):
    """Schema para sugerencias de conciliación"""
    movimiento_id: int = Field(..., description="ID del movimiento bancario")
    cfdi_uuid: Optional[str] = Field(None, description="UUID del CFDI sugerido")
    nivel_confianza: Decimal = Field(..., ge=0, le=1, description="Nivel de confianza")
    razon: str = Field(..., description="Razón de la sugerencia")
    datos_comparacion: Dict[str, Any] = Field(..., description="Datos de la comparación")


class ResumenConciliacion(BaseModel):
    """Schema de respuesta para proceso de conciliación"""
    exito: bool
    mensaje: str
    estadisticas: EstadisticasConciliacion
    alertas_criticas: List[AlertaCritica] = []
    sugerencias: List[SugerenciaConciliacion] = []
    fecha_proceso: datetime
    tiempo_total_segundos: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "exito": True,
                "mensaje": "Conciliación completada exitosamente",
                "estadisticas": {
                    "total_movimientos_bancarios": 150,
                    "movimientos_conciliados": 142,
                    "movimientos_pendientes": 8,
                    "porcentaje_conciliacion": 94.67
                },
                "alertas_criticas": [],
                "sugerencias": [],
                "fecha_proceso": "2024-01-15T14:30:00",
                "tiempo_total_segundos": 45
            }
        }


# === SCHEMAS PARA REPORTES ===

class FiltrosMovimientos(BaseModel):
    """Filtros para búsqueda de movimientos"""
    estado: Optional[EstadoConciliacion] = None
    tipo: Optional[TipoMovimiento] = None
    metodo_conciliacion: Optional[MetodoConciliacion] = None
    fecha_inicio: Optional[datetime] = None
    fecha_fin: Optional[datetime] = None
    monto_minimo: Optional[Decimal] = Field(None, ge=0)
    monto_maximo: Optional[Decimal] = Field(None, ge=0)
    concepto_like: Optional[str] = Field(None, max_length=100)
    referencia_like: Optional[str] = Field(None, max_length=50)
    
    @validator('monto_maximo')
    def validar_montos(cls, v, values):
        if v and 'monto_minimo' in values and values['monto_minimo']:
            if v < values['monto_minimo']:
                raise ValueError("Monto máximo debe ser mayor al monto mínimo")
        return v


class ReporteConciliacion(BaseModel):
    """Reporte detallado de conciliación"""
    empresa_id: int
    rfc_empresa: str
    periodo_inicio: datetime
    periodo_fin: datetime
    estadisticas: EstadisticasConciliacion
    movimientos_pendientes: List[MovimientoBancarioResponse] = []
    movimientos_con_alertas: List[MovimientoBancarioResponse] = []
    alertas_criticas: List[AlertaCritica] = []
    sugerencias_mejora: List[str] = []
    fecha_generacion: datetime
    
    class Config:
        from_attributes = True


# === SCHEMAS PARA OCR ===

class SubirEstadoCuentaRequest(BaseModel):
    """Schema para subida de estado de cuenta"""
    rfc_empresa: constr(pattern=r'^[A-Z&Ñ]{3,4}[0-9]{6}[A-Z0-9]{3}$') = Field(
        ..., description="RFC de la empresa"
    )
    
    @validator('rfc_empresa')
    def validar_rfc_empresa(cls, v):
        return validar_rfc(v)
    
    class Config:
        json_schema_extra = {
            "example": {
                "rfc_empresa": "ABC123456789"
            }
        }


class ResultadoOCR(BaseModel):
    """Resultado del procesamiento OCR"""
    exito: bool
    mensaje: str
    archivo_id: Optional[int] = None
    banco_detectado: Optional[TipoBanco] = None
    periodo_detectado: Optional[Dict[str, datetime]] = None
    total_movimientos_extraidos: int = 0
    errores: List[str] = []
    tiempo_procesamiento_segundos: int = 0
    
    class Config:
        json_schema_extra = {
            "example": {
                "exito": True,
                "mensaje": "Estado de cuenta procesado exitosamente",
                "archivo_id": 123,
                "banco_detectado": "bbva",
                "total_movimientos_extraidos": 45,
                "errores": [],
                "tiempo_procesamiento_segundos": 12
            }
        }


# === SCHEMAS PARA PAGINACIÓN ===

class PaginacionRequest(BaseModel):
    """Schema para solicitudes paginadas"""
    page: int = Field(1, ge=1, description="Número de página")
    size: int = Field(50, ge=1, le=1000, description="Tamaño de página")
    sort_by: Optional[str] = Field("fecha", description="Campo de ordenamiento")
    sort_order: Optional[str] = Field("desc", pattern="^(asc|desc)$", description="Orden: asc o desc")


class PaginacionResponse(BaseModel):
    """Schema de respuesta paginada"""
    items: List[Any]
    total: int
    page: int
    size: int
    pages: int
    has_next: bool
    has_prev: bool 