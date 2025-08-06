"use client";

import { useState, createContext, useContext } from "react";
import Header from "./Header";
import Sidebar from "./Sidebar";

// Context para el estado del sidebar
const SidebarContext = createContext<{
  isSidebarOpen: boolean;
  setIsSidebarOpen: (open: boolean) => void;
}>({
  isSidebarOpen: true,
  setIsSidebarOpen: () => {}
});

export const useSidebar = () => useContext(SidebarContext);

interface LayoutProps {
  children: React.ReactNode;
  noPadding?: boolean;
}

export default function Layout({ children, noPadding = false }: LayoutProps) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  return (
    <SidebarContext.Provider value={{ isSidebarOpen, setIsSidebarOpen }}>
      <div className="h-screen flex overflow-hidden bg-gray-50">
        {/* Sidebar */}
        <Sidebar isOpen={isSidebarOpen} setIsOpen={setIsSidebarOpen} />

        {/* Main content area */}
        <div 
          className={`flex-1 flex flex-col overflow-hidden transition-all duration-300 ${
            isSidebarOpen ? 'md:ml-64' : 'md:ml-0'
          }`}
        >
          {/* Header */}
          <Header />

          {/* Page content */}
          <main className={`flex-1 overflow-auto ${noPadding ? '' : 'p-6'}`}>
            {children}
          </main>
        </div>
      </div>
    </SidebarContext.Provider>
  );
}
