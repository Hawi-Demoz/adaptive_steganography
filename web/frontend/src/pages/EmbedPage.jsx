import { useState } from 'react';
import axios from 'axios';
import { useStego } from '../context/StegoContext';
import { API_BASE } from '../lib/api';
import { UploadCloud, Settings, Shield, FileAudio, KeyRound, Type, SlidersHorizontal, ArrowRight } from 'lucide-react';

export default function EmbedPage() {
  const { refreshGeneratedFiles } = useStego();
  const [file, setFile] = useState(null);
  const [message, setMessage] = useState('');
  const [password, setPassword] = useState('');
  const [encrypt, setEncrypt] = useState(true);
  const [adaptivityLevel, setAdaptivityLevel] = useState('medium'); // 'low', 'medium', 'high'
  const [useCustomName, setUseCustomName] = useState(false);
  const [outputName, setOutputName] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [successMsg, setSuccessMsg] = useState('');

  const buildSuggestedName = (sourceName) => {
    const baseName = sourceName.replace(/\.[^.]+$/, '');
    return `stego_${baseName}.wav`;
  };

  const handleFileChange = (e) => {
    if (e.target.files[0]) {
      setFile(e.target.files[0]);
      if (useCustomName) {
        setOutputName(buildSuggestedName(e.target.files[0].name));
      }
    }
  };

  const handleEmbed = async () => {
    if (!file || !message || !password) return alert("Missing fields criteria.");
    
    setIsLoading(true);
    setSuccessMsg('');
    const formData = new FormData();
    formData.append('cover', file);
    formData.append('message', message);
    formData.append('password', password);
    formData.append('encrypt', encrypt ? 'true' : 'false');
    if (useCustomName && outputName.trim()) {
      formData.append('stego_filename', outputName.trim());
    }

    const levelMap = { low: 0, medium: 20, high: 40 };
    const energyPercentileVal = levelMap[adaptivityLevel];
    formData.append('energy_percentile', String(energyPercentileVal));
    formData.append('robust_repeat', 1);

    try {
      const response = await axios.post(`${API_BASE}/api/embed`, formData);
      
      const stegoData = response.data;
      await refreshGeneratedFiles();

      // Optionally auto-download immediately (or allow them to grab it from extracting later)
      const downloadUrl = `${API_BASE}/api/download/${stegoData.stego_filename}`;
      const link = document.createElement('a');
      link.href = downloadUrl;
      const downloadName = stegoData.stego_filename || outputName.trim() || `stego_${file.name}`;
      link.setAttribute('download', downloadName.endsWith('.wav') ? downloadName : `${downloadName}.wav`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      setSuccessMsg("Payload successfully embedded and downloaded! It is now available in session for extraction and visualization.");
    } catch (error) {
      console.error(error);
      const errMsg = error.response?.data?.error || error.message;
      alert(`Error generating payload carrier: ${errMsg}`);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-700">
      <header className="mb-10">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-theme-border bg-theme-border/20 text-xs font-semibold text-theme-accent mb-4 uppercase tracking-wider">
          <Settings size={12} /> Adaptive Steganography
        </div>
        <h2 className="text-4xl font-bold tracking-tight text-theme-text-main mb-3">Payload Ingestion</h2>
        <p className="text-theme-text-muted max-w-2xl leading-relaxed">
          Embed confidential telemetry and secure messaging into high-energy acoustic carriers using deterministic keyed placement.
        </p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left Column: Data Input */}
        <div className="lg:col-span-7 space-y-6">
          <SectionCard title="Acoustic Carrier" icon={<FileAudio className="text-theme-accent" size={18} />}>
            <label 
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault();
                if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                  const droppedFile = e.dataTransfer.files[0];
                  setFile(droppedFile);
                  if (useCustomName) {
                    setOutputName(buildSuggestedName(droppedFile.name));
                  }
                }
              }}
              className="flex flex-col items-center justify-center w-full h-36 border border-dashed border-theme-border hover:border-theme-accent rounded-xl cursor-pointer bg-theme-base/50 transition-all hover:bg-theme-border/10 group shadow-inner"
            >
              <div className="flex flex-col items-center justify-center pt-5 pb-6">
                <UploadCloud size={32} strokeWidth={1.5} className="text-theme-text-muted mb-3 group-hover:text-theme-accent transition-colors" />
                <p className="text-sm font-medium text-theme-text-main">
                  {file ? <span className="text-theme-text-main">{file.name}</span> : 'Select or drop WAV container'}
                </p>
                <p className="text-xs text-theme-text-muted mt-1">16-bit PCM WAV required</p>
              </div>
              <input type="file" className="hidden" accept=".wav" onChange={handleFileChange} />
            </label>
          </SectionCard>

          <SectionCard title="Secure Payload" icon={<Shield className="text-theme-accent" size={18} />}>
            <div className="space-y-4">
              <div className="relative">
                <Type className="absolute left-3 top-3.5 text-theme-text-muted" size={16} />
                <textarea 
                  className="w-full bg-theme-base border border-theme-border rounded-xl pl-10 p-3 text-sm text-theme-text-main placeholder:text-theme-text-muted focus:outline-none focus:ring-1 focus:ring-theme-accent focus:border-theme-accent min-h-30 transition-all resize-none shadow-inner"
                  placeholder="Enter ciphertext or plaintext payload..."
                  value={message} onChange={(e) => setMessage(e.target.value)}
                />
              </div>
              
              <div className="relative">
                <KeyRound className="absolute left-3 top-1/2 -translate-y-1/2 text-theme-text-muted" size={16} />
                <input 
                  type="password" 
                  className="w-full bg-theme-base border border-theme-border rounded-xl pl-10 p-3 text-sm text-theme-text-main placeholder:text-theme-text-muted focus:outline-none focus:ring-1 focus:ring-theme-accent focus:border-theme-accent transition-all shadow-inner"
                  placeholder="Cryptographic Seed / Key"
                  value={password} onChange={(e) => setPassword(e.target.value)}
                />
              </div>

              <div className="relative">
                <FileAudio className="absolute left-3 top-1/2 -translate-y-1/2 text-theme-text-muted" size={16} />
                <input 
                  type="text" 
                  className="w-full bg-theme-base border border-theme-border rounded-xl pl-10 p-3 text-sm text-theme-text-main placeholder:text-theme-text-muted focus:outline-none focus:ring-1 focus:ring-theme-accent focus:border-theme-accent transition-all shadow-inner"
                  placeholder="Custom filename for the saved stego file"
                  value={outputName} onChange={(e) => setOutputName(e.target.value)}
                  disabled={!useCustomName}
                />
              </div>
            </div>
          </SectionCard>
        </div>

        {/* Right Column: Parameters and Actions */}
        <div className="lg:col-span-5 space-y-6 flex flex-col">
          <SectionCard title="Embedding Morphology" icon={<SlidersHorizontal className="text-theme-accent" size={18} />} className="flex-1">
            <div className="space-y-6">
              
              {/* Toggle Switch */}
              <div className="flex items-center justify-between p-3 rounded-lg border border-theme-border bg-theme-base/30">
                <div className="flex flex-col">
                  <span className="text-sm font-medium text-theme-text-main">AES-256 Encryption</span>
                  <span className="text-xs text-theme-text-muted">Encrypt payload before injection</span>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" className="sr-only peer" checked={encrypt} onChange={(e) => setEncrypt(e.target.checked)} />
                  <div className="w-9 h-5 bg-theme-border peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-0.5 after:left-0.5 after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-theme-accent"></div>
                </label>
              </div>

              <div className="space-y-3 p-3 rounded-lg border border-theme-border bg-theme-base/30">
                <div className="flex flex-col">
                  <span className="text-sm font-medium text-theme-text-main">Stego File Name</span>
                  <span className="text-xs text-theme-text-muted">Choose automatic naming or give the saved file a custom name.</span>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => {
                      setUseCustomName(false);
                      setOutputName('');
                    }}
                    className={`py-2 px-3 rounded-lg text-xs font-semibold uppercase tracking-wider transition-all duration-200 border ${!useCustomName ? 'bg-theme-accent text-theme-base border-theme-accent' : 'text-theme-text-muted border-theme-border hover:text-theme-text-main hover:bg-theme-border/20'}`}
                  >
                    Auto-name
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setUseCustomName(true);
                      if (file && !outputName.trim()) {
                        setOutputName(buildSuggestedName(file.name));
                      }
                    }}
                    className={`py-2 px-3 rounded-lg text-xs font-semibold uppercase tracking-wider transition-all duration-200 border ${useCustomName ? 'bg-theme-accent text-theme-base border-theme-accent' : 'text-theme-text-muted border-theme-border hover:text-theme-text-main hover:bg-theme-border/20'}`}
                  >
                    Rename file
                  </button>
                </div>
              </div>

              {/* Segmented Button Selection for Energy Adaptivity */}
              <div className="space-y-4">
                <div className="flex flex-col">
                  <span className="text-sm font-medium text-theme-text-main">Energy Adaptivity Level</span>
                  <span className="text-xs text-theme-text-muted">Determines RMS energy threshold for secure embedding</span>
                </div>
                
                <div className="grid grid-cols-3 gap-1 bg-theme-base/30 p-1 rounded-xl border border-theme-border shadow-inner">
                  {['low', 'medium', 'high'].map((level) => (
                    <button
                      key={level}
                      type="button"
                      onClick={() => setAdaptivityLevel(level)}
                      className={`py-2 px-3 rounded-lg text-xs font-semibold uppercase tracking-wider transition-all duration-200 cursor-pointer text-center
                        ${adaptivityLevel === level 
                          ? 'bg-theme-accent text-theme-base shadow-sm font-bold scale-[1.01]' 
                          : 'text-theme-text-muted hover:text-theme-text-main hover:bg-theme-border/20'}`}
                    >
                      {level}
                    </button>
                  ))}
                </div>

                <div className="flex justify-between text-[10px] text-theme-text-muted font-mono bg-theme-border/10 p-3 rounded-lg border border-theme-border/40">
                  <span className="flex flex-col items-start gap-0.5">
                    <span className="font-semibold text-theme-text-main">Capacity</span>
                    <span>{adaptivityLevel === 'low' ? 'Maximum (100%)' : adaptivityLevel === 'medium' ? 'Optimal (80%)' : 'Conservative (60%)'}</span>
                  </span>
                  <span className="flex flex-col items-end gap-0.5">
                    <span className="font-semibold text-theme-text-main">Imperceptibility</span>
                    <span>{adaptivityLevel === 'low' ? 'Standard' : adaptivityLevel === 'medium' ? 'Strong' : 'Excellent (Acoustic Masking)'}</span>
                  </span>
                </div>
              </div>
            </div>
            
            {successMsg && (
              <div className="mt-4 p-3 bg-green-950/30 border border-green-900/50 text-green-400 text-sm rounded-lg text-center animate-in fade-in">
                {successMsg}
              </div>
            )}

            <div className="mt-8">
              <button 
                onClick={handleEmbed}
                disabled={isLoading}
                className="w-full py-3.5 bg-theme-text-main text-theme-base hover:opacity-90 disabled:opacity-50 rounded-xl font-medium transition-all shadow-md flex items-center justify-center gap-2 group"
              >
                {isLoading ? (
                  <span className="animate-pulse flex items-center gap-2">Initiating Sequence...</span>
                ) : (
                  <>
                    Initialize Embedding <ArrowRight size={18} className="group-hover:translate-x-1 transition-transform" />
                  </>
                )}
              </button>
            </div>
          </SectionCard>
        </div>
      </div>
    </div>
  );
}

function SectionCard({ title, icon, children, className = '' }) {
  return (
    <div className={`glass-panel rounded-2xl p-6 ${className}`}>
      <h3 className="text-sm font-semibold flex items-center gap-2 mb-5 uppercase tracking-wider text-theme-text-muted">
        {icon} {title}
      </h3>
      {children}
    </div>
  );
}
