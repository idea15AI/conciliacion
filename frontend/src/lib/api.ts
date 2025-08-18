// SISTEMA CFDI - API ENDPOINTS REALES

import axios from 'axios';
import { 
  ResultadoOCR, 
  ConciliacionRequest, 
  ResumenConciliacion,
  ReporteConciliacion,
  MovimientoBancario,
  ArchivoBancario
} from '@/types';

// Configuración base de la API
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Tipos específicos para CFDI
export interface DashboardStats {
  ingresos: string;
  gastos: string;
  iva_por_pagar: string;
  saldo_ppd: string;
  variacion_ingresos: string;
  variacion_gastos: string;
  fecha_vencimiento_iva: string;
}



export interface AlertaListaNegra {
  rfc: string;
  nombre: string;
  estado: 'revision' | 'critico';
  descripcion: string;
}



export interface EmpresaContribuyente {
  id: number;
  rfc: string;
  razon_social: string;
  correo_electronico: string;
  fecha_expiracion?: string;
  fecha_creacion?: string;
  fecha_actualizacion?: string;
}

export interface TopCliente {
  rfc: string;
  nombre: string;
  total: string;
  variacion: string;
  tendencia: 'up' | 'down' | 'stable';
}

export interface TopProveedor {
  rfc: string;
  nombre: string;
  total: string;
  variacion: string;
  tendencia: 'up' | 'down' | 'stable';
}

export interface ChartDataset {
  label?: string;
  data: number[];
  borderColor?: string;
  backgroundColor?: string | string[];
  fill?: boolean;
}

export interface ChartData {
  labels: string[];
  datasets: ChartDataset[];
}

export interface DashboardChartData {
  ingresos_vs_gastos: ChartData;
  tipos_comprobante: ChartData;
  evolucion_cfdis: ChartData;
  analisis_impuestos: ChartData;
  cancelaciones: ChartData;
  regimen_fiscal: ChartData;
  formas_pago: ChartData;
  heatmap_emision: ChartData;
  top_clientes: ChartData;
  top_proveedores: ChartData;
}

export interface CFDIQueryRequest {
  pregunta: string;
  rfc: string;
  conversacion_id?: number;
  nombre_empresa?: string;
}

export interface CFDIQueryResponse {
  respuesta: string;
  datos_adicionales?: Record<string, unknown>;
  tiempo_procesamiento?: number;
  conversacion_id: number;
}

// Nuevos tipos para funcionalidades avanzadas del dashboard
export interface AnalisisIVAData {
  iva_ingresos_pue: number;
  iva_ingresos_complementos: number;
  iva_trasladado_total: number;
  iva_gastos_pue: number;
  iva_gastos_complementos: number;
  iva_acreditable_total: number;
  iva_a_pagar_favor: number;
}

export interface AnalisisIEPSData {
  ieps_ingresos_pue: number;
  ieps_ingresos_complementos: number;
  ieps_trasladado_total: number;
  ieps_gastos_pue: number;
  ieps_gastos_complementos: number;
  ieps_acreditable_total: number;
  ieps_a_pagar_favor: number;
}

export interface AnalisisRetencionesData {
  iva_retenido_por_pagar: number;
  isr_retenido_por_pagar: number;
  ieps_retenido_por_pagar: number;
  isr_sueldos_por_pagar: number;
  total_impuestos_retenidos_por_pagar: number;
}

export interface ResumenEjecutivoImpuestosData {
  total_iva_pagar_favor: number;
  total_ieps_pagar_favor: number;
  total_retenciones_pagar: number;
  impacto_fiscal_total: number;
  fecha_vencimiento: string;
}

export interface PeriodoImpuestosData {
  fecha_inicio: string;
  fecha_fin: string;
  mes_nombre: string;
}

export interface AnalisisImpuestosData {
  iva: AnalisisIVAData;
  ieps: AnalisisIEPSData;
  retenciones: AnalisisRetencionesData;
  resumen_ejecutivo: ResumenEjecutivoImpuestosData;
  periodo: PeriodoImpuestosData;
}

export interface AnalisisCancelacionesData {
  mes: string;
  cancelados: number;
  total_mes: number;
  porcentaje_cancelacion: number;
}

export interface RegimenFiscalData {
  regimen: string;
  descripcion: string;
  cantidad: number;
  monto_total: number;
  porcentaje: number;
}

export interface FormaPagoData {
  clave: string;
  descripcion: string;
  cantidad: number;
  monto_total: number;
  porcentaje: number;
}

export interface ListaNegraSATData {
  rfc_detectado: string;
  razon_social_detectada: string;
  tipo_lista: string;
  nombre_lista: string;
  mes_deteccion: number;
  anio_deteccion: number;
  operaciones: number;
  monto_total: number;
  descripcion: string;
}

// Nuevos tipos para la sección completa de Lista Negra SAT
export interface AlertaCriticaListaNegra {
  nivel: 'ALTO' | 'MEDIO' | 'BAJO';
  cantidad: number;
  monto_total: number;
  color: string;
}

export interface KPIListaNegra {
  total_detectados: number;
  monto_total_riesgo: number;
  dias_desde_actualizacion: number;
  tendencia_mensual: number;
}

export interface ContribuyenteDetallado extends ListaNegraSATData {
  tipo_relacion: 'Cliente' | 'Proveedor' | 'Ambos' | 'Desconocido';
  nivel_riesgo: 'ALTO' | 'MEDIO' | 'BAJO';
  fecha_entrada_lista: string;
  fecha_ultima_operacion: string;
  estado_seguimiento: 'Nuevo' | 'En Seguimiento' | 'Resuelto';
  cfdis_afectados: number;
}

export interface ImpactoFinancieroListaNegra {
  exposicion_total: number;
  por_tipo_lista: Array<{
    tipo: string;
    cantidad: number;
    monto: number;
    porcentaje: number;
  }>;
  timeline_riesgo: Array<{
    fecha: string;
    nuevos_detectados: number;
    monto_afectado: number;
  }>;
  proyeccion_rechazo_deducciones: number;
}

export interface DashboardListaNegra {
  alertas_criticas: {
    alto: AlertaCriticaListaNegra;
    medio: AlertaCriticaListaNegra;
    bajo: AlertaCriticaListaNegra;
  };
  kpis: KPIListaNegra;
  contribuyentes_detallados: ContribuyenteDetallado[];
}

export interface CFDIContribuyente {
  uuid: string;
  serie: string;
  folio: string;
  fecha: string;
  fecha_timbrado: string;
  rfc_emisor: string;
  nombre_emisor: string;
  rfc_receptor: string;
  nombre_receptor: string;
  subtotal: number;
  total: number;
  tipo_comprobante: string;
  forma_pago: string;
  metodo_pago: string;
  moneda: string;
  estatus_sat: string;
  tipo_operacion: string;
}

export interface CFDIsContribuyenteResponse {
  cfdis: CFDIContribuyente[];
  total: number;
  monto_total: number;
  rfc_contribuyente: string;
  empresa_rfc: string;
}

export interface ComplementoNominaData {
  mes: string;
  percepciones: number;
  deducciones: number;
  isr: number;
  imss: number;
  empleados: number;
  carga_fiscal_promedio: number;
}

export interface ComplementoPagoData {
  forma_pago: string;
  cantidad_pagos: number;
  monto_total: number;
  dias_promedio_pago: number;
}

export interface HeatmapEmisionData {
  dia_semana: number;
  hora: number;
  cantidad: number;
}

export interface ScoreCumplimientoData {
  score_total: number;
  componentes: {
    pct_cancelados: number;
    inconsistencia_promedio: number;
    estructuras_incorrectas: number;
    cumplimiento_cfdi40: number;
  };
  historico: Array<{
    mes: string;
    score: number;
  }>;
}

export interface ConcentracionRiesgoData {
  rfc: string;
  nombre: string;
  operaciones: number;
  monto_total: number;
  porcentaje_concentracion: number;
  tipo: 'emisor' | 'receptor';
}

export interface FlujoCajaData {
  mes: string;
  flujo_proyectado: number;
  banda_inferior: number;
  banda_superior: number;
  confianza: number;
}

export interface RedRelacionesData {
  nodos: Array<{
    id: string;
    rfc: string;
    nombre: string;
    tipo: 'empresa' | 'cliente' | 'proveedor';
    peso: number;
  }>;
  enlaces: Array<{
    origen: string;
    destino: string;
    peso_relacion: number;
    monto_total: number;
  }>;
}

export interface EstacionalidadData {
  mes: string;
  monto_real: number;
  monto_esperado: number;
  tendencia: number;
  estacionalidad: number;
  desviacion: number;
}

export interface AnalisisCancelacionesDetallado {
  resumen: {
    total_cancelados: number;
    porcentaje_general: number;
    tendencia: string;
  };
  por_mes: Array<{
    mes: string;
    cancelados: number;
    monto_cancelado: number;
  }>;
  razones_principales: Array<{
    razon: string;
    porcentaje: number;
  }>;
  impacto_fiscal: {
    monto_cancelado: number;
    iva_perdido: number;
  };
}

export interface DistribucionMonedasData {
  moneda: string;
  descripcion: string;
  cantidad: number;
  monto_total: number;
  porcentaje: number;
}

export interface AnalisisUsoCfdiData {
  tipo_comprobante: string;
  tipo_descripcion: string;
  uso_cfdi: string;
  uso_descripcion: string;
  cantidad: number;
  monto_total: number;
}

export interface MetricasTiempoRealData {
  timestamp: string;
  cfdis_hoy: number;
  monto_facturado_hoy: number;
  promedio_por_hora: number;
  status_sistema: string;
  ultimas_operaciones: Array<{
    uuid: string;
    timestamp: string | null;
    monto: number;
    tipo: string;
    receptor: string;
  }>;
}

export interface ExportacionData {
  rfc: string;
  timestamp: string;
  [key: string]: unknown;
}

export interface ConfiguracionAlertas {
  mensaje: string;
  rfc: string;
  configuracion: Record<string, unknown>;
  timestamp: string;
  status: string;
}

export interface FiltrosDisponibles {
  tipos_comprobante: string[];
  monedas: string[];
  formas_pago: string[];
  rango_fechas: {
    fecha_minima: string | null;
    fecha_maxima: string | null;
  };
  periodos_predefinidos: Array<{
    valor: string;
    descripcion: string;
  }>;
}

export interface FiltrosAplicados {
  mensaje: string;
  rfc: string;
  filtros_aplicados: Record<string, unknown>;
  total_registros_filtrados: number;
  timestamp: string;
  status: string;
}

export interface PrediccionCashFlow {
  predicciones: Array<{
    mes: string;
    prediccion: number;
    tipo: string;
  }>;
  confianza: number;
  modelo: string;
}

export interface AnomaliaDetectada {
  mes: string;
  tipo: string;
  valor: number;
  severidad: string;
  descripcion: string;
  z_score: number;
}

export interface IndiceEstacionalidad {
  indices_mensuales: Array<{
    mes_numero: number;
    mes_nombre: string;
    indice_estacionalidad: number;
    variacion_porcentual: number;
    promedio_mes: number;
    interpretacion: string;
  }>;
  estacionalidad_general: number;
  interpretacion_general: string;
}

export interface KPIEjecutivo {
  total_cfdis: number;
  cfdis_vigentes: number;
  cfdis_cancelados: number;
  porcentaje_cancelados: number;
  facturacion_total: number;
  gastos_totales: number;
  ticket_promedio: number;
  margen_bruto: number;
  variaciones: {
    cfdis: number;
    facturacion: number;
    gastos: number;
    ticket: number;
    margen: number;
    cancelados: number;
  };
}

// RFC por defecto removido - ahora se pasa desde el contexto

// API específica para CFDI Dashboard con endpoints reales
export const cfdiDashboardAPI = {
  getStats: async (rfc: string): Promise<DashboardStats> => {
    console.log('🔄 Getting CFDI dashboard stats from backend');
    try {
      const response = await api.get(`/api/v1/cfdi/dashboard/stats/${rfc}`);
      return response.data;
    } catch (error) {
      console.error('Error getting dashboard stats:', error);
      // Fallback con datos vacíos
    return {
        ingresos: '$0.00',
        gastos: '$0.00',
        iva_por_pagar: '$0.00',
        saldo_ppd: '$0.00',
        variacion_ingresos: '0.0% vs mes anterior',
        variacion_gastos: '0.0% vs mes anterior',
        fecha_vencimiento_iva: 'N/A'
      };
    }
  },



  getAlertasListaNegra: async (rfc: string): Promise<AlertaListaNegra[]> => {
    console.log('🔄 Getting alertas lista negra from backend');
    try {
      const response = await api.get(`/api/v1/cfdi/dashboard/alertas-lista-negra/${rfc}`);
      return response.data;
    } catch (error) {
      console.error('Error getting alertas lista negra:', error);
      return [];
    }
  },



  getGraficos: async (rfc: string, meses: number = 12): Promise<DashboardChartData> => {
    console.log('🔄 Getting chart data from backend');
    try {
      const response = await api.get(`/api/v1/cfdi/dashboard/graficos/${rfc}?meses=${meses}`);
      return response.data;
    } catch (error) {
      console.error('Error getting chart data:', error);
      return {
        ingresos_vs_gastos: { labels: [], datasets: [] },
        tipos_comprobante: { labels: [], datasets: [] },
        evolucion_cfdis: { labels: [], datasets: [] },
        analisis_impuestos: { labels: [], datasets: [] },
        cancelaciones: { labels: [], datasets: [] },
        regimen_fiscal: { labels: [], datasets: [] },
        formas_pago: { labels: [], datasets: [] },
        heatmap_emision: { labels: [], datasets: [] },
        top_clientes: { labels: [], datasets: [] },
        top_proveedores: { labels: [], datasets: [] }
      };
    }
  },

  getEmpresasContribuyentes: async (): Promise<EmpresaContribuyente[]> => {
    console.log('🔄 Getting empresas contribuyentes from backend');
    try {
      const response = await api.get('/api/v1/cfdi/empresas-contribuyentes');
      return response.data;
    } catch (error) {
      console.error('Error getting empresas contribuyentes:', error);
      return [];
    }
  },

  // Nuevos endpoints para funcionalidades avanzadas
  getAnalisisImpuestos: async (rfc: string, periodo?: string): Promise<AnalisisImpuestosData[]> => {
    console.log('🔄 Getting análisis de impuestos from backend');
    try {
      const url = periodo ? `/api/v1/cfdi/dashboard/analisis-impuestos/${rfc}?periodo=${periodo}` : `/api/v1/cfdi/dashboard/analisis-impuestos/${rfc}`;
      const response = await api.get(url);
      return response.data;
    } catch (error) {
      console.error('Error getting análisis de impuestos:', error);
      return [];
    }
  },

  getAnalisisCancelaciones: async (rfc: string, periodo?: string): Promise<AnalisisCancelacionesData[]> => {
    console.log('🔄 Getting análisis de cancelaciones from backend');
    try {
      const url = periodo ? `/api/v1/cfdi/dashboard/analisis-cancelaciones/${rfc}?periodo=${periodo}` : `/api/v1/cfdi/dashboard/analisis-cancelaciones/${rfc}`;
      const response = await api.get(url);
      return response.data;
    } catch (error) {
      console.error('Error getting análisis de cancelaciones:', error);
      return [];
    }
  },

  getRegimenFiscal: async (rfc: string, periodo?: string): Promise<RegimenFiscalData[]> => {
    console.log('🔄 Getting distribución por régimen fiscal from backend');
    try {
      const url = periodo ? `/api/v1/cfdi/dashboard/regimen-fiscal/${rfc}?periodo=${periodo}` : `/api/v1/cfdi/dashboard/regimen-fiscal/${rfc}`;
      const response = await api.get(url);
      return response.data;
    } catch (error) {
      console.error('Error getting distribución por régimen fiscal:', error);
      return [];
    }
  },

  getFormasPago: async (rfc: string, periodo?: string): Promise<FormaPagoData[]> => {
    console.log('🔄 Getting formas de pago from backend');
    try {
      const url = periodo ? `/api/v1/cfdi/dashboard/formas-pago/${rfc}?periodo=${periodo}` : `/api/v1/cfdi/dashboard/formas-pago/${rfc}`;
      const response = await api.get(url);
      return response.data;
    } catch (error) {
      console.error('Error getting formas de pago:', error);
      return [];
    }
  },

  getListaNegraSAT: async (rfc: string): Promise<ListaNegraSATData[]> => {
    console.log('🔄 Getting dashboard completo lista negra SAT from backend');
    try {
      const response = await api.get(`/api/v1/cfdi/dashboard/lista-negra-sat/${rfc}`);
      return response.data;
    } catch (error) {
      console.error('Error getting dashboard lista negra SAT:', error);
      return [];
    }
  },

  // Nueva función para dashboard completo de Lista Negra SAT
  getDashboardListaNegraSAT: async (rfc: string): Promise<DashboardListaNegra> => {
    console.log('🔄 Getting dashboard completo lista negra SAT from backend');
    try {
      const response = await api.get(`/api/v1/cfdi/dashboard-lista-negra-completo/${rfc}`);
      return response.data;
    } catch (error) {
      console.error('Error getting dashboard completo lista negra SAT:', error);
      throw error;
    }
  },


  // Nueva función para dashboard completo de Lista Negra SAT con filtro opcional de período
  getDashboardListaNegraSATConPeriodo: async (rfc: string, periodo?: string): Promise<DashboardListaNegra> => {
    console.log(`🔄 Getting dashboard completo lista negra SAT${periodo ? ` con período ${periodo}` : ''} from backend`);
    try {
      const url = periodo 
        ? `/api/v1/cfdi/dashboard-lista-negra-completo/${rfc}?periodo=${periodo}`
        : `/api/v1/cfdi/dashboard-lista-negra-completo/${rfc}`;
      const response = await api.get(url);
      return response.data;
    } catch (error) {
      console.error('Error getting dashboard completo lista negra SAT con período:', error);
      throw error;
    }
  },

  // Función para obtener CFDIs de un contribuyente específico con filtro de período
  getCFDIsContribuyente: async (rfcEmpresa: string, rfcContribuyente: string, periodo?: string): Promise<CFDIsContribuyenteResponse> => {
    console.log(`🔄 Getting CFDIs de ${rfcContribuyente} para empresa ${rfcEmpresa}${periodo ? ` con período ${periodo}` : ''}`);
    try {
      const url = periodo 
        ? `/api/v1/cfdi/lista-negra-cfdis/${rfcEmpresa}/${rfcContribuyente}?periodo=${periodo}`
        : `/api/v1/cfdi/lista-negra-cfdis/${rfcEmpresa}/${rfcContribuyente}`;
      const response = await api.get(url);
      return response.data;
    } catch (error) {
      console.error('Error getting CFDIs de contribuyente:', error);
      throw error;
    }
  },

  getComplementosNomina: async (rfc: string, periodo?: string): Promise<ComplementoNominaData[]> => {
    console.log('🔄 Getting análisis complementos nómina from backend');
    try {
      const url = periodo ? `/api/v1/cfdi/dashboard/complementos-nomina/${rfc}?periodo=${periodo}` : `/api/v1/cfdi/dashboard/complementos-nomina/${rfc}`;
      const response = await api.get(url);
      return response.data;
    } catch (error) {
      console.error('Error getting análisis complementos nómina:', error);
      return [];
    }
  },

  getComplementosPago: async (rfc: string, periodo?: string): Promise<ComplementoPagoData[]> => {
    console.log('🔄 Getting análisis complementos pago from backend');
    try {
      const url = periodo ? `/api/v1/cfdi/dashboard/complementos-pago/${rfc}?periodo=${periodo}` : `/api/v1/cfdi/dashboard/complementos-pago/${rfc}`;
      const response = await api.get(url);
      return response.data;
    } catch (error) {
      console.error('Error getting análisis complementos pago:', error);
      return [];
    }
  },

  getHeatmapEmision: async (rfc: string, periodo?: string): Promise<HeatmapEmisionData[]> => {
    console.log('🔄 Getting heatmap tendencias emisión from backend');
    try {
      const url = periodo ? `/api/v1/cfdi/dashboard/heatmap-emision/${rfc}?periodo=${periodo}` : `/api/v1/cfdi/dashboard/heatmap-emision/${rfc}`;
      const response = await api.get(url);
      return response.data;
    } catch (error) {
      console.error('Error getting heatmap tendencias emisión:', error);
      return [];
    }
  },

  getScoreCumplimiento: async (rfc: string): Promise<ScoreCumplimientoData> => {
    console.log('🔄 Getting score de cumplimiento fiscal from backend');
    try {
      const response = await api.get(`/api/v1/cfdi/dashboard/score-cumplimiento/${rfc}`);
      return response.data;
    } catch (error) {
      console.error('Error getting score de cumplimiento fiscal:', error);
      return {
        score_total: 0,
        componentes: {
          pct_cancelados: 0,
          inconsistencia_promedio: 0,
          estructuras_incorrectas: 0,
          cumplimiento_cfdi40: 0
        },
        historico: []
      };
    }
  },

  getKPIsEjecutivos: async (rfc: string, periodo?: string): Promise<KPIEjecutivo> => {
    console.log('🔄 Getting KPIs ejecutivos from backend');
    try {
      const url = periodo ? `/api/v1/cfdi/dashboard/kpis-ejecutivos/${rfc}?periodo=${periodo}` : `/api/v1/cfdi/dashboard/kpis-ejecutivos/${rfc}`;
      const response = await api.get(url);
      return response.data;
    } catch (error) {
      console.error('Error getting KPIs ejecutivos:', error);
      return {
        total_cfdis: 0,
        cfdis_vigentes: 0,
        cfdis_cancelados: 0,
        porcentaje_cancelados: 0,
        facturacion_total: 0,
        gastos_totales: 0,
        ticket_promedio: 0,
        margen_bruto: 0,
        variaciones: {
          cfdis: 0,
          facturacion: 0,
          gastos: 0,
          ticket: 0,
          margen: 0,
          cancelados: 0
        }
      };
    }
  },

  getConcentracionRiesgo: async (rfc: string, tipo: 'emisor' | 'receptor' = 'emisor'): Promise<ConcentracionRiesgoData[]> => {
    console.log('🔄 Getting análisis concentración riesgo from backend');
    try {
      const response = await api.get(`/api/v1/cfdi/dashboard/concentracion-riesgo/${rfc}?tipo=${tipo}`);
      return response.data;
    } catch (error) {
      console.error('Error getting análisis concentración riesgo:', error);
      return [];
    }
  },

  getFlujoCaja: async (rfc: string): Promise<FlujoCajaData[]> => {
    console.log('🔄 Getting análisis predictivo flujo caja from backend');
    try {
      const response = await api.get(`/api/v1/cfdi/dashboard/flujo-caja/${rfc}`);
      return response.data;
    } catch (error) {
      console.error('Error getting análisis predictivo flujo caja:', error);
      return [];
    }
  },

  getRedRelaciones: async (rfc: string, umbral?: number): Promise<RedRelacionesData> => {
    console.log('🔄 Getting red de relaciones from backend');
    try {
      const url = umbral ? `/api/v1/cfdi/dashboard/red-relaciones/${rfc}?umbral=${umbral}` : `/api/v1/cfdi/dashboard/red-relaciones/${rfc}`;
      const response = await api.get(url);
      return response.data;
    } catch (error) {
      console.error('Error getting red de relaciones:', error);
      return {
        nodos: [],
        enlaces: []
      };
    }
  },

  getEstacionalidad: async (rfc: string): Promise<EstacionalidadData[]> => {
    console.log('🔄 Getting análisis de estacionalidad from backend');
    try {
      const response = await api.get(`/api/v1/cfdi/dashboard/estacionalidad/${rfc}`);
      return response.data;
    } catch (error) {
      console.error('Error getting análisis de estacionalidad:', error);
      return [];
    }
  },

  // NUEVOS MÉTODOS FALTANTES SOLICITADOS
  getAnalisisCancelacionesDetallado: async (rfc: string): Promise<AnalisisCancelacionesDetallado> => {
    console.log('🔄 Getting análisis detallado de cancelaciones from backend');
    try {
      const response = await api.get(`/api/v1/cfdi/dashboard/analisis-cancelaciones-detallado/${rfc}`);
      return response.data;
    } catch (error) {
      console.error('Error getting análisis detallado de cancelaciones:', error);
      return {
        resumen: { total_cancelados: 0, porcentaje_general: 0, tendencia: "Sin datos" },
        por_mes: [],
        razones_principales: [],
        impacto_fiscal: { monto_cancelado: 0, iva_perdido: 0 }
      };
    }
  },

  getDistribucionMonedas: async (rfc: string): Promise<DistribucionMonedasData[]> => {
    console.log('🔄 Getting distribución de monedas from backend');
    try {
      const response = await api.get(`/api/v1/cfdi/dashboard/distribucion-monedas/${rfc}`);
      return response.data;
    } catch (error) {
      console.error('Error getting distribución de monedas:', error);
      return [];
    }
  },

  getAnalisisUsoCfdi: async (rfc: string): Promise<AnalisisUsoCfdiData[]> => {
    console.log('🔄 Getting análisis de uso CFDI from backend');
    try {
      const response = await api.get(`/api/v1/cfdi/dashboard/analisis-uso-cfdi/${rfc}`);
      return response.data;
    } catch (error) {
      console.error('Error getting análisis de uso CFDI:', error);
      return [];
    }
  },

  getMetricasTiempoReal: async (rfc: string): Promise<MetricasTiempoRealData> => {
    console.log('🔄 Getting métricas en tiempo real from backend');
    try {
      const response = await api.get(`/api/v1/cfdi/dashboard/metricas-tiempo-real/${rfc}`);
      return response.data;
    } catch (error) {
      console.error('Error getting métricas en tiempo real:', error);
      return {
        timestamp: new Date().toISOString(),
        cfdis_hoy: 0,
        monto_facturado_hoy: 0,
        promedio_por_hora: 0,
        status_sistema: "Sin datos",
        ultimas_operaciones: []
      };
    }
  },

  exportarDatos: async (rfc: string, formato: 'json' | 'csv' = 'json'): Promise<ExportacionData> => {
    console.log('🔄 Exporting dashboard data from backend');
    try {
      const response = await api.get(`/api/v1/cfdi/dashboard/exportar-datos/${rfc}?formato=${formato}`);
      return response.data;
    } catch (error) {
      console.error('Error exporting dashboard data:', error);
      throw error;
    }
  },

  configurarAlertas: async (rfc: string, alertasConfig: Record<string, unknown>): Promise<ConfiguracionAlertas> => {
    console.log('🔄 Configuring custom alerts');
    try {
      const response = await api.post(`/api/v1/cfdi/dashboard/configurar-alertas/${rfc}`, alertasConfig);
      return response.data;
    } catch (error) {
      console.error('Error configuring alerts:', error);
      throw error;
    }
  },

  getFiltrosDisponibles: async (rfc: string): Promise<FiltrosDisponibles> => {
    console.log('🔄 Getting available filters from backend');
    try {
      const response = await api.get(`/api/v1/cfdi/dashboard/filtros-disponibles/${rfc}`);
      return response.data;
    } catch (error) {
      console.error('Error getting available filters:', error);
      return { 
        tipos_comprobante: [],
        monedas: [],
        formas_pago: [],
        rango_fechas: { fecha_minima: null, fecha_maxima: null },
        periodos_predefinidos: []
      };
    }
  },

  aplicarFiltros: async (rfc: string, filtros: Record<string, unknown>): Promise<FiltrosAplicados> => {
    console.log('🔄 Applying custom filters');
    try {
      const response = await api.post(`/api/v1/cfdi/dashboard/aplicar-filtros/${rfc}`, filtros);
      return response.data;
    } catch (error) {
      console.error('Error applying filters:', error);
      throw error;
    }
  },

  // ANÁLISIS PREDICTIVOS
  getPredictCashFlow: async (rfc: string): Promise<PrediccionCashFlow> => {
    console.log('🔄 Getting cash flow prediction from backend');
    try {
      const response = await api.get(`/api/v1/cfdi/dashboard/predict-cash-flow/${rfc}`);
      return response.data;
    } catch (error) {
      console.error('Error getting cash flow prediction:', error);
      return { predicciones: [], confianza: 0, modelo: "Sin datos" };
    }
  },

  getDetectAnomalies: async (rfc: string): Promise<AnomaliaDetectada[]> => {
    console.log('🔄 Getting anomaly detection from backend');
    try {
      const response = await api.get(`/api/v1/cfdi/dashboard/detect-anomalies/${rfc}`);
      return response.data;
    } catch (error) {
      console.error('Error getting anomaly detection:', error);
      return [];
    }
  },

  getCalculateSeasonality: async (rfc: string): Promise<IndiceEstacionalidad> => {
    console.log('🔄 Getting seasonality index from backend');
    try {
      const response = await api.get(`/api/v1/cfdi/dashboard/calculate-seasonality/${rfc}`);
      return response.data;
    } catch (error) {
      console.error('Error getting seasonality index:', error);
      return { indices_mensuales: [], estacionalidad_general: 0, interpretacion_general: "Sin datos" };
    }
  },

  getTopClientes: async (rfc: string): Promise<TopCliente[]> => {
    console.log('🔄 Getting top clientes from backend');
    try {
      const response = await api.get(`/api/v1/clientes-proveedores/top-clientes/${rfc}`);
      return response.data;
    } catch (error) {
      console.error('Error getting top clientes:', error);
      return [];
    }
  },

  getTopProveedores: async (rfc: string): Promise<TopProveedor[]> => {
    console.log('🔄 Getting top proveedores from backend');
    try {
      const response = await api.get(`/api/v1/clientes-proveedores/top-proveedores/${rfc}`);
      return response.data;
    } catch (error) {
      console.error('Error getting top proveedores:', error);
      return [];
    }
  }
};

// Chat API actualizado para usar endpoints reales del backend
export interface Chat {
  id: number;
  titulo: string;
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  id: number;
  contenido: string;
  remitente: 'usuario' | 'asistente';
  created_at: string;
}

export interface ChatWithMessages extends Chat {
  mensajes: ChatMessage[];
}

export interface BackendMessage {
  id: number;
  role: string;
  content: string;
  timestamp: string;
  emoji?: string;
}

export interface BackendConversationResponse {
  conversacion_id: number;
  rfc_empresa: string;
  nombre_empresa: string;
  mensajes: BackendMessage[];
  total_mensajes: number;
  created_at: string;
  updated_at: string;
}

export interface BackendConversation {
  id: number;
  titulo: string;
  rfc_empresa: string;
  nombre_empresa: string;
  total_mensajes: number;
  ultimo_mensaje_preview: string;
  ultimo_mensaje_tipo: string | null;
  created_at: string;
  updated_at: string;
}

export const chatsAPI = {
  getAll: async (rfc: string): Promise<Chat[]> => {
    console.log('🔄 Getting all conversations from backend');
    try {
      const response = await api.get(`/api/v1/conversacion/conversaciones/${rfc}`);
      const conversaciones = response.data;
      
      // Convertir las conversaciones del backend al formato esperado
      if (Array.isArray(conversaciones)) {
        return conversaciones.map((conv: BackendConversation) => ({
          id: conv.id,
          titulo: conv.titulo || `Conversación ${conv.id}`,
          created_at: conv.created_at,
          updated_at: conv.updated_at
        }));
      }
      
      return [];
    } catch (error) {
      console.error('Error getting conversations:', error);
      return [];
    }
  },

  getById: async (chatId: number, rfc: string): Promise<ChatWithMessages> => {
    console.log('🔄 Getting chat by ID from backend:', chatId);
    try {
      // Obtener los datos usando el RFC del contexto
      const response = await api.get(`/api/v1/conversacion/historial/${rfc}?conversacion_id=${chatId}`);
      const data = response.data;
      
      // Si la respuesta es válida, convertirla al formato esperado
      if (data && data.conversacion_id) {
        const mensajes: ChatMessage[] = data.mensajes ? data.mensajes.map((msg: BackendMessage) => ({
          id: msg.id,
          contenido: msg.content,
          remitente: msg.role === 'user' ? 'usuario' : 'asistente',
          created_at: msg.timestamp
        })) : [];
        
        return {
          id: data.conversacion_id,
          titulo: `Conversación ${data.conversacion_id}`,
          created_at: data.created_at || new Date().toISOString(),
          updated_at: data.updated_at || new Date().toISOString(),
          mensajes
        };
      }
      
      // Si no hay datos válidos, devolver chat vacío
      return {
        id: chatId,
        titulo: `Conversación ${chatId}`,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        mensajes: []
      };
    } catch (error) {
      console.error('Error getting chat by ID:', error);
      // Devolver chat vacío en caso de error
      return {
        id: chatId,
        titulo: `Conversación ${chatId}`,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        mensajes: []
      };
    }
  },

  create: async (titulo: string): Promise<Chat> => {
    console.log('🔄 Creating new chat will be handled by first message');
    // El chat se crea automáticamente con el primer mensaje
    return {
      id: Date.now(),
      titulo,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
  },

  delete: async (chatId: number, rfc: string): Promise<{ message: string }> => {
    console.log('🔄 Deleting conversation completely:', chatId);
    try {
      const response = await api.delete(`/api/v1/conversacion/conversaciones/${chatId}?rfc=${rfc}`);
      return response.data;
    } catch (error) {
      console.error('Error deleting conversation:', error);
      throw error;
    }
  },

  sendMessage: async (data: CFDIQueryRequest): Promise<CFDIQueryResponse> => {
    console.log('🔄 Sending message to backend:', data.pregunta);
    try {
      const response = await api.post('/api/v1/conversacion/chat', {
        pregunta: data.pregunta,
        rfc: data.rfc,
        conversacion_id: data.conversacion_id,
        nombre_empresa: data.nombre_empresa
      });
      
      return {
        respuesta: response.data.respuesta,
        conversacion_id: response.data.conversacion_id,
        datos_adicionales: response.data.datos_adicionales,
        tiempo_procesamiento: response.data.tiempo_procesamiento
      };
    } catch (error) {
      console.error('Error sending message:', error);
      throw error;
    }
  }
  };

// API específica para Conciliación Bancaria
export const conciliacionAPI = {
  // Obtener empresas contribuyentes
  getEmpresasContribuyentes: async (): Promise<EmpresaContribuyente[]> => {
    console.log('🔄 Getting empresas contribuyentes from conciliacion API');
    try {
      const response = await api.get('/api/v1/conciliacion/empresas');
      return response.data;
    } catch (error) {
      console.error('Error getting empresas contribuyentes:', error);
      return [];
    }
  },

  // Subir estado de cuenta bancario
  subirEstadoCuenta: async (rfcEmpresa: string, file: File): Promise<ResultadoOCR> => {
    console.log('📄 Subiendo estado de cuenta para RFC:', rfcEmpresa);
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await api.post(`/api/v1/conciliacion/subir-estado-cuenta?rfc_empresa=${rfcEmpresa}`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    console.log('✅ Estado de cuenta procesado:', response.data);
    return response.data;
  },

  // Subir estado de cuenta por empresa_id (usa router unificado)
  subirEstadoCuentaEmpresa: async (empresaId: number, file: File): Promise<ResultadoOCR> => {
    console.log('📄 Subiendo estado de cuenta para empresa_id:', empresaId);
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post(`/api/v1/procesar-pdf/subir?empresa_id=${empresaId}`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    console.log('✅ Estado de cuenta procesado (empresa_id):', response.data);
    return response.data;
  },

  ejecutarConciliacion: async (request: ConciliacionRequest): Promise<ResumenConciliacion> => {
    console.log('🔄 Ejecutando conciliación:', request);
    const response = await api.post('/api/v1/conciliacion/ejecutar', request);
    console.log('✅ Conciliación completada:', response.data);
    return response.data;
  },

  obtenerEstadisticas: async (empresaId: number): Promise<ReporteConciliacion> => {
    console.log('📊 Obteniendo estadísticas para empresa:', empresaId);
    const response = await api.get(`/api/v1/conciliacion/estadisticas/${empresaId}`);
    console.log('📊 Estadísticas obtenidas:', response.data);
    return response.data;
  },

  obtenerReporte: async (empresaId: number): Promise<ReporteConciliacion> => {
    console.log('📋 Obteniendo reporte para empresa:', empresaId);
    const response = await api.get(`/api/v1/conciliacion/reporte/${empresaId}`);
    console.log('📋 Reporte obtenido:', response.data);
    return response.data;
  },

  obtenerMovimientos: async (empresaId: number, filtros?: Record<string, string | number>): Promise<{ movimientos: MovimientoBancario[], total: number }> => {
    console.log('📑 Obteniendo movimientos para empresa:', empresaId);
    let url = `/api/v1/conciliacion/movimientos/${empresaId}`;
    
    if (filtros) {
      const params = new URLSearchParams();
      Object.keys(filtros).forEach(key => {
        if (filtros[key] !== undefined && filtros[key] !== null) {
          params.append(key, String(filtros[key]));
        }
      });
      if (params.toString()) {
        url += `?${params.toString()}`;
      }
    }
    
    const response = await api.get(url);
    console.log('📑 Movimientos obtenidos:', response.data);
    
    // Mapear la respuesta de la API (items) al formato esperado por el frontend (movimientos)
    return {
      movimientos: response.data.items || [],
      total: response.data.total || 0
    };
  },

  obtenerArchivos: async (empresaId: number): Promise<{ archivos: ArchivoBancario[], total: number }> => {
    console.log('📁 Obteniendo archivos para empresa:', empresaId);
    const response = await api.get(`/api/v1/conciliacion/archivos/${empresaId}`);
    console.log('📁 Archivos obtenidos:', response.data);
    
    // La API devuelve un array directamente, mapear al formato esperado
    const archivos = Array.isArray(response.data) ? response.data : [];
    return {
      archivos,
      total: archivos.length
    };
  }
};

// =============================================================================
// ANÁLISIS DE IMPUESTOS - API FUNCTIONS
// =============================================================================

export const impuestosAPI = {
  obtenerAnalisisCompleto: async (rfc: string, fechaInicio?: string, fechaFin?: string): Promise<AnalisisImpuestosData> => {
    console.log('📊 Obteniendo análisis completo de impuestos para RFC:', rfc);
    let url = `/api/v1/cfdi/dashboard/analisis-impuestos/${rfc}`;
    
    const params = new URLSearchParams();
    if (fechaInicio) params.append('fecha_inicio', fechaInicio);
    if (fechaFin) params.append('fecha_fin', fechaFin);
    
    if (params.toString()) {
      url += `?${params.toString()}`;
    }
    
    const response = await api.get(url);
    console.log('📊 Análisis de impuestos obtenido:', response.data);
    return response.data;
  },

  obtenerAnalisisIVA: async (rfc: string, fechaInicio: string, fechaFin: string): Promise<AnalisisIVAData> => {
    console.log('📊 Obteniendo análisis de IVA para RFC:', rfc);
    const response = await api.get(`/api/v1/cfdi/dashboard/analisis-iva/${rfc}?fecha_inicio=${fechaInicio}&fecha_fin=${fechaFin}`);
    console.log('📊 Análisis de IVA obtenido:', response.data);
    return response.data;
  },

  obtenerAnalisisIEPS: async (rfc: string, fechaInicio: string, fechaFin: string): Promise<AnalisisIEPSData> => {
    console.log('📊 Obteniendo análisis de IEPS para RFC:', rfc);
    const response = await api.get(`/api/v1/cfdi/dashboard/analisis-ieps/${rfc}?fecha_inicio=${fechaInicio}&fecha_fin=${fechaFin}`);
    console.log('📊 Análisis de IEPS obtenido:', response.data);
    return response.data;
  },

  obtenerAnalisisRetenciones: async (rfc: string, fechaInicio: string, fechaFin: string): Promise<AnalisisRetencionesData> => {
    console.log('📊 Obteniendo análisis de retenciones para RFC:', rfc);
    const response = await api.get(`/api/v1/cfdi/dashboard/analisis-retenciones/${rfc}?fecha_inicio=${fechaInicio}&fecha_fin=${fechaFin}`);
    console.log('📊 Análisis de retenciones obtenido:', response.data);
    return response.data;
  }
};

// Export para compatibilidad
export default api;
