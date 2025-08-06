"""
Modelos de base de datos para el módulo de conciliación bancaria
"""

from sqlalchemy import Column, Integer, String, DECIMAL, DateTime, Boolean, Text, JSON, ForeignKey, Index, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum as PyEnum

from app.core.database import Base
from app.models.mysql_models import EmpresaContribuyente, ComprobanteFiscal


# === ENUMS ===

class TipoMovimiento(PyEnum):
    """Tipo de movimiento bancario"""
    CARGO = "cargo"
    ABONO = "abono"


class EstadoConciliacion(PyEnum):
    """Estado de conciliación del movimiento"""
    PENDIENTE = "pendiente"
    CONCILIADO = "conciliado"
    MANUAL = "manual"
    DESCARTADO = "descartado"


class MetodoConciliacion(PyEnum):
    """Método usado para conciliar el movimiento"""
    EXACTO = "exacto"
    REFERENCIA = "referencia"
    APROXIMADO = "aproximado"
    COMPLEMENTO_PPD = "complemento_ppd"
    HEURISTICA = "heuristica"
    ML_PATRON = "ml_patron"
    MANUAL = "manual"


class TipoBanco(PyEnum):
    """Bancos soportados en México"""
    BBVA = "bbva"
    SANTANDER = "santander"
    BANAMEX = "banamex"
    BANORTE = "banorte"
    HSBC = "hsbc"
    SCOTIABANK = "scotiabank"
    INBURSA = "inbursa"
    AZTECA = "azteca"
    OTRO = "otro"


# === MODELOS ===

class MovimientoBancario(Base):
    """
    Modelo para movimientos bancarios extraídos de estados de cuenta
    
    Almacena cada transacción bancaria con información detallada para conciliación
    """
    __tablename__ = "movimientos_bancarios"
    
    # Campos principales
    id = Column(Integer, primary_key=True, autoincrement=True)
    empresa_id = Column(Integer, ForeignKey("empresas_contribuyentes.id", ondelete="CASCADE"), nullable=False)
    
    # Información del movimiento
    fecha = Column(DateTime, nullable=False)
    concepto = Column(Text, nullable=False)  # Concepto completo del movimiento
    monto = Column(DECIMAL(12, 2), nullable=False)
    tipo = Column(Enum(TipoMovimiento), nullable=False)
    referencia = Column(String(255))  # Referencia bancaria
    saldo = Column(DECIMAL(12, 2))  # Saldo después del movimiento
    
    # Estados de conciliación
    estado = Column(Enum(EstadoConciliacion), default=EstadoConciliacion.PENDIENTE)
    cfdi_uuid = Column(String(36, collation='utf8mb4_general_ci'), ForeignKey("comprobantes_fiscales.uuid", ondelete="SET NULL"))
    nivel_confianza = Column(DECIMAL(3, 2))  # 0.00 a 1.00
    metodo_conciliacion = Column(Enum(MetodoConciliacion))
    
    # Metadatos
    archivo_origen_id = Column(Integer, ForeignKey("archivos_bancarios.id", ondelete="SET NULL"))
    datos_ocr = Column(JSON)  # Datos raw del OCR
    notas = Column(Text)  # Notas adicionales o observaciones
    
    # Timestamps
    fecha_creacion = Column(DateTime, nullable=False, default=func.current_timestamp())
    fecha_actualizacion = Column(DateTime, nullable=False, default=func.current_timestamp(), onupdate=func.current_timestamp())
    fecha_conciliacion = Column(DateTime)  # Cuando se concilió
    
    # Relaciones
    empresa = relationship("EmpresaContribuyente", back_populates="movimientos_bancarios")
    comprobante_fiscal = relationship("ComprobanteFiscal", back_populates="movimientos_bancarios")
    archivo_origen = relationship("ArchivoBancario", back_populates="movimientos")
    
    # Índices para optimización
    __table_args__ = (
        Index('idx_movimiento_empresa_fecha', 'empresa_id', 'fecha'),
        Index('idx_movimiento_estado', 'estado'),
        Index('idx_movimiento_monto', 'monto'),
        Index('idx_movimiento_cfdi_uuid', 'cfdi_uuid'),
        Index('idx_movimiento_concepto', 'concepto', mysql_length=100),  # Índice parcial para MySQL
    )
    
    def __repr__(self):
        return f"<MovimientoBancario(id={self.id}, fecha={self.fecha}, monto={self.monto}, estado='{self.estado}')>"


class ArchivoBancario(Base):
    """
    Modelo para tracking de archivos bancarios procesados
    
    Mantiene registro de cada archivo PDF procesado para evitar duplicados
    """
    __tablename__ = "archivos_bancarios"
    
    # Campos principales
    id = Column(Integer, primary_key=True, autoincrement=True)
    empresa_id = Column(Integer, ForeignKey("empresas_contribuyentes.id", ondelete="CASCADE"), nullable=False)
    
    # Información del archivo
    nombre_archivo = Column(String(255), nullable=False)
    hash_archivo = Column(String(64), nullable=False, unique=True)  # SHA-256 del archivo
    tamano_bytes = Column(Integer, nullable=False)
    
    # Información bancaria detectada
    banco = Column(Enum(TipoBanco), nullable=False)
    numero_cuenta = Column(String(50))
    periodo_inicio = Column(DateTime)
    periodo_fin = Column(DateTime)
    saldo_inicial = Column(DECIMAL(12, 2))
    saldo_final = Column(DECIMAL(12, 2))
    
    # Estadísticas de procesamiento
    total_movimientos = Column(Integer, default=0)
    movimientos_procesados = Column(Integer, default=0)
    errores_ocr = Column(JSON)  # Lista de errores durante OCR
    tiempo_procesamiento = Column(Integer)  # Segundos
    
    # Metadatos OCR
    paginas_procesadas = Column(Integer, default=0)
    datos_metadata = Column(JSON)  # Metadatos adicionales del PDF
    
    # Estados
    procesado_exitosamente = Column(Boolean, default=False)
    
    # Timestamps
    fecha_creacion = Column(DateTime, nullable=False, default=func.current_timestamp())
    fecha_procesamiento = Column(DateTime)
    
    # Relaciones
    empresa = relationship("EmpresaContribuyente", back_populates="archivos_bancarios")
    movimientos = relationship("MovimientoBancario", back_populates="archivo_origen")
    
    # Índices
    __table_args__ = (
        Index('idx_archivo_empresa', 'empresa_id'),
        Index('idx_archivo_hash', 'hash_archivo'),
        Index('idx_archivo_banco_periodo', 'banco', 'periodo_inicio', 'periodo_fin'),
    )
    
    def __repr__(self):
        return f"<ArchivoBancario(id={self.id}, nombre='{self.nombre_archivo}', banco='{self.banco}')>" 