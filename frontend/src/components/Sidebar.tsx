"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BanknotesIcon,
  DocumentTextIcon,
  ChartBarIcon,
  DocumentArrowUpIcon,
} from "@heroicons/react/24/outline";

const navigation = [
  {
    name: "Conciliación Bancaria",
    href: "/conciliacion",
    icon: BanknotesIcon,
    description: "Estados de cuenta y conciliación automática",
  },
  {
    name: "Reportes",
    href: "/conciliacion/reportes",
    icon: ChartBarIcon,
    description: "Reportes y estadísticas de conciliación",
  },
  {
    name: "Documentación",
    href: "/conciliacion/docs",
    icon: DocumentTextIcon,
    description: "Guía de uso del sistema",
  },
  {
    name: "Subir Estado de Cuenta",
    href: "/subir-estado",
    icon: DocumentArrowUpIcon,
    description: "Subir estado de cuenta para conciliación",
  },
];

interface SidebarProps {
  isOpen: boolean;
  setIsOpen: (open: boolean) => void;
}

export default function Sidebar({ isOpen, setIsOpen }: SidebarProps) {
  const pathname = usePathname();
  const [isMobileOpen, setIsMobileOpen] = useState(false);

  return (
    <>
      {/* Botón flotante para abrir sidebar (solo visible cuando está cerrado) */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="fixed top-4 left-4 z-50 p-3 bg-white border border-gray-200 rounded-lg shadow-lg hover:shadow-xl transition-all duration-200 hover:bg-gray-50 md:block hidden"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="h-5 w-5 text-black"
            viewBox="0 0 16 16"
            fill="currentColor"
          >
            <path
              fillRule="evenodd"
              clipRule="evenodd"
              d="M3.25 1A2.25 2.25 0 001 3.25v9.5A2.25 2.25 0 003.25 15h9.5A2.25 2.25 0 0015 12.75v-9.5A2.25 2.25 0 0012.75 1h-9.5zM2.5 3.25a.75.75 0 01.75-.75h1.8v11h-1.8a.75.75 0 01-.75-.75v-9.5zM6.45 13.5h6.3a.75.75 0 00.75-.75v-9.5a.75.75 0 00-.75-.75h-6.3v11z"
            />
          </svg>
        </button>
      )}

      {/* Overlay para cerrar sidebar al hacer clic fuera */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 z-40 md:hidden"
          onClick={() => setIsOpen(false)}
        />
      )}

      {/* Sidebar principal */}
      <aside
        className={`
        fixed left-0 top-0 h-full w-64 bg-white border-r border-gray-200 z-50 transform transition-transform duration-300 ease-in-out
        ${isOpen ? "translate-x-0" : "-translate-x-full"}
        md:block hidden
      `}
      >
        <div className="h-full flex flex-col">
          {/* Header del Sidebar con Logo */}
          <div className="flex items-center justify-between p-4 border-b border-gray-200">
            <Link
              href="/conciliacion"
              className="flex items-center space-x-3 hover:opacity-80 transition-opacity"
            >
              <div className="w-8 h-8 relative">
                <BanknotesIcon className="w-8 h-8 text-blue-600" />
              </div>
              <div className="flex flex-col">
                <span className="text-sm font-bold text-gray-900">Sistema de</span>
                <span className="text-sm font-bold text-blue-600">Conciliación</span>
              </div>
            </Link>

            {/* Botón para cerrar sidebar */}
            <button
              onClick={() => setIsOpen(false)}
              className="p-1.5 rounded-lg text-gray-500 hover:text-gray-700 hover:bg-gray-100 transition-all duration-200"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-5 w-5 text-black"
                viewBox="0 0 16 16"
                fill="currentColor"
              >
                <path
                  fillRule="evenodd"
                  clipRule="evenodd"
                  d="M3.25 1A2.25 2.25 0 001 3.25v9.5A2.25 2.25 0 003.25 15h9.5A2.25 2.25 0 0015 12.75v-9.5A2.25 2.25 0 0012.75 1h-9.5zM2.5 3.25a.75.75 0 01.75-.75h1.8v11h-1.8a.75.75 0 01-.75-.75v-9.5zM6.45 13.5h6.3a.75.75 0 00.75-.75v-9.5a.75.75 0 00-.75-.75h-6.3v11z"
                />
              </svg>
            </button>
          </div>

          {/* Navigation */}
          <div className="flex-1 overflow-y-auto">
            <nav className="p-4 space-y-2">
              {navigation.map((item) => {
                const isActive = pathname === item.href || (item.href === "/conciliacion" && pathname.startsWith("/conciliacion"));
                return (
                  <Link
                    key={item.name}
                    href={item.href}
                    onClick={() => setIsMobileOpen(false)}
                    className={`
                      group flex items-center px-4 py-3 text-sm font-medium rounded-lg transition-all duration-200
                      ${
                        isActive
                          ? "bg-blue-100 text-blue-900 border border-blue-200"
                          : "text-gray-800 hover:bg-gray-100"
                      }
                    `}
                  >
                    <item.icon
                      className={`
                        mr-3 h-6 w-6 flex-shrink-0
                        ${
                          isActive
                            ? "text-blue-600"
                            : "text-gray-600 group-hover:text-gray-800"
                        }
                      `}
                    />
                    <div className="flex-1">
                      <div className="font-medium">{item.name}</div>
                      <div
                        className={`text-xs ${
                          isActive ? "text-blue-600" : "text-gray-500"
                        }`}
                      >
                        {item.description}
                      </div>
                    </div>
                  </Link>
                );
              })}
            </nav>
          </div>

          {/* Footer */}
          <div className="p-4 border-t border-gray-200">
            <div className="text-xs text-gray-500 text-center">
              Conciliación Bancaria v1.0
            </div>
          </div>
        </div>
      </aside>

      {/* Sidebar móvil */}
      <div className="md:hidden">
        {/* Botón de menú móvil */}
        <button
          onClick={() => setIsMobileOpen(true)}
          className="fixed top-4 left-4 z-20 p-3 rounded-lg text-gray-600 hover:text-gray-800 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-gray-500 bg-white shadow-lg border border-gray-200 transition-all duration-200"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="h-5 w-5 text-black"
            viewBox="0 0 16 16"
            fill="currentColor"
          >
            <path
              fillRule="evenodd"
              clipRule="evenodd"
              d="M3.25 1A2.25 2.25 0 001 3.25v9.5A2.25 2.25 0 003.25 15h9.5A2.25 2.25 0 0015 12.75v-9.5A2.25 2.25 0 0012.75 1h-9.5zM2.5 3.25a.75.75 0 01.75-.75h1.8v11h-1.8a.75.75 0 01-.75-.75v-9.5zM6.45 13.5h6.3a.75.75 0 00.75-.75v-9.5a.75.75 0 00-.75-.75h-6.3v11z"
            />
          </svg>
        </button>

        {/* Sidebar móvil */}
        {isMobileOpen && (
          <div className="fixed inset-0 z-50 flex">
            {/* Overlay */}
            <div
              className="fixed inset-0 bg-gray-600 bg-opacity-75"
              onClick={() => setIsMobileOpen(false)}
            />

            {/* Panel del menú */}
            <div className="relative flex-1 flex flex-col max-w-xs w-full bg-white">
              <div className="absolute top-0 right-0 -mr-12 pt-2">
                <button
                  onClick={() => setIsMobileOpen(false)}
                  className="ml-1 flex items-center justify-center h-10 w-10 rounded-full focus:outline-none focus:ring-2 focus:ring-inset focus:ring-white"
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    className="h-5 w-5 text-white"
                    viewBox="0 0 16 16"
                    fill="currentColor"
                  >
                    <path
                      fillRule="evenodd"
                      clipRule="evenodd"
                      d="M3.25 1A2.25 2.25 0 001 3.25v9.5A2.25 2.25 0 003.25 15h9.5A2.25 2.25 0 0015 12.75v-9.5A2.25 2.25 0 0012.75 1h-9.5zM2.5 3.25a.75.75 0 01.75-.75h1.8v11h-1.8a.75.75 0 01-.75-.75v-9.5zM6.45 13.5h6.3a.75.75 0 00.75-.75v-9.5a.75.75 0 00-.75-.75h-6.3v11z"
                    />
                  </svg>
                </button>
              </div>

              {/* Header móvil */}
              <div className="flex items-center p-4 border-b border-gray-200">
                <BanknotesIcon className="w-8 h-8 text-blue-600" />
                <div className="ml-3 flex flex-col">
                  <span className="text-sm font-bold text-gray-900">Sistema de</span>
                  <span className="text-sm font-bold text-blue-600">Conciliación</span>
                </div>
              </div>

              {/* Contenido del menú */}
              <div className="flex-1 h-0 pt-5 pb-4 overflow-y-auto">
                {/* Navegación móvil */}
                <nav className="px-2 space-y-1">
                  {navigation.map((item) => {
                    const isActive = pathname === item.href || (item.href === "/conciliacion" && pathname.startsWith("/conciliacion"));
                    return (
                      <Link
                        key={item.name}
                        href={item.href}
                        onClick={() => setIsMobileOpen(false)}
                        className={`
                          group flex items-center px-3 py-3 text-base font-medium rounded-lg transition-all duration-200
                          ${
                            isActive
                              ? "bg-blue-100 text-blue-900 border border-blue-200"
                              : "text-gray-800 hover:bg-gray-100"
                          }
                        `}
                      >
                        <item.icon
                          className={`
                            mr-4 h-6 w-6 flex-shrink-0
                            ${
                              isActive
                                ? "text-blue-600"
                                : "text-gray-600 group-hover:text-gray-800"
                            }
                          `}
                        />
                        <div>
                          <div className="font-medium">{item.name}</div>
                          <div
                            className={`text-sm ${
                              isActive ? "text-blue-600" : "text-gray-500"
                            }`}
                          >
                            {item.description}
                          </div>
                        </div>
                      </Link>
                    );
                  })}
                </nav>
              </div>

              {/* Footer móvil */}
              <div className="p-4 border-t border-gray-200">
                <div className="text-xs text-gray-500 text-center">
                  Conciliación Bancaria v1.0
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
