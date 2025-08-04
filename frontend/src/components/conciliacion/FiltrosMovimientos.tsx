'use client';

import { useState } from 'react';
import { 
  MagnifyingGlassIcon,
  FunnelIcon,
  XMarkIcon,
  CalendarDaysIcon
} from '@heroicons/react/24/outline';

interface FiltrosMovimientosProps {
  onFiltrosChange: (filtros: Record<string, string>) => void;
  loading?: boolean;
}

export default function FiltrosMovimientos({ onFiltrosChange, loading = false }: FiltrosMovimientosProps) {
  const [filtros, setFiltros] = useState({
    concepto: '',
    estado: '',
    tipo: '',
    fecha_inicio: '',
    fecha_fin: '',
    monto_min: '',
    monto_max: ''
  });

  const [mostrarFiltrosAvanzados, setMostrarFiltrosAvanzados] = useState(false);

  const handleInputChange = (campo: string, valor: string) => {
    const nuevosFiltros = { ...filtros, [campo]: valor };
    setFiltros(nuevosFiltros);
    
    // Limpiar valores vacíos antes de enviar
    const filtrosLimpios = Object.fromEntries(
      Object.entries(nuevosFiltros).filter(([, value]) => value !== '')
    );
    
    onFiltrosChange(filtrosLimpios);
  };

  const limpiarFiltros = () => {
    const filtrosVacios = {
      concepto: '',
      estado: '',
      tipo: '',
      fecha_inicio: '',
      fecha_fin: '',
      monto_min: '',
      monto_max: ''
    };
    setFiltros(filtrosVacios);
    onFiltrosChange({});
  };

  const hayFiltrosAplicados = Object.values(filtros).some(valor => valor !== '');

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 mb-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center">
          <FunnelIcon className="w-5 h-5 text-gray-500 mr-2" />
          <h3 className="text-sm font-medium text-gray-900">Filtros</h3>
          {hayFiltrosAplicados && (
            <span className="ml-2 inline-flex items-center px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 rounded-full">
              Activos
            </span>
          )}
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={() => setMostrarFiltrosAvanzados(!mostrarFiltrosAvanzados)}
            className="text-sm text-blue-600 hover:text-blue-800 font-medium"
          >
            {mostrarFiltrosAvanzados ? 'Ocultar filtros' : 'Más filtros'}
          </button>
          {hayFiltrosAplicados && (
            <button
              onClick={limpiarFiltros}
              className="inline-flex items-center text-sm text-red-600 hover:text-red-800"
            >
              <XMarkIcon className="w-4 h-4 mr-1" />
              Limpiar
            </button>
          )}
        </div>
      </div>

      <div className="space-y-4">
        {/* Filtros básicos */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Búsqueda por concepto */}
          <div className="relative">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Buscar en concepto
            </label>
            <div className="relative">
              <input
                type="text"
                value={filtros.concepto}
                onChange={(e) => handleInputChange('concepto', e.target.value)}
                placeholder="Buscar movimientos..."
                className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md leading-5 bg-white placeholder-gray-500 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                disabled={loading}
              />
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <MagnifyingGlassIcon className="h-5 w-5 text-gray-400" />
              </div>
            </div>
          </div>

          {/* Estado */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Estado
            </label>
            <select
              value={filtros.estado}
              onChange={(e) => handleInputChange('estado', e.target.value)}
              className="block w-full py-2 pl-3 pr-10 border border-gray-300 bg-white rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
              disabled={loading}
            >
              <option value="">Todos los estados</option>
              <option value="pendiente">Pendiente</option>
              <option value="conciliado">Conciliado</option>
              <option value="manual">Manual</option>
            </select>
          </div>

          {/* Tipo */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Tipo
            </label>
            <select
              value={filtros.tipo}
              onChange={(e) => handleInputChange('tipo', e.target.value)}
              className="block w-full py-2 pl-3 pr-10 border border-gray-300 bg-white rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
              disabled={loading}
            >
              <option value="">Todos los tipos</option>
              <option value="cargo">Cargo</option>
              <option value="abono">Abono</option>
            </select>
          </div>
        </div>

        {/* Filtros avanzados */}
        {mostrarFiltrosAvanzados && (
          <div className="border-t pt-4 space-y-4">
            {/* Rango de fechas */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2 flex items-center">
                <CalendarDaysIcon className="w-4 h-4 mr-1" />
                Rango de fechas
              </label>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Desde</label>
                  <input
                    type="date"
                    value={filtros.fecha_inicio}
                    onChange={(e) => handleInputChange('fecha_inicio', e.target.value)}
                    className="block w-full py-2 px-3 border border-gray-300 bg-white rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                    disabled={loading}
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Hasta</label>
                  <input
                    type="date"
                    value={filtros.fecha_fin}
                    onChange={(e) => handleInputChange('fecha_fin', e.target.value)}
                    className="block w-full py-2 px-3 border border-gray-300 bg-white rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                    disabled={loading}
                  />
                </div>
              </div>
            </div>

            {/* Rango de montos */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Rango de montos
              </label>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Monto mínimo</label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                      <span className="text-gray-500 sm:text-sm">$</span>
                    </div>
                    <input
                      type="number"
                      step="0.01"
                      value={filtros.monto_min}
                      onChange={(e) => handleInputChange('monto_min', e.target.value)}
                      placeholder="0.00"
                      className="block w-full pl-7 pr-3 py-2 border border-gray-300 rounded-md leading-5 bg-white placeholder-gray-500 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                      disabled={loading}
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Monto máximo</label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                      <span className="text-gray-500 sm:text-sm">$</span>
                    </div>
                    <input
                      type="number"
                      step="0.01"
                      value={filtros.monto_max}
                      onChange={(e) => handleInputChange('monto_max', e.target.value)}
                      placeholder="0.00"
                      className="block w-full pl-7 pr-3 py-2 border border-gray-300 rounded-md leading-5 bg-white placeholder-gray-500 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                      disabled={loading}
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Indicador de carga */}
      {loading && (
        <div className="mt-4 flex items-center justify-center py-2">
          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
          <span className="ml-2 text-sm text-gray-500">Aplicando filtros...</span>
        </div>
      )}
    </div>
  );
} 