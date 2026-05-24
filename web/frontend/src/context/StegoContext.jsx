import { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';
import { API_BASE } from '../lib/api';

const StegoContext = createContext();

export function StegoProvider({ children }) {
  const [generatedFiles, setGeneratedFiles] = useState([]);

  const refreshGeneratedFiles = async () => {
    const res = await axios.get(`${API_BASE}/api/session/files`);
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

  const [visualsMode, setVisualsMode] = useState('generated');
  const [visualsSelectedStego, setVisualsSelectedStego] = useState('');
  const [visualsCoverFile, setVisualsCoverFile] = useState(null);
  const [visualsStegoFile, setVisualsStegoFile] = useState(null);
  const [visualsActiveTab, setVisualsActiveTab] = useState('waveform');
  const [visualsCompareMode, setVisualsCompareMode] = useState(true);
  const [visualsSummary, setVisualsSummary] = useState(null);
  const [visualsImages, setVisualsImages] = useState({});
  const [visualsResolvedPair, setVisualsResolvedPair] = useState({ cover: '', stego: '' });

  return (
    <StegoContext.Provider
      value={{
        generatedFiles,
        addGeneratedFile,
        refreshGeneratedFiles,
        visualsMode,
        setVisualsMode,
        visualsSelectedStego,
        setVisualsSelectedStego,
        visualsCoverFile,
        setVisualsCoverFile,
        visualsStegoFile,
        setVisualsStegoFile,
        visualsActiveTab,
        setVisualsActiveTab,
        visualsCompareMode,
        setVisualsCompareMode,
        visualsSummary,
        setVisualsSummary,
        visualsImages,
        setVisualsImages,
        visualsResolvedPair,
        setVisualsResolvedPair,
      }}
    >
      {children}
    </StegoContext.Provider>
  );
}

export function useStego() {
  return useContext(StegoContext);
}
