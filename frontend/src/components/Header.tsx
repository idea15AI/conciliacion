"use client";

import { useState, useEffect } from 'react';
import { useConciliacionContext } from '@/contexts/ConciliacionContext';
import { conciliacionAPI, EmpresaContribuyente } from '@/lib/api';

export default function Header() {
  const { rfcEmpresa, setRfcEmpresa } = useConciliacionContext();
  const [empresas, setEmpresas] = useState<EmpresaContribuyente[]>([]);
  const [loading, setLoading] = useState(true);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);

  useEffect(() => {
    const fetchEmpresas = async () => {
      try {
        const empresasData = await conciliacionAPI.getEmpresasContribuyentes();
        setEmpresas(empresasData);
        
        // Si no hay RFC seleccionado y hay empresas, seleccionar la primera
        if (!rfcEmpresa && empresasData.length > 0) {
          setRfcEmpresa(empresasData[0].rfc);
        }
      } catch (error) {
        console.error('Error fetching empresas:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchEmpresas();
  }, [rfcEmpresa, setRfcEmpresa]);

  const empresaActual = empresas.find(emp => emp.rfc === rfcEmpresa);

  const handleRfcChange = (rfc: string) => {
    setRfcEmpresa(rfc);
    setIsDropdownOpen(false);
  };

  return (
    <header className="backdrop-blur-2xl bg-transparent border-none sticky top-0 z-10">
      <div className="px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center py-2.5">
          {/* Logo and RFC Selector */}
          <div className="flex items-center space-x-4">
            <div className="text-lg font-semibold text-gray-900">
               {"         "}
            </div>
            
            {/* RFC Selector */}
            <div className="relative ml-10 mt-3">
              <button
                onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                className="flex items-center space-x-1 text-white hover:opacity-80 transition-opacity focus:outline-none"
                disabled={loading}
              >
                {loading ? (
                  <div className="flex items-center space-x-2">
                    <div className="w-4 h-4 border-2 border-gray-300 border-t-blue-600 rounded-full animate-spin"></div>
                    <span className="text-sm text-gray-500">Cargando...</span>
                  </div>
                ) : (
                  <div className="flex items-center space-x-2">
                    <div className="flex flex-col items-start">
                      <span className="text-sm font-medium text-gray-900">
                        {empresaActual?.rfc || rfcEmpresa}
                      </span>
                      {empresaActual && (
                        <span className="text-xs text-gray-500 truncate max-w-48">
                          {empresaActual.razon_social}
                        </span>
                      )}
                    </div>
                    <svg 
                      className={`w-4 h-4 text-gray-400 transition-transform ${isDropdownOpen ? 'rotate-180' : ''}`} 
                      fill="none" 
                      stroke="currentColor" 
                      viewBox="0 0 24 24"
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  </div>
                )}
              </button>

              {/* Dropdown */}
              {isDropdownOpen && !loading && (
                <div className="absolute top-full mt-1 w-80 bg-white border border-gray-200 rounded-lg shadow-lg z-50 max-h-96 overflow-y-auto">
                  {empresas.length === 0 ? (
                    <div className="px-4 py-3 text-sm text-gray-500">
                      No hay empresas disponibles
                    </div>
                  ) : (
                    empresas.map((empresa) => (
                      <button
                        key={empresa.id}
                        onClick={() => handleRfcChange(empresa.rfc)}
                        className={`w-full px-4 py-3 text-left hover:bg-gray-50 focus:bg-gray-50 focus:outline-none transition-colors border-b border-gray-100 last:border-b-0 ${
                          empresa.rfc === rfcEmpresa ? 'bg-blue-50 text-blue-900' : 'text-gray-900'
                        }`}
                      >
                        <div className="flex flex-col">
                          <span className="font-medium text-sm">
                            {empresa.rfc}
                          </span>
                          <span className="text-xs text-gray-500 truncate">
                            {empresa.razon_social}
                          </span>
                        </div>
                      </button>
                    ))
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Right side */}
          <div className="flex items-center space-x-4">
            <div className="text-sm text-gray-600">
              Sistema de Conciliación Bancaria
            </div>
          </div>
        </div>
      </div>
      <div className="h-[2px] w-full backdrop-blur-2xl bg-white/5" />


      {/* Backdrop for dropdown */}
      {isDropdownOpen && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => setIsDropdownOpen(false)}
        />
      )}
    </header>
  );
}
