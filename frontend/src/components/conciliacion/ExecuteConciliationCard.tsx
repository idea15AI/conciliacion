"use client";

import { useState } from "react";
import { conciliacionAPI } from "@/lib/api";
import { PlayIcon, ArrowPathIcon } from "@heroicons/react/24/outline";
import type { ConciliacionRequest } from "@/types";

type Props = { rfc: string; onSuccess?: () => void };

export default function ExecuteConciliationCard({ rfc, onSuccess }: Props) {
  const [isExecuting, setIsExecuting] = useState(false);
  const [mesAnio, setMesAnio] = useState({ mes: new Date().getMonth() + 1, anio: new Date().getFullYear() });
  const [tolerancias, setTolerancias] = useState({ monto: 1.0, dias: 3 });

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
        forzar_reproceso: forzarReproceso,
      };
      await conciliacionAPI.ejecutarConciliacion(request);
      onSuccess?.();
    } catch (error: any) {
      if (error?.response?.status === 409) {
        const confirmed = window.confirm(
          `Ya existe una conciliación para ${mesAnio.mes}/${mesAnio.anio}.\n\n¿Deseas reprocesar y sobrescribir los resultados existentes?\n\nEsto aplicará las correcciones del OCR a los movimientos.`
        );
        if (confirmed) await executeInternal(true);
        return;
      }
      alert("Error al ejecutar conciliación. Revisa la consola para más detalles.");
      console.error(error);
    } finally {
      setIsExecuting(false);
    }
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
              onChange={(e) => setMesAnio({ ...mesAnio, mes: parseInt(e.target.value) })}
              className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
            >
              {Array.from({ length: 12 }, (_, i) => (
                <option key={i + 1} value={i + 1}>
                  {new Date(2024, i, 1).toLocaleDateString("es-ES", { month: "long" })}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Año</label>
            <select
              value={mesAnio.anio}
              onChange={(e) => setMesAnio({ ...mesAnio, anio: parseInt(e.target.value) })}
              className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
            >
              {Array.from({ length: 5 }, (_, i) => {
                const year = new Date().getFullYear() - i;
                return (
                  <option key={year} value={year}>
                    {year}
                  </option>
                );
              })}
            </select>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Tolerancia Monto ($)</label>
            <input
              type="number"
              step="0.01"
              value={tolerancias.monto}
              onChange={(e) => setTolerancias({ ...tolerancias, monto: parseFloat(e.target.value) })}
              className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Tolerancia Días</label>
            <input
              type="number"
              value={tolerancias.dias}
              onChange={(e) => setTolerancias({ ...tolerancias, dias: parseInt(e.target.value) })}
              className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
            />
          </div>
        </div>
        <button
          onClick={() => executeInternal(false)}
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


