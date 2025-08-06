'use client';

import { createContext, useContext, useState, ReactNode } from 'react';

interface ConciliacionContextType {
  rfcEmpresa: string;
  setRfcEmpresa: (rfc: string) => void;
}

const ConciliacionContext = createContext<ConciliacionContextType>({
  rfcEmpresa: '',
  setRfcEmpresa: () => {},
});

export const useConciliacionContext = () => {
  const context = useContext(ConciliacionContext);
  if (!context) {
    throw new Error('useConciliacionContext must be used within a ConciliacionProvider');
  }
  return context;
};

export const ConciliacionProvider = ({ children }: { children: ReactNode }) => {
  const [rfcEmpresa, setRfcEmpresa] = useState<string>('');

  return (
    <ConciliacionContext.Provider value={{ rfcEmpresa, setRfcEmpresa }}>
      {children}
    </ConciliacionContext.Provider>
  );
}; 