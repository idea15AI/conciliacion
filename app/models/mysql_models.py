from sqlalchemy import Column, String, DECIMAL, DATETIME, Text, ForeignKey, Integer, Index, Enum, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base

class EmpresaContribuyente(Base):
    """Modelo para tabla empresas_contribuyentes"""
    __tablename__ = "empresas_contribuyentes"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    rfc = Column(String(13))
    razon_social = Column(String(250))
    correo_electronico = Column(String(250))
    feccha_expiracion = Column(DATETIME)  # Mantengo el typo del esquema original
    fecha_creacion = Column(DATETIME, nullable=False, default=func.current_timestamp())
    fecha_actualizacion = Column(DATETIME, nullable=False, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # Relaciones
    comprobantes_fiscales = relationship("ComprobanteFiscal", back_populates="empresa")
    contribuyentes_detectados = relationship("ContribuyenteDetectadoListaNegra", back_populates="empresa")
    
    # Relaciones con módulo de conciliación bancaria
    movimientos_bancarios = relationship("MovimientoBancario", back_populates="empresa")
    archivos_bancarios = relationship("ArchivoBancario", back_populates="empresa")
    resultados_conciliacion = relationship("ResultadoConciliacion", back_populates="empresa")
    
    def __repr__(self):
        return f"<EmpresaContribuyente(id={self.id}, rfc='{self.rfc}', razon_social='{self.razon_social}')>"

class ComprobanteFiscal(Base):
    """Modelo para tabla comprobantes_fiscales"""
    __tablename__ = "comprobantes_fiscales"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    empresa_id = Column(Integer, ForeignKey("empresas_contribuyentes.id", ondelete="CASCADE"))
    version_cfdi = Column(DECIMAL(4, 2))
    rfc_emisor = Column(String(13))
    nombre_emisor = Column(String(500))
    regimen_fiscal_emisor = Column(String(3))
    rfc_receptor = Column(String(13))
    nombre_receptor = Column(String(500))
    codigo_postal_receptor = Column(String(5))
    regimen_fiscal_receptor = Column(String(3))
    subtotal = Column(DECIMAL(12, 2))
    descuento = Column(DECIMAL(12, 2))
    total = Column(DECIMAL(12, 2))
    fecha = Column(DATETIME)
    forma_pago = Column(String(2))
    metodo_pago = Column(String(3))
    moneda = Column(String(3))
    tipo_cambio = Column(DECIMAL(8, 2))
    tipo_comprobante = Column(Enum('I', 'E', 'T', 'N', 'P', name='tipo_comprobante_enum'))
    complementos = Column(String(150))
    codigo_postal_expedicion = Column(String(6))
    serie_cfdi = Column(String(25))
    folio_cfdi = Column(String(40))
    uuid = Column(String(36), unique=True)
    fecha_timbrado = Column(DATETIME)
    uso_cfdi = Column(String(3))
    estatus_sat = Column(Boolean, default=True)
    fecha_cancelacion = Column(DATETIME)
    nombre_archivo = Column(String(255))
    fecha_creacion = Column(DATETIME, nullable=False, default=func.current_timestamp())
    fecha_actualizacion = Column(DATETIME, nullable=False, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # Relaciones
    empresa = relationship("EmpresaContribuyente", back_populates="comprobantes_fiscales")
    conceptos = relationship("ConceptoComprobante", back_populates="comprobante_fiscal")
    impuestos_conceptos = relationship("ImpuestoConcepto", back_populates="comprobante_fiscal")
    totales_impuestos = relationship("TotalImpuestoComprobanteFiscal", back_populates="comprobante_fiscal", uselist=False)
    complemento_pago = relationship("ComplementoPago", back_populates="comprobante_fiscal")
    complemento_nomina = relationship("ComplementoNomina", back_populates="comprobante_fiscal", uselist=False)
    incapacidades_nomina = relationship("IncapacidadNomina", back_populates="comprobante_fiscal")
    documentos_relacionados = relationship("DocumentoRelacionadoPago", back_populates="comprobante_fiscal")
    impuestos_comprobante = relationship("ImpuestoComprobante", back_populates="comprobante_fiscal")
    
    # Relaciones con módulo de conciliación bancaria
    movimientos_bancarios = relationship("MovimientoBancario", back_populates="comprobante_fiscal")
    
    def __repr__(self):
        return f"<ComprobanteFiscal(id={self.id}, uuid='{self.uuid}', total={self.total})>"

class ConceptoComprobante(Base):
    """Modelo para tabla conceptos_comprobantes"""
    __tablename__ = "conceptos_comprobantes"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    cfdi_id = Column(Integer, ForeignKey("comprobantes_fiscales.id", ondelete="CASCADE"), nullable=False)
    clave_producto_servicio = Column(String(100))
    numero_identificacion = Column(String(100))
    clave_unidad = Column(String(100))
    unidad = Column(String(50))
    cantidad = Column(DECIMAL(12, 2))
    descripcion = Column(String(1000))
    valor_unitario = Column(DECIMAL(12, 2))
    importe = Column(DECIMAL(12, 2))
    descuento = Column(DECIMAL(12, 2))
    fecha_creacion = Column(DATETIME, nullable=False, default=func.current_timestamp())
    fecha_actualizacion = Column(DATETIME, nullable=False, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # Relaciones
    comprobante_fiscal = relationship("ComprobanteFiscal", back_populates="conceptos")
    impuestos = relationship("ImpuestoConcepto", back_populates="concepto")
    
    def __repr__(self):
        return f"<ConceptoComprobante(id={self.id}, descripcion='{self.descripcion[:50]}...', importe={self.importe})>"

class ImpuestoConcepto(Base):
    """Modelo para tabla impuestos_conceptos"""
    __tablename__ = "impuestos_conceptos"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    cfdi_id = Column(Integer, ForeignKey("comprobantes_fiscales.id", ondelete="CASCADE"), nullable=False)
    concepto_id = Column(Integer, ForeignKey("conceptos_comprobantes.id", ondelete="CASCADE"), nullable=False)
    tipo_impuesto = Column(Boolean, default=False)  # 0=traslado, 1=retención
    base_gravable = Column(DECIMAL(16, 6))
    codigo_impuesto = Column(String(3))
    tipo_factor = Column(Enum('Tasa', 'Cuota', 'Exento', name='tipo_factor_enum'), default='Tasa')
    tasa_o_cuota = Column(DECIMAL(10, 6))
    importe_impuesto = Column(DECIMAL(12, 2))
    fecha_creacion = Column(DATETIME, nullable=False, default=func.current_timestamp())
    fecha_actualizacion = Column(DATETIME, nullable=False, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # Relaciones
    comprobante_fiscal = relationship("ComprobanteFiscal", back_populates="impuestos_conceptos")
    concepto = relationship("ConceptoComprobante", back_populates="impuestos")
    
    def __repr__(self):
        return f"<ImpuestoConcepto(id={self.id}, codigo_impuesto='{self.codigo_impuesto}', importe_impuesto={self.importe_impuesto})>"

class TotalImpuestoComprobanteFiscal(Base):
    """Modelo para tabla totales_impuestos_comprobantes_fiscales"""
    __tablename__ = "totales_impuestos_comprobantes_fiscales"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    cfdi_id = Column(Integer, ForeignKey("comprobantes_fiscales.id", ondelete="CASCADE"), nullable=False)
    total_impuestos_trasladados = Column(DECIMAL(12, 2))
    total_iva_trasladado = Column(DECIMAL(12, 2))
    total_ieps_trasladado = Column(DECIMAL(12, 2))
    total_impuestos_retenidos = Column(DECIMAL(12, 2))
    total_iva_retenido = Column(DECIMAL(12, 2))
    total_isr_retenido = Column(DECIMAL(12, 2))
    total_ieps_retenido = Column(DECIMAL(12, 2))
    fecha_creacion = Column(DATETIME, nullable=False, default=func.current_timestamp())
    fecha_actualizacion = Column(DATETIME, nullable=False, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # Relaciones
    comprobante_fiscal = relationship("ComprobanteFiscal", back_populates="totales_impuestos")
    
    def __repr__(self):
        return f"<TotalImpuestoComprobanteFiscal(cfdi_id={self.cfdi_id}, total_impuestos_trasladados={self.total_impuestos_trasladados})>"

class ComplementoPago(Base):
    """Modelo para tabla complementos_pago"""
    __tablename__ = "complementos_pago"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    cfdi_id = Column(Integer, ForeignKey("comprobantes_fiscales.id", ondelete="CASCADE"), nullable=False)
    objeto_impuesto_pago = Column(Boolean, default=True)
    forma_pago_pago = Column(String(3))
    fecha_pago_pago = Column(DATETIME)
    moneda_pago = Column(String(3))
    monto_pago = Column(DECIMAL(12, 2))
    tipo_cambio_pago = Column(DECIMAL(12, 2))
    cuenta_ordenante_pago = Column(String(255))
    cuenta_beneficiario_pago = Column(String(255))
    total_ieps_retenciones_pago = Column(DECIMAL(12, 2))
    total_isr_retenciones_pago = Column(DECIMAL(12, 2))
    total_iva_retenciones_pago = Column(DECIMAL(12, 2))
    total_base_iva_exento_traslados_pago = Column(DECIMAL(12, 2))
    total_base_iva_0_traslados_pago = Column(DECIMAL(12, 2))
    total_base_iva_8_traslados_pago = Column(DECIMAL(12, 2))
    total_base_iva_16_traslados_pago = Column(DECIMAL(12, 2))
    total_impuesto_iva_0_traslados_pago = Column(DECIMAL(12, 2))
    total_impuesto_iva_8_traslados_pago = Column(DECIMAL(12, 2))
    total_impuesto_iva_16_traslados_pago = Column(DECIMAL(12, 2))
    fecha_creacion = Column(DATETIME, nullable=False, default=func.current_timestamp())
    fecha_actualizacion = Column(DATETIME, nullable=False, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # Relaciones
    comprobante_fiscal = relationship("ComprobanteFiscal", back_populates="complemento_pago")
    
    def __repr__(self):
        return f"<ComplementoPago(cfdi_id={self.cfdi_id}, monto_pago={self.monto_pago})>"

class ComplementoNomina(Base):
    """Modelo para tabla complementos_nomina"""
    __tablename__ = "complementos_nomina"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    cfdi_id = Column(Integer, ForeignKey("comprobantes_fiscales.id", ondelete="CASCADE"), nullable=False, unique=True)
    tipo_nomina = Column(String(3))
    numero_dias_pagados = Column(Integer)
    fecha_pago = Column(DATETIME)
    fecha_inicial_periodo = Column(DATETIME)
    fecha_final_periodo = Column(DATETIME)
    total_percepciones_nomina = Column(DECIMAL(12, 2))
    total_exento = Column(DECIMAL(12, 2))
    total_gravado = Column(DECIMAL(12, 2))
    total_sueldos = Column(DECIMAL(12, 2))
    total_otros_pagos = Column(DECIMAL(12, 2))
    total_deducciones_nomina = Column(DECIMAL(12, 2))
    total_impuestos_retenidos = Column(DECIMAL(12, 2))
    total_otras_deducciones = Column(DECIMAL(12, 2))
    total_subsidio = Column(DECIMAL(12, 2))
    total_subsidio_causado = Column(DECIMAL(12, 2))
    total_imss = Column(DECIMAL(12, 2))
    total_isr = Column(DECIMAL(12, 2))
    total_infonavit = Column(DECIMAL(12, 2))
    total_aportaciones_a_retiro = Column(DECIMAL(12, 2))
    fecha_creacion = Column(DATETIME, nullable=False, default=func.current_timestamp())
    fecha_actualizacion = Column(DATETIME, nullable=False, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # Relaciones
    comprobante_fiscal = relationship("ComprobanteFiscal", back_populates="complemento_nomina")
    
    def __repr__(self):
        return f"<ComplementoNomina(cfdi_id={self.cfdi_id}, total_percepciones_nomina={self.total_percepciones_nomina})>"

class IncapacidadNomina(Base):
    """Modelo para tabla incapacidades_nomina"""
    __tablename__ = "incapacidades_nomina"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    cfdi_id = Column(Integer, ForeignKey("comprobantes_fiscales.id", ondelete="CASCADE"), nullable=False)
    total_incapacidades = Column(DECIMAL(12, 2), default=0.00)
    monto_riesgo_trabajo = Column(DECIMAL(12, 2), default=0.00)
    monto_enfermedad_general = Column(DECIMAL(12, 2), default=0.00)
    monto_maternidad = Column(DECIMAL(12, 2), default=0.00)
    monto_licencia_cuidados_hijos = Column(DECIMAL(12, 2), default=0.00)
    fecha_creacion = Column(DATETIME, nullable=False, default=func.current_timestamp())
    fecha_actualizacion = Column(DATETIME, nullable=False, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # Relaciones
    comprobante_fiscal = relationship("ComprobanteFiscal", back_populates="incapacidades_nomina")
    
    def __repr__(self):
        return f"<IncapacidadNomina(cfdi_id={self.cfdi_id}, total_incapacidades={self.total_incapacidades})>"

class DocumentoRelacionadoPago(Base):
    """Modelo para tabla documentos_relacionados_pago"""
    __tablename__ = "documentos_relacionados_pago"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    cfdi_id = Column(Integer, ForeignKey("comprobantes_fiscales.id", ondelete="CASCADE"), nullable=False)
    uuid_cfdi_relacionado = Column(String(36))
    serie_cfdi_relacionado = Column(String(255))
    folio_cfdi_relacionado = Column(String(255))
    moneda_cfdi_relacionado = Column(String(3))
    tipo_cambio_cfdi_relacionado = Column(DECIMAL(8, 2))
    metodo_pago_cfdi_relacionado = Column(String(3))
    numero_parcialidad = Column(Integer)
    importe_saldo_anterior = Column(DECIMAL(12, 2))
    importe_pagado = Column(DECIMAL(12, 2))
    saldo_restante = Column(DECIMAL(12, 2))
    fecha_creacion = Column(DATETIME, nullable=False, default=func.current_timestamp())
    fecha_actualizacion = Column(DATETIME, nullable=False, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # Relaciones
    comprobante_fiscal = relationship("ComprobanteFiscal", back_populates="documentos_relacionados")
    
    def __repr__(self):
        return f"<DocumentoRelacionadoPago(cfdi_id={self.cfdi_id}, uuid_cfdi_relacionado='{self.uuid_cfdi_relacionado}')>"

class ListaNegraSatOficial(Base):
    """Modelo para tabla lista_negra_sat_oficial"""
    __tablename__ = "lista_negra_sat_oficial"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    rfc = Column(String(13))
    nombre_razon_social = Column(String(255))
    tipo_lista = Column(String(5))
    supuesto = Column(String(50))
    descripcion_motivo = Column(String(255))
    nombre_archivo = Column(String(50))
    fecha_inicio_situacion = Column(String(50))
    fecha_fin_situacion = Column(String(50))
    fecha_creacion = Column(DATETIME, nullable=False, default=func.current_timestamp())
    fecha_actualizacion = Column(DATETIME, nullable=False, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    def __repr__(self):
        return f"<ListaNegraSatOficial(rfc='{self.rfc}', tipo_lista='{self.tipo_lista}', supuesto='{self.supuesto}')>"

class ContribuyenteDetectadoListaNegra(Base):
    """Modelo para tabla contribuyentes_detectados_lista_negra"""
    __tablename__ = "contribuyentes_detectados_lista_negra"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    empresa_id = Column(Integer, ForeignKey("empresas_contribuyentes.id", ondelete="CASCADE"))
    tipo_relacion_cfdi = Column(Boolean, default=False)  # 0 = cliente, 1 = proveedor
    rfc_detectado = Column(String(13))
    razon_social_detectada = Column(String(500))
    tipo_lista = Column(String(255))
    nombre_lista = Column(String(255))
    mes_deteccion = Column(Integer)
    anio_deteccion = Column(Integer)
    descripcion = Column(Text)
    fecha_creacion = Column(DATETIME, nullable=False, default=func.current_timestamp())
    fecha_actualizacion = Column(DATETIME, nullable=False, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # Relaciones
    empresa = relationship("EmpresaContribuyente", back_populates="contribuyentes_detectados")
    
    def __repr__(self):
        return f"<ContribuyenteDetectadoListaNegra(rfc_detectado='{self.rfc_detectado}', tipo_lista='{self.tipo_lista}', mes_deteccion={self.mes_deteccion})>"

class ImpuestoComprobante(Base):
    """Modelo para tabla impuestos_comprobante"""
    __tablename__ = "impuestos_comprobante"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    cfdi_id = Column(Integer, ForeignKey("comprobantes_fiscales.id", ondelete="CASCADE"), nullable=False)
    retencion = Column(Boolean, default=False)  # 0=traslado, 1=retención
    base = Column(DECIMAL(12, 2))
    impuesto = Column(String(3))
    tipoFactor = Column(String(10))
    tasaOCuota = Column(DECIMAL(10, 6))
    importe = Column(DECIMAL(12, 2))
    fecha_creacion = Column(DATETIME, nullable=False, default=func.current_timestamp())
    fecha_actualizacion = Column(DATETIME, nullable=False, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # Relaciones
    comprobante_fiscal = relationship("ComprobanteFiscal", back_populates="impuestos_comprobante")
    
    def __repr__(self):
        return f"<ImpuestoComprobante(id={self.id}, impuesto='{self.impuesto}', importe={self.importe})>"

# Definir índices adicionales para optimización
Index('idx_rfc', EmpresaContribuyente.rfc)

Index('idx_uuid', ComprobanteFiscal.uuid)
Index('idx_rfc_emisor', ComprobanteFiscal.rfc_emisor)
Index('idx_rfc_receptor', ComprobanteFiscal.rfc_receptor)
Index('idx_tipo_comprobante', ComprobanteFiscal.tipo_comprobante)
Index('idx_fecha_timbrado', ComprobanteFiscal.fecha_timbrado)
Index('idx_empresa_fecha', ComprobanteFiscal.empresa_id, ComprobanteFiscal.fecha_timbrado)

Index('idx_cfdi_concepto', ConceptoComprobante.cfdi_id)
Index('idx_clave_producto', ConceptoComprobante.clave_producto_servicio)

Index('idx_concepto_impuesto', ImpuestoConcepto.concepto_id, ImpuestoConcepto.tipo_impuesto, ImpuestoConcepto.codigo_impuesto)

Index('idx_totales_monto', TotalImpuestoComprobanteFiscal.total_impuestos_trasladados)

Index('idx_cfdi_pago', ComplementoPago.cfdi_id)
Index('idx_fecha_pago', ComplementoPago.fecha_pago_pago)

Index('idx_fecha_pago_nomina', ComplementoNomina.fecha_pago)

Index('idx_cfdi_incapacidad', IncapacidadNomina.cfdi_id)

Index('idx_pago_documento', DocumentoRelacionadoPago.cfdi_id, DocumentoRelacionadoPago.uuid_cfdi_relacionado)
Index('idx_uuid_pagado', DocumentoRelacionadoPago.uuid_cfdi_relacionado)

Index('rfc_index', ListaNegraSatOficial.rfc)

Index('idx_rfc_detectado', ContribuyenteDetectadoListaNegra.rfc_detectado)
Index('idx_empresa_fecha', ContribuyenteDetectadoListaNegra.empresa_id, ContribuyenteDetectadoListaNegra.mes_deteccion, ContribuyenteDetectadoListaNegra.anio_deteccion) 