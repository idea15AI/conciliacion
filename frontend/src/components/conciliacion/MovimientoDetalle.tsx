'use client';

import { Fragment } from 'react';
import { Dialog, Transition } from '@headlessui/react';
import { 
  XMarkIcon,
  DocumentTextIcon,
  CurrencyDollarIcon,
  CalendarIcon,
  BanknotesIcon,
  CheckCircleIcon,
  XCircleIcon,
  ExclamationTriangleIcon
} from '@heroicons/react/24/outline';
import { MovimientoBancario } from '@/types';

interface MovimientoDetalleProps {
  movimiento: MovimientoBancario | null;
  isOpen: boolean;
  onClose: () => void;
}

export default function MovimientoDetalle({ movimiento, isOpen, onClose }: MovimientoDetalleProps) {
  if (!movimiento) return null;

  const getEstadoIcon = (estado: string) => {
    switch (estado) {
      case 'CONCILIADO':
        return <CheckCircleIcon className="w-5 h-5 text-green-500" />;
      case 'PENDIENTE':
        return <ExclamationTriangleIcon className="w-5 h-5 text-yellow-500" />;
      case 'MANUAL':
        return <XCircleIcon className="w-5 h-5 text-red-500" />;
      default:
        return <ExclamationTriangleIcon className="w-5 h-5 text-gray-500" />;
    }
  };

  const getEstadoColor = (estado: string) => {
    switch (estado) {
      case 'CONCILIADO':
        return 'bg-green-100 text-green-800';
      case 'PENDIENTE':
        return 'bg-yellow-100 text-yellow-800';
      case 'MANUAL':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getTipoColor = (tipo: string) => {
    return tipo === 'cargo' 
      ? 'bg-red-100 text-red-800' 
      : 'bg-green-100 text-green-800';
  };

  return (
    <Transition appear show={isOpen} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={onClose}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black bg-opacity-25" />
        </Transition.Child>

        <div className="fixed inset-0 overflow-y-auto">
          <div className="flex min-h-full items-center justify-center p-4 text-center">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 scale-95"
              enterTo="opacity-100 scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 scale-100"
              leaveTo="opacity-0 scale-95"
            >
              <Dialog.Panel className="w-full max-w-2xl transform overflow-hidden rounded-2xl bg-white p-6 text-left align-middle shadow-xl transition-all">
                <div className="flex items-center justify-between mb-6">
                  <Dialog.Title
                    as="h3"
                    className="text-lg font-medium leading-6 text-gray-900 flex items-center"
                  >
                    <DocumentTextIcon className="w-6 h-6 text-blue-600 mr-2" />
                    Detalle del Movimiento
                  </Dialog.Title>
                  <button
                    type="button"
                    className="rounded-md text-gray-400 hover:text-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    onClick={onClose}
                  >
                    <XMarkIcon className="w-6 h-6" />
                  </button>
                </div>

                <div className="space-y-6">
                  {/* Información Principal */}
                  <div className="bg-gray-50 rounded-lg p-4">
                    <h4 className="text-sm font-medium text-gray-900 mb-3">Información Principal</h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">ID</label>
                        <p className="mt-1 text-sm text-gray-900">#{movimiento.id}</p>
                      </div>
                      <div>
                        <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">Archivo ID</label>
                        <p className="mt-1 text-sm text-gray-900">#{movimiento.archivo_id}</p>
                      </div>
                      <div>
                        <label className="text-xs font-medium text-gray-500 uppercase tracking-wide flex items-center">
                          <CalendarIcon className="w-4 h-4 mr-1" />
                          Fecha
                        </label>
                        <p className="mt-1 text-sm text-gray-900">
                          {new Date(movimiento.fecha).toLocaleDateString('es-MX', {
                            weekday: 'long',
                            year: 'numeric',
                            month: 'long',
                            day: 'numeric'
                          })}
                        </p>
                      </div>
                      <div>
                        <label className="text-xs font-medium text-gray-500 uppercase tracking-wide flex items-center">
                          <CurrencyDollarIcon className="w-4 h-4 mr-1" />
                          Monto
                        </label>
                        <p className="mt-1 text-lg font-semibold text-gray-900">
                          ${movimiento.monto.toLocaleString('es-MX', { minimumFractionDigits: 2 })}
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Estado y Tipo */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">Estado</label>
                      <div className="mt-1 flex items-center">
                        {getEstadoIcon(movimiento.estado)}
                        <span className={`ml-2 inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getEstadoColor(movimiento.estado)}`}>
                          {movimiento.estado}
                        </span>
                      </div>
                    </div>
                    <div>
                      <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">Tipo</label>
                      <div className="mt-1">
                        <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getTipoColor(movimiento.tipo)}`}>
                          {movimiento.tipo.toUpperCase()}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Concepto */}
                  <div>
                    <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">Concepto</label>
                    <p className="mt-1 text-sm text-gray-900 bg-gray-50 p-3 rounded-md">
                      {movimiento.concepto}
                    </p>
                  </div>

                  {/* Referencia y Saldo */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {movimiento.referencia && (
                      <div>
                        <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">Referencia</label>
                        <p className="mt-1 text-sm text-gray-900 font-mono">
                          {movimiento.referencia}
                        </p>
                      </div>
                    )}
                    <div>
                      <label className="text-xs font-medium text-gray-500 uppercase tracking-wide flex items-center">
                        <BanknotesIcon className="w-4 h-4 mr-1" />
                        Saldo Resultante
                      </label>
                      <p className="mt-1 text-sm text-gray-900 font-semibold">
                        {movimiento.saldo !== null ? (
                          `$${movimiento.saldo.toLocaleString('es-MX', { minimumFractionDigits: 2 })}`
                        ) : (
                          <span className="text-gray-500 italic">No disponible</span>
                        )}
                      </p>
                    </div>
                  </div>

                  {/* Información de Conciliación */}
                  {(movimiento.cfdi_uuid || movimiento.nivel_confianza || movimiento.metodo_conciliacion) && (
                    <div className="bg-blue-50 rounded-lg p-4">
                      <h4 className="text-sm font-medium text-blue-900 mb-3">Información de Conciliación</h4>
                      <div className="space-y-3">
                        {movimiento.cfdi_uuid && (
                          <div>
                            <label className="text-xs font-medium text-blue-700 uppercase tracking-wide">UUID CFDI</label>
                            <p className="mt-1 text-sm text-blue-900 font-mono bg-white p-2 rounded border">
                              {movimiento.cfdi_uuid}
                            </p>
                          </div>
                        )}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          {movimiento.nivel_confianza && (
                            <div>
                              <label className="text-xs font-medium text-blue-700 uppercase tracking-wide">Nivel de Confianza</label>
                              <div className="mt-1 flex items-center">
                                <div className="flex-1 bg-gray-200 rounded-full h-2">
                                  <div 
                                    className="bg-blue-600 h-2 rounded-full" 
                                    style={{ width: `${(movimiento.nivel_confianza || 0) * 100}%` }}
                                  ></div>
                                </div>
                                <span className="ml-2 text-sm font-medium text-blue-900">
                                  {((movimiento.nivel_confianza || 0) * 100).toFixed(1)}%
                                </span>
                              </div>
                            </div>
                          )}
                          {movimiento.metodo_conciliacion && (
                            <div>
                              <label className="text-xs font-medium text-blue-700 uppercase tracking-wide">Método</label>
                              <p className="mt-1 text-sm text-blue-900">
                                {movimiento.metodo_conciliacion}
                              </p>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Observaciones */}
                  {movimiento.observaciones && (
                    <div>
                      <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">Observaciones</label>
                      <p className="mt-1 text-sm text-gray-900 bg-yellow-50 p-3 rounded-md border border-yellow-200">
                        {movimiento.observaciones}
                      </p>
                    </div>
                  )}

                  {/* Fechas de Sistema */}
                  <div className="border-t pt-4">
                    <h4 className="text-sm font-medium text-gray-900 mb-3">Información del Sistema</h4>
                    <div className="text-xs text-gray-500">
                      <p>Creado: {new Date(movimiento.created_at).toLocaleString('es-MX')}</p>
                    </div>
                  </div>
                </div>

                <div className="mt-6 flex justify-end">
                  <button
                    type="button"
                    className="inline-flex justify-center rounded-md border border-transparent bg-blue-100 px-4 py-2 text-sm font-medium text-blue-900 hover:bg-blue-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
                    onClick={onClose}
                  >
                    Cerrar
                  </button>
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition>
  );
} 