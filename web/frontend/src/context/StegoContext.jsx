import { createContext, useContext, useState } from 'react';

const StegoContext = createContext();

export function StegoProvider({ children }) {
  const [generatedFiles, setGeneratedFiles] = useState([]);

  const addGeneratedFile = (fileData) => {
    setGeneratedFiles((prev) => [...prev, fileData]);
  };

  return (
    <StegoContext.Provider value={{ generatedFiles, addGeneratedFile }}>
      {children}
    </StegoContext.Provider>
  );
}

export function useStego() {
  return useContext(StegoContext);
}
