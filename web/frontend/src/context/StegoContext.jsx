import { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';

const StegoContext = createContext();

export function StegoProvider({ children }) {
  const [generatedFiles, setGeneratedFiles] = useState([]);

  useEffect(() => {
    // Fetch persisted generated generated files on mount
    axios.get('http://localhost:5000/api/session/files')
      .then(res => {
        if (Array.isArray(res.data)) {
          setGeneratedFiles(res.data);
        }
      })
      .catch(err => {
        console.error("Failed to load session files", err);
      });
  }, []);

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
