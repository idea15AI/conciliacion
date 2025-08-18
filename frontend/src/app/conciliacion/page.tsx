'use client';

import Layout from '@/components/Layout';
import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useConciliacionContext } from '@/contexts/ConciliacionContext';
import { 
  DocumentArrowUpIcon, 
  CurrencyDollarIcon, 
  ExclamationTriangleIcon,
  DocumentTextIcon,
  BanknotesIcon,
  CheckCircleIcon,
  XCircleIcon,
  PlayIcon,
  ArrowPathIcon,
  EyeIcon
} from '@heroicons/react/24/outline';
import { conciliacionAPI } from '@/lib/api';
import { 
  ReporteConciliacion, 
  MovimientoBancario,
  ArchivoBancario,
  ConciliacionRequest,
  ResultadoOCR
} from '@/types';
import MovimientoDetalle from '@/components/conciliacion/MovimientoDetalle';
import FiltrosMovimientos from '@/components/conciliacion/FiltrosMovimientos';

// Componente para subir estado de cuenta
function SubirEstadoCuenta({ rfc, onSuccess }: { rfc: string, onSuccess: () => void }) {
  const [isUploading, setIsUploading] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [uploadResult, setUploadResult] = useState<ResultadoOCR | null>(null);

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0];
    if (selectedFile) {
      setFile(selectedFile);
      setUploadResult(null);
    }
  };

  const handleUpload = async () => {
    if (!file || !rfc) return;

    setIsUploading(true);
    try {
      const result = await conciliacionAPI.subirEstadoCuenta(rfc, file);
      setUploadResult(result);
      if (result.exito) {
        onSuccess();
      }
    } catch (error) {
      console.error('Error al subir archivo:', error);
      setUploadResult({
        exito: false,
        mensaje: 'Error al procesar el archivo',
        total_movimientos_extraidos: 0,
        errores: ['Error de conexión'],
        tiempo_procesamiento_segundos: 0
      });
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div className="flex items-center mb-4">
        <DocumentArrowUpIcon className="w-6 h-6 text-blue-600 mr-2" />
        <h3 className="text-lg font-semibold text-gray-900">Subir Estado de Cuenta</h3>
      </div>
      
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Seleccionar archivo PDF
          </label>
          <input 
            type="file" 
            accept=".pdf"
            onChange={handleFileSelect}
            className="block w-full text-sm text-gray-500 
                       file:mr-4 file:py-2 file:px-4
                       file:rounded-md file:border-0
                       file:text-sm file:font-semibold
                       file:bg-blue-50 file:text-blue-700
                       hover:file:bg-blue-100"
          />
        </div>

        {file && (
          <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
            <div>
              <p className="text-sm font-medium text-gray-900">{file.name}</p>
              <p className="text-sm text-gray-500">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
            </div>
            <button
              onClick={handleUpload}
              disabled={isUploading}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:bg-gray-400"
            >
              {isUploading ? (
                <>
                  <ArrowPathIcon className="w-4 h-4 mr-2 animate-spin" />
                  Procesando...
                </>
              ) : (
                <>
                  <DocumentArrowUpIcon className="w-4 h-4 mr-2" />
                  Procesar
                </>
              )}
            </button>
          </div>
        )}

        {uploadResult && (
          <div className={`p-4 rounded-lg ${uploadResult.exito ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}>
            <div className="flex items-center">
              {uploadResult.exito ? (
                <CheckCircleIcon className="w-5 h-5 text-green-500 mr-2" />
              ) : (
                <XCircleIcon className="w-5 h-5 text-red-500 mr-2" />
              )}
              <h4 className={`font-medium ${uploadResult.exito ? 'text-green-800' : 'text-red-800'}`}>
                {uploadResult.mensaje}
              </h4>
            </div>
            {uploadResult.exito && (
              <div className="mt-2 text-sm text-green-700">
                <p>Banco detectado: <strong>{(uploadResult.banco_detectado || 'No especificado').toUpperCase()}</strong></p>
                <p>Movimientos extraídos: <strong>{uploadResult.total_movimientos_extraidos}</strong></p>
                <p>Tiempo de procesamiento: <strong>{uploadResult.tiempo_procesamiento_segundos}s</strong></p>
              </div>
            )}
            {uploadResult.errores && uploadResult.errores.length > 0 && (
              <div className="mt-2">
                <p className="text-sm font-medium text-red-800">Errores:</p>
                <ul className="list-disc list-inside text-sm text-red-700">
                  {uploadResult.errores.map((error, index) => (
                    <li key={index}>{error}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// Componente para tarjetas de estadísticas
function TarjetaEstadistica({ 
  titulo, 
  valor, 
  icono: Icon, 
  color = 'blue',
  descripcion
}: {
  titulo: string;
  valor: string | number;
  icono: React.ComponentType<{ className?: string }>;
  color?: 'green' | 'red' | 'blue' | 'yellow';
  descripcion?: string;
}) {
  const bubbleClasses = 'w-10 h-10 rounded-full flex items-center justify-center bg-blue-600 text-white shadow-sm';

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div className="flex items-center">
        <div className="flex-shrink-0">
          <div className={bubbleClasses}>
            <Icon className="w-5 h-5" />
          </div>
        </div>
        <div className="ml-4 flex-1">
          <p className="text-sm font-medium text-gray-500">{titulo}</p>
          <p className="text-2xl font-semibold text-gray-900">{valor}</p>
          {descripcion && (
            <p className="text-xs text-green-600 mt-1">{descripcion}</p>
          )}
        </div>
      </div>
    </div>
  );
}

// Componente para ejecutar conciliación
function EjecutarConciliacion({ rfc, onSuccess }: { rfc: string, onSuccess: () => void }) {
  const [isExecuting, setIsExecuting] = useState(false);
  const [mesAnio, setMesAnio] = useState({ mes: new Date().getMonth() + 1, anio: new Date().getFullYear() });
  const [tolerancias, setTolerancias] = useState({ monto: 1.0, dias: 3 });

  const executeWithRequest = async (request: ConciliacionRequest) => {
    return await conciliacionAPI.ejecutarConciliacion(request);
  };

  const executeInternal = async (forzarReproceso: boolean = false) => {
    if (!rfc) return;

    setIsExecuting(true);
    try {
      const request: ConciliacionRequest = {
        rfc_empresa: rfc,
        mes: mesAnio.mes,
        anio: mesAnio.anio,
        tolerancia_monto: tolerancias.monto,
        dias_tolerancia: tolerancias.dias,
        forzar_reproceso: forzarReproceso
      };

      await executeWithRequest(request);
      onSuccess();
    } catch (error: unknown) {
      console.error('Error al ejecutar conciliación:', error);
      
      // Manejar error 409 - conciliación ya existe
      if (error && typeof error === 'object' && 'response' in error) {
        const axiosError = error as { response: { status: number } };
        if (axiosError.response?.status === 409) {
          const confirmed = window.confirm(
            `Ya existe una conciliación para ${mesAnio.mes}/${mesAnio.anio}.\n\n` +
            '¿Deseas reprocesar y sobrescribir los resultados existentes?\n\n' +
            'Esto aplicará las correcciones del OCR a los movimientos.'
          );
          
          if (confirmed) {
            // Reintentar con forzar_reproceso = true
            try {
              await executeInternal(true);
              return;
            } catch (retryError) {
              console.error('Error al forzar reproceso:', retryError);
              alert('Error al forzar el reproceso. Revisa la consola para más detalles.');
            }
          }
          return;
        }
      }
      
      // Otros errores
      alert('Error al ejecutar conciliación. Revisa la consola para más detalles.');
    } finally {
      setIsExecuting(false);
    }
  };

  const handleExecute = () => {
    executeInternal(false);
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div className="flex items-center mb-4">
        <PlayIcon className="w-6 h-6 text-green-600 mr-2" />
        <h3 className="text-lg font-semibold text-gray-900">Ejecutar Conciliación</h3>
      </div>
      
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Mes</label>
            <select 
              value={mesAnio.mes}
              onChange={(e) => setMesAnio({...mesAnio, mes: parseInt(e.target.value)})}
              className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
            >
              {Array.from({length: 12}, (_, i) => (
                <option key={i+1} value={i+1}>
                  {new Date(2024, i, 1).toLocaleDateString('es-ES', { month: 'long' })}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Año</label>
            <select 
              value={mesAnio.anio}
              onChange={(e) => setMesAnio({...mesAnio, anio: parseInt(e.target.value)})}
              className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
            >
              {Array.from({length: 5}, (_, i) => {
                const year = new Date().getFullYear() - i;
                return <option key={year} value={year}>{year}</option>;
              })}
            </select>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Tolerancia Monto ($)
            </label>
            <input
              type="number"
              step="0.01"
              value={tolerancias.monto}
              onChange={(e) => setTolerancias({...tolerancias, monto: parseFloat(e.target.value)})}
              className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Tolerancia Días
            </label>
            <input
              type="number"
              value={tolerancias.dias}
              onChange={(e) => setTolerancias({...tolerancias, dias: parseInt(e.target.value)})}
              className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
            />
          </div>
        </div>

        <button
          onClick={handleExecute}
          disabled={isExecuting}
          className="w-full inline-flex justify-center items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:bg-gray-400"
        >
          {isExecuting ? (
            <>
              <ArrowPathIcon className="w-4 h-4 mr-2 animate-spin" />
              Ejecutando conciliación...
            </>
          ) : (
            <>
              <PlayIcon className="w-4 h-4 mr-2" />
              Ejecutar Conciliación
            </>
          )}
        </button>
      </div>
    </div>
  );
}

// Componente principal
export default function ConciliacionPage() {
  const { rfcEmpresa } = useConciliacionContext();
  const [estadisticas, setEstadisticas] = useState<ReporteConciliacion | null>(null);
  const [movimientos, setMovimientos] = useState<MovimientoBancario[]>([]);
  const [archivos, setArchivos] = useState<ArchivoBancario[]>([]);
  const [loading, setLoading] = useState(true);
  const [movimientoSeleccionado, setMovimientoSeleccionado] = useState<MovimientoBancario | null>(null);
  const [mostrarDetalle, setMostrarDetalle] = useState(false);
  const [filtrosActivos, setFiltrosActivos] = useState<Record<string, string>>({});

  const cargarDatos = async () => {
    if (!rfcEmpresa) return;

    setLoading(true);
    try {
      // Mapear RFC a empresa ID (en un caso real esto vendría del backend)
      const empresaId = rfcEmpresa === 'IDE2001209V6' ? 2 : 1;
      const [statsData, movimientosData, archivosData] = await Promise.all([
        conciliacionAPI.obtenerEstadisticas(empresaId),
        conciliacionAPI.obtenerMovimientos(empresaId, { page: 1, size: 50, ...filtrosActivos }),
        conciliacionAPI.obtenerArchivos(empresaId)
      ]);

      setEstadisticas(statsData);
      setMovimientos(movimientosData.movimientos || []);
      setArchivos(archivosData.archivos || []);
    } catch (error) {
      console.error('Error cargando datos:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    cargarDatos();
  }, [rfcEmpresa, filtrosActivos]);

  const handleFiltrosChange = (nuevosFiltros: Record<string, string>) => {
    setFiltrosActivos(nuevosFiltros);
  };

  const handleVerDetalle = (movimiento: MovimientoBancario) => {
    setMovimientoSeleccionado(movimiento);
    setMostrarDetalle(true);
  };

  if (!rfcEmpresa) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <ExclamationTriangleIcon className="w-12 h-12 text-yellow-500 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              Empresa no seleccionada
            </h3>
            <p className="text-gray-600">
              Por favor selecciona una empresa para ver la conciliación bancaria.
            </p>
          </div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {loading ? (
          <div className="flex justify-center py-12">
            <ArrowPathIcon className="w-8 h-8 text-blue-600 animate-spin" />
          </div>
        ) : (
          <>
            {/* Estadísticas */}
            {estadisticas && (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
                <TarjetaEstadistica
                  titulo="Total Movimientos"
                  valor={estadisticas.movimientos.total}
                  icono={DocumentTextIcon}
                  color="blue"
                />
                <TarjetaEstadistica
                  titulo="Conciliados"
                  valor={estadisticas.movimientos.conciliados}
                  icono={CheckCircleIcon}
                  color="green"
                  descripcion={`${estadisticas.movimientos.porcentaje_conciliacion.toFixed(1)}%`}
                />
                <TarjetaEstadistica
                  titulo="Pendientes"
                  valor={estadisticas.movimientos.pendientes}
                  icono={XCircleIcon}
                  color="red"
                />
                <TarjetaEstadistica
                  titulo="Monto Total"
                  valor={`$${estadisticas.movimientos.monto_total.toLocaleString('es-MX', { minimumFractionDigits: 2 })}`}
                  icono={CurrencyDollarIcon}
                  color="blue"
                />
              </div>
            )}

            {/* Bloques hero de acciones principales - estilo solicitado */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
              {/* Subir Estado de Cuenta - azul sólido/gradiente */}
              <div className="relative overflow-hidden rounded-2xl p-8 bg-gradient-to-br from-blue-600 to-blue-500 text-white shadow-md">
                <div className="max-w-xl">
                  <h3 className="text-2xl font-semibold mb-2">Subir Estado de Cuenta</h3>
                  <p className="opacity-90 mb-6">Carga tu archivo PDF para extraer movimientos bancarios automáticamente.</p>
                  <Link href="/subir-estado" className="inline-flex items-center px-4 py-2 rounded-md bg-white/75 text-gray-700 font-medium hover:bg-white transition shadow">
                    Ir a Subir Archivo
                  </Link>
                </div>
                <div className="absolute -right-6 bottom-6 opacity-30">
                  <div className="w-44 h-44 rounded-full bg-white/20" />
                </div>
              </div>

              {/* Ejecutar Conciliación - panel oscuro azulado */}
              <div className="rounded-2xl p-8 bg-slate-900 text-white shadow-md">
                <h3 className="text-2xl font-semibold mb-2">Ejecutar Conciliación</h3>
                <p className="opacity-90 mb-6">Configura los parámetros y ejecuta el proceso de conciliación automática.</p>
                <Link href="/conciliacion" className="inline-flex items-center px-4 py-2 rounded-md bg-gray-700 text-white font-medium hover:bg-gray-900 transition shadow">
                  Ir a Configuración
                </Link>
              </div>
            </div>

            {/* Filtros de movimientos */}
            <FiltrosMovimientos 
              onFiltrosChange={handleFiltrosChange}
              loading={loading}
            />

            {/* Movimientos recientes */}
            {movimientos.length > 0 && (
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 mb-8">
                <div className="px-6 py-4 border-b border-gray-200">
                  <h3 className="text-lg font-semibold text-gray-900">Movimientos Bancarios</h3>
                </div>
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Fecha
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Concepto
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Monto
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Tipo
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Estado
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Acciones
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {movimientos.map((movimiento) => (
                        <tr key={movimiento.id}>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                            {new Date(movimiento.fecha).toLocaleDateString('es-MX')}
                          </td>
                          <td className="px-6 py-4 text-sm text-gray-900">
                            {movimiento.concepto.substring(0, 50)}...
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                            ${movimiento.monto.toLocaleString('es-MX', { minimumFractionDigits: 2 })}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                              movimiento.tipo === 'cargo' 
                                ? 'bg-red-100 text-red-800' 
                                : 'bg-green-100 text-green-800'
                            }`}>
                              {movimiento.tipo.toUpperCase()}
                            </span>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                              movimiento.estado === 'CONCILIADO' 
                                ? 'bg-green-100 text-green-800' 
                                : movimiento.estado === 'PENDIENTE'
                                ? 'bg-yellow-100 text-yellow-800'
                                : 'bg-blue-100 text-blue-800'
                            }`}>
                              {movimiento.estado}
                            </span>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                            <button
                              onClick={() => handleVerDetalle(movimiento)}
                              className="text-blue-600 hover:text-blue-900 inline-flex items-center"
                            >
                              <EyeIcon className="w-4 h-4 mr-1" />
                              Ver detalle
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Archivos procesados */}
            {archivos.length > 0 && (
              <div className="bg-white rounded-lg shadow-sm border border-gray-200">
                <div className="px-6 py-4 border-b border-gray-200">
                  <h3 className="text-lg font-semibold text-gray-900">Archivos Procesados</h3>
                </div>
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Archivo
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Banco
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Período
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Movimientos
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Estado
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {archivos.map((archivo) => (
                        <tr key={archivo.id}>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                            {archivo.nombre_archivo}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                            {archivo.banco.toUpperCase()}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                            {new Date(archivo.periodo_inicio).toLocaleDateString('es-MX')} - {new Date(archivo.periodo_fin).toLocaleDateString('es-MX')}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                            {archivo.total_movimientos}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                              archivo.procesado_exitosamente 
                                ? 'bg-green-100 text-green-800' 
                                : 'bg-red-100 text-red-800'
                            }`}>
                              {archivo.procesado_exitosamente ? 'EXITOSO' : 'ERROR'}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Mensaje cuando no hay movimientos */}
            {!loading && movimientos.length === 0 && (
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-8 text-center">
                <div className="text-gray-500">
                  <DocumentTextIcon className="mx-auto h-12 w-12 text-gray-400 mb-4" />
                  <h3 className="text-lg font-medium text-gray-900 mb-2">No hay movimientos</h3>
                  <p className="text-sm text-gray-500">
                    No se encontraron movimientos bancarios con los filtros aplicados.
                  </p>
                  {Object.keys(filtrosActivos).length > 0 && (
                    <p className="text-sm text-blue-600 mt-2">
                      Intenta ajustar los filtros o cargar un estado de cuenta.
                    </p>
                  )}
                </div>
              </div>
            )}
          </>
        )}

        {/* Modal de detalle del movimiento */}
        <MovimientoDetalle 
          movimiento={movimientoSeleccionado}
          isOpen={mostrarDetalle}
          onClose={() => setMostrarDetalle(false)}
        />
      </div>
    </Layout>
  );
} 