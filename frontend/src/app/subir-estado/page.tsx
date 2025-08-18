'use client';

import Layout from '@/components/Layout';
import Link from 'next/link';
import { DocumentArrowUpIcon } from '@heroicons/react/24/outline';
import { useState } from 'react';

export default function SubirEstadoPage() {
  const [showTable, setShowTable] = useState(false);

  return (
    <Layout>
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">

        {/* Hero azul sólido/gradiente como en diseño */}
        <div className="relative overflow-hidden rounded-2xl p-8 mb-8 bg-gradient-to-br from-blue-600 to-blue-500 text-white shadow-md">
          <div className="max-w-2xl">
            <h3 className="text-2xl font-semibold mb-2">Sube tu archivo de estado de cuenta</h3>
            <p className="opacity-90 mb-6">El sistema procesará el PDF y extraerá los movimientos de forma automática.</p>
            <Link
              href="#tabla-subida"
              className="inline-flex items-center px-4 py-2 rounded-md bg-white/75 text-gray-700 font-medium hover:bg-white transition shadow"
              onClick={(e) => {
                e.preventDefault();
                setShowTable(true);
                setTimeout(() => {
                  document.getElementById('tabla-subida')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }, 0);
              }}
            >
              Subir archivo
            </Link>
          </div>
          <div className="absolute -right-6 bottom-6 opacity-30">
            <DocumentArrowUpIcon className="w-48 h-48 text-white" />
          </div>
        </div>

        {/* Tabla de resultados */}
        {showTable && (
          <div id="tabla-subida" className="bg-white rounded-lg shadow-sm border border-gray-200">
            <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">Movimientos extraídos</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Fecha</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Referencia</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Concepto</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Tipo</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Monto</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Saldo</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  <tr>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 text-center" colSpan={6}>
                      Aún no hay datos. Sube un archivo para ver los movimientos.
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
}


