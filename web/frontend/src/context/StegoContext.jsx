import { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';

const StegoContext = createContext();

export function StegoProvider({ children }) {
  const [generatedFiles, setGeneratedFiles] = useState([]);

  const refreshGeneratedFiles = async () => {
    const res = await axios.get('http://localhost:5000/api/session/files');
    if (Array.isArray(res.data)) {
      setGeneratedFiles(res.data);
    }
    return res.data;
  };

  useEffect(() => {
    refreshGeneratedFiles().catch((err) => {
      console.error("Failed to load session files", err);
    });
  }, []);

  const addGeneratedFile = (fileData) => {
    setGeneratedFiles((prev) => {
      const withoutDuplicate = prev.filter(
        (entry) => entry.stego_filename !== fileData.stego_filename
      );
      return [...withoutDuplicate, fileData];
    });
  };

  return (
    <StegoContext.Provider value={{ generatedFiles, addGeneratedFile, refreshGeneratedFiles }}>
      {children}
    </StegoContext.Provider>
  );
}

export function useStego() {
  return useContext(StegoContext);
}
