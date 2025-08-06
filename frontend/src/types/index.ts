export interface Categoria {
  id: number;
  nombre: string;
  empresa_id: number;
  empresa_nombre: string;
  es_categoria_general: boolean;
  created_at: string;
}

export interface Usuario {
  id: number;
  nombre: string;
  email: string;
  rol: 'super_admin' | 'usuario';
  empresa_id: number;
  created_at: string;
}

export interface UsuarioBasic {
  id: number;
  nombre: string;
  email: string;
  rol?: 'super_admin' | 'usuario';
}

export interface CategoriaCreateRequest {
  nombre: string;
}

export interface CategoriaUpdateRequest {
  nombre: string;
}

export interface ChatMessage {
  id: string;
  type: "user" | "assistant";
  content: string;
  timestamp: Date;
  sources?: Array<{
    titulo: string;
    documento_id: string;
  }>;
}

export interface Chat {
  id: number;
  titulo: string;
  created_at: string;
  updated_at: string;
}

// Tipos para Conciliación Bancaria
export interface MovimientoBancario {
  id: number;
  empresa_id: number;
  archivo_id: number;
  fecha: string;
  concepto: string;
  monto: number;
  tipo: 'cargo' | 'abono';
  referencia?: string;
  saldo: number | null; // El saldo puede ser null cuando no está disponible en el estado de cuenta
  estado: 'PENDIENTE' | 'CONCILIADO' | 'MANUAL';
  cfdi_uuid?: string;
  nivel_confianza?: number;
  metodo_conciliacion?: string;
  observaciones?: string;
  created_at: string;
}

export interface ArchivoBancario {
  id: number;
  empresa_id: number;
  nombre_archivo: string;
  banco: 'bbva' | 'santander' | 'banamex' | 'hsbc' | 'scotiabank' | 'banorte' | 'otro';
  periodo_inicio: string;
  periodo_fin: string;
  numero_cuenta: string;
  hash_archivo: string;
  procesado_exitosamente: boolean;
  total_movimientos: number;
  errores_procesamiento?: string[];
  fecha_procesamiento: string;
  created_at: string;
}

export interface EstadisticasConciliacion {
  total_movimientos_bancarios: number;
  movimientos_conciliados: number;
  movimientos_pendientes: number;
  porcentaje_conciliacion: number;
  monto_total_conciliado: number;
  monto_total_pendiente: number;
  tiempo_promedio_conciliacion: number;
}

export interface AlertaCritica {
  tipo: 'DESCUADRE_MAYOR' | 'MOVIMIENTOS_DUPLICADOS' | 'REFERENCIAS_FALTANTES' | 'FECHAS_INCONSISTENTES';
  mensaje: string;
  severidad: 'alta' | 'media' | 'baja';
  movimientos_afectados: number;
  accion_recomendada: string;
}

export interface SugerenciaConciliacion {
  movimiento_bancario_id: number;
  cfdi_uuid: string;
  nivel_confianza: number;
  razon: string;
  datos_comparacion: {
    monto_diferencia: number;
    dias_diferencia: number;
    similitud_concepto: number;
  };
}

export interface ResumenConciliacion {
  exito: boolean;
  mensaje: string;
  estadisticas: EstadisticasConciliacion;
  alertas_criticas: AlertaCritica[];
  sugerencias: SugerenciaConciliacion[];
  fecha_proceso: string;
  tiempo_total_segundos: number;
}

export interface ReporteConciliacion {
  empresa: {
    id: number;
    rfc: string;
    razon_social: string;
  };
  movimientos: {
    total: number;
    conciliados: number;
    pendientes: number;
    porcentaje_conciliacion: number;
    monto_total: number;
  };
  archivos: {
    total_procesados: number;
    exitosos: number;
    tasa_exito: number;
  };
  ultimos_procesos: ArchivoBancario[];
}

export interface ConciliacionRequest {
  rfc_empresa: string;
  mes: number;
  anio: number;
  tolerancia_monto?: number;
  dias_tolerancia?: number;
  forzar_reproceso?: boolean;
}

export interface SubirEstadoCuentaRequest {
  rfc_empresa: string;
  file: File;
}

export interface ResultadoOCR {
  exito: boolean;
  mensaje: string;
  archivo_id?: number;
  banco_detectado?: string;
  total_movimientos_extraidos: number;
  errores: string[];
  tiempo_procesamiento_segundos: number;
} 