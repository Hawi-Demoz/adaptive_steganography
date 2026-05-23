import { useState } from 'react';
import axios from 'axios';
import { useStego } from '../context/StegoContext';
import { UploadCloud, Settings, Shield, FileAudio, KeyRound, Type, SlidersHorizontal, ArrowRight } from 'lucide-react';

export default function EmbedPage() {
  const { addGeneratedFile } = useStego();
  const [file, setFile] = useState(null);
  const [message, setMessage] = useState('');
  const [password, setPassword] = useState('');
  const [encrypt, setEncrypt] = useState(true);
  const [energyPercentile, setEnergyPercentile] = useState(20);
  const [robustRepeat, setRobustRepeat] = useState(1);
  const [isLoading, setIsLoading] = useState(false);

  const handleFileChange = (e) => {
    if (e.target.files[0]) setFile(e.target.files[0]);
  };

  const handleEmbed = async () => {
    if (!file || !message || !password) return alert("Missing fields criteria.");
    
    setIsLoading(true);
    const formData = new FormData();
    formData.append('cover', file);
    formData.append('message', message);
    formData.append('password', password);
    formData.append('encrypt', encrypt);
    formData.append('energy_percentile', energyPercentile);
    formData.append('robust_repeat', robustRepeat);

    try {
      const response = await axios.post('http://localhost:5000/api/embed', formData);
      
      const stegoData = response.data;
      
      // Save globally
      addGeneratedFile({
        ...stegoData, // stego_filename, cover_filename, original_name, timestamp
        type: 'generated',
        metrics: { energyPercentile, robustRepeat, encrypt }
      });

      // Optionally auto-download immediately (or allow them to grab it from extracting later)
      const downloadUrl = `http://localhost:5000/api/download/${stegoData.stego_filename}`;
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.setAttribute('download', `stego_${file.name}`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
    } catch (error) {
      console.error(error);
      alert("Error generating payload carrier.");
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
            <label className="flex flex-col items-center justify-center w-full h-36 border border-dashed border-theme-border hover:border-theme-accent rounded-xl cursor-pointer bg-theme-base/50 transition-all hover:bg-theme-border/10 group shadow-inner">
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
                  className="w-full bg-theme-base border border-theme-border rounded-xl pl-10 p-3 text-sm text-theme-text-main placeholder:text-theme-text-muted focus:outline-none focus:ring-1 focus:ring-theme-accent focus:border-theme-accent min-h-[120px] transition-all resize-none shadow-inner"
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
                  <div className="w-9 h-5 bg-theme-border peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-theme-accent"></div>
                </label>
              </div>

                <div className="flex items-center justify-between p-3 rounded-lg border border-theme-border bg-theme-base/30">
                <div className="flex flex-col">
                  <span className="text-sm font-medium text-theme-text-main">Robust Repeat Factor</span>
                  <span className="text-xs text-theme-text-muted">Redundant encoding depth</span>
                </div>
                <div className="flex items-center gap-2">
                  <input 
                    type="number" 
                    min="1" 
                    max="10" 
                    value={robustRepeat} 
                    onChange={(e) => setRobustRepeat(parseInt(e.target.value) || 1)}
                    className="w-16 bg-theme-base border border-theme-border rounded-lg p-1.5 text-center text-sm text-theme-text-main focus:outline-none focus:ring-1 focus:ring-theme-accent focus:border-theme-accent transition-all shadow-inner"
                  />
                </div>
              </div>

              {/* Slider */}
              <div className="space-y-3">
                <div className="flex justify-between items-end">
                  <div className="flex flex-col">
                    <label className="text-sm font-medium text-theme-text-main">Acoustic Masking Threshold</label>
                    <span className="text-xs text-theme-text-muted">RMS Energy Percentile</span>
                  </div>
                  <span className="text-sm font-mono text-theme-accent bg-theme-border/30 px-2 py-0.5 rounded">{energyPercentile}%</span>
                </div>
                
                <input 
                  type="range" min="0" max="100" 
                  value={energyPercentile} onChange={(e)=>setEnergyPercentile(e.target.value)}
                  className="w-full h-1.5 bg-theme-border rounded-lg appearance-none cursor-pointer accent-theme-accent"
                />
                
                <div className="flex justify-between text-[10px] uppercase tracking-wider text-theme-text-muted font-semibold">
                  <span>Capacity</span>
                  <span>Imperceptibility</span>
                </div>
              </div>
            </div>
            
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
