"use client";

import { useState } from "react";
import { conciliacionAPI } from "@/lib/api";
import { ArrowPathIcon, DocumentArrowUpIcon, CheckCircleIcon, XCircleIcon } from "@heroicons/react/24/outline";

type UploadCardProps = {
  rfc?: string;
  empresaId?: number;
  onSuccess?: () => void;
};

type ResultadoOCR = {
  exito: boolean;
  mensaje: string;
  banco_detectado?: string | null;
  total_movimientos_extraidos?: number;
  tiempo_procesamiento_segundos?: number;
  errores?: string[];
};

export default function UploadCard({ rfc, empresaId, onSuccess }: UploadCardProps) {
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [result, setResult] = useState<ResultadoOCR | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0] ?? null;
    setFile(f);
    setResult(null);
  };

  const handleUpload = async () => {
    if (!file) return;
    setIsUploading(true);
    try {
      let r: any;
      if (typeof empresaId === 'number') {
        r = await conciliacionAPI.subirEstadoCuentaEmpresa(empresaId, file);
      } else if (rfc) {
        r = await conciliacionAPI.subirEstadoCuenta(rfc, file);
      } else {
        throw new Error('Falta empresa seleccionada');
      }
      setResult(r as ResultadoOCR);
      if (r?.exito && onSuccess) onSuccess();
    } catch (e) {
      setResult({
        exito: false,
        mensaje: "Error al procesar el archivo",
        total_movimientos_extraidos: 0,
        errores: ["Error de conexión"],
        tiempo_procesamiento_segundos: 0,
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
        {!rfc && typeof empresaId !== 'number' && (
          <div className="p-3 rounded-md bg-yellow-50 border border-yellow-200 text-sm text-yellow-800">
            Selecciona una empresa antes de subir el archivo.
          </div>
        )}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Seleccionar archivo PDF</label>
          <input
            type="file"
            accept=".pdf"
            onChange={handleFileChange}
            className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
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

        {result && (
          <div className={`p-4 rounded-lg ${result.exito ? "bg-green-50 border border-green-200" : "bg-red-50 border border-red-200"}`}>
            <div className="flex items-center">
              {result.exito ? (
                <CheckCircleIcon className="w-5 h-5 text-green-500 mr-2" />
              ) : (
                <XCircleIcon className="w-5 h-5 text-red-500 mr-2" />
              )}
              <h4 className={`font-medium ${result.exito ? "text-green-800" : "text-red-800"}`}>{result.mensaje}</h4>
            </div>
            {result.exito && (
              <div className="mt-2 text-sm text-green-700">
                <p>
                  Banco detectado: <strong>{(result.banco_detectado || "No especificado").toString().toUpperCase()}</strong>
                </p>
                <p>
                  Movimientos extraídos: <strong>{result.total_movimientos_extraidos}</strong>
                </p>
                <p>
                  Tiempo de procesamiento: <strong>{result.tiempo_procesamiento_segundos}s</strong>
                </p>
              </div>
            )}
            {result.errores && result.errores.length > 0 && (
              <div className="mt-2">
                <p className="text-sm font-medium text-red-800">Errores:</p>
                <ul className="list-disc list-inside text-sm text-red-700">
                  {result.errores.map((e, i) => (
                    <li key={i}>{e}</li>
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


