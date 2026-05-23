import { useState, useRef } from 'react';
import axios from 'axios';
import { useStego } from '../context/StegoContext';
import { 
  UploadCloud, 
  FileAudio,  
  KeyRound, 
  Settings, 
  Cpu, 
  CheckCircle2, 
  AlertTriangle, 
  XOctagon, 
  Fingerprint,
  Activity,
  ArrowRight,
  ShieldCheck,
  Unlock
} from 'lucide-react';

export default function ExtractPage() {
  const { generatedFiles } = useStego();
  const [selectedFileMode, setSelectedFileMode] = useState('upload'); // 'upload' or 'generated'
  const [selectedGeneratedFile, setSelectedGeneratedFile] = useState('');
  
  const [file, setFile] = useState(null);
  const [key, setKey] = useState('');
  const [status, setStatus] = useState('IDLE'); // IDLE, EXTRACTING, VERIFIED, INVALID KEY, CORRUPTED PAYLOAD
  const [extractedData, setExtractedData] = useState(null);
  
  const fileInputRef = useRef(null);

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setStatus('UPLOAD_SUCCESS');
      setExtractedData(null);
    }
  };

  const handleExtract = async () => {
    if ((selectedFileMode === 'upload' && !file) || (selectedFileMode === 'generated' && !selectedGeneratedFile) || !key) return;
    
    setStatus('EXTRACTING');
    
    const formData = new FormData();
    if (selectedFileMode === 'upload') {
      formData.append('stego', file);
    } else {
      formData.append('stego_filename', selectedGeneratedFile);
    }
    formData.append('password', key);

    try {
      const response = await axios.post('http://localhost:5000/api/extract', formData);

      if (response.data && response.data.message) {
        setStatus('VERIFIED');
        setExtractedData({
          text: response.data.message,
          metadata: 'Extraction completed'
        });
      }
    } catch (error) {
      console.error(error);
      const errorMsg = error.response?.data?.error || "Extraction failed";
      
      if (errorMsg.toLowerCase().includes('password') || errorMsg.toLowerCase().includes('key') || errorMsg.toLowerCase().includes('mac')) {
        setStatus('INVALID KEY');
      } else {
        setStatus('CORRUPTED PAYLOAD');
      }
      
      setExtractedData({
        text: errorMsg,
        metadata: 'Fatal Decoding Error'
      });
    }
  };

  const getStatusConfig = () => {
    switch(status) {
      case 'VERIFIED':
        return { icon: CheckCircle2, color: 'text-emerald-500', border: 'border-emerald-500/30', bg: 'bg-emerald-500/10' };
      case 'INVALID KEY':
        return { icon: AlertTriangle, color: 'text-amber-500', border: 'border-amber-500/30', bg: 'bg-amber-500/10' };
      case 'CORRUPTED PAYLOAD':
        return { icon: XOctagon, color: 'text-red-500', border: 'border-red-500/30', bg: 'bg-red-500/10' };
      default:
        return { icon: Cpu, color: 'text-theme-text-muted', border: 'border-theme-border', bg: 'bg-theme-border/10' };
    }
  };

  const StatusIcon = getStatusConfig().icon;

  return (
    <div className="space-y-8 animate-in fade-in duration-700">
      <header className="mb-10">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-theme-border bg-theme-border/20 text-xs font-semibold text-theme-accent mb-4 uppercase tracking-wider">
          <Settings size={12} /> Extraction Protocol
        </div>
        <h2 className="text-4xl font-bold tracking-tight text-theme-text-main mb-3">Signal Recovery</h2>
        <p className="text-theme-text-muted max-w-2xl leading-relaxed">
          Reconstruct embedded confidential payloads from steganographic carriers using inverse energy-adaptive mapping and cryptographic seed synchronization.
        </p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        {/* LEFT: Upload Area */}
        <div className="lg:col-span-12 xl:col-span-7 space-y-6">
          <SectionCard title="Steganographic Carrier" icon={<FileAudio className="text-theme-accent" size={18} />}>
            
            <div className="flex gap-4 mb-4 border-b border-theme-border pb-2">
              <button 
                onClick={() => setSelectedFileMode('generated')}
                className={`text-sm py-1 border-b-2 transition-colors ${selectedFileMode === 'generated' ? 'border-theme-accent text-theme-accent' : 'border-transparent text-theme-text-muted'}`}>
                Session Files
              </button>
              <button 
                onClick={() => setSelectedFileMode('upload')}
                className={`text-sm py-1 border-b-2 transition-colors ${selectedFileMode === 'upload' ? 'border-theme-accent text-theme-accent' : 'border-transparent text-theme-text-muted'}`}>
                Manual Upload
              </button>
            </div>

            {selectedFileMode === 'generated' ? (
               <div className="flex flex-col space-y-3 min-h-[140px]">
                 {generatedFiles.length === 0 ? (
                   <div className="text-sm text-theme-text-muted italic py-8 text-center flex-1">No session files generated yet.</div>
                 ) : (
                   <select 
                     value={selectedGeneratedFile}
                     onChange={(e) => setSelectedGeneratedFile(e.target.value)}
                     className="w-full bg-theme-base border border-theme-border rounded-xl p-3 text-sm text-theme-text-main focus:outline-none focus:ring-1 focus:ring-theme-accent"
                   >
                     <option value="" disabled>Select generated payload...</option>
                     {generatedFiles.map((gf, idx) => (
                       <option key={idx} value={gf.stego_filename}>
                         {gf.stego_filename} (Cover: {gf.original_name})
                       </option>
                     ))}
                   </select>
                 )}
               </div>
            ) : (
               <div 
                 className={`flex flex-col items-center justify-center w-full min-h-[180px] border border-dashed rounded-xl cursor-pointer bg-theme-base/50 transition-all group shadow-inner
                   ${file ? 'border-theme-accent' : 'border-theme-border hover:border-theme-accent hover:bg-theme-border/10'}`}
                 onDragOver={(e) => e.preventDefault()}
                 onDrop={(e) => {
                   e.preventDefault();
                   if (e.dataTransfer.files[0]) setFile(e.dataTransfer.files[0]);
                 }}
                 onClick={() => fileInputRef.current?.click()}
               >
                 <input type="file" ref={fileInputRef} className="hidden" accept=".wav" onChange={handleFileChange} />
                 
                 <div className="flex flex-col items-center justify-center pt-5 pb-6">
                   <UploadCloud size={32} strokeWidth={1.5} className={`mb-3 transition-colors ${file ? 'text-theme-accent' : 'text-theme-text-muted group-hover:text-theme-accent'}`} />
                   <p className="text-sm font-medium text-theme-text-main">
                     {file ? file.name : 'Select or drop stego WAV'}
                   </p>
                   <p className="text-xs text-theme-text-muted mt-1">16-bit PCM WAV required</p>
                 </div>
               </div>
            )}

          </SectionCard>
        </div>

        {/* RIGHT: Input Parameters */}
        <div className="lg:col-span-12 xl:col-span-5 space-y-6 flex flex-col">
          <SectionCard title="Recovery Parameters" icon={<Unlock className="text-theme-accent" size={18} />} className="flex-1">
            <div className="space-y-6">
              <div className="space-y-2">
                <label className="text-[10px] uppercase tracking-[0.2em] text-theme-text-muted font-semibold flex items-center gap-2">
                  <KeyRound className="w-3 h-3" />
                  Cryptographic Seed / Key
                </label>
                <input type="password" value={key} onChange={(e) => setKey(e.target.value)} placeholder="Enter decryption key..." className="w-full bg-theme-base border border-theme-border rounded-xl p-3 text-sm text-theme-text-main placeholder:text-theme-text-muted focus:outline-none focus:ring-1 focus:ring-theme-accent focus:border-theme-accent transition-all shadow-inner" />
              </div>
            </div>

            <div className="mt-10 flex flex-col gap-4">

              {status === 'UPLOAD_SUCCESS' && (
                <div className="p-3 bg-green-950/30 border border-green-900/50 text-green-400 text-sm rounded-lg text-center animate-in fade-in">
                  Stego carrier successfully staged for engine scan.
                </div>
              )}

              <button 
                onClick={handleExtract}
                disabled={(selectedFileMode === 'upload' && !file) || (selectedFileMode === 'generated' && !selectedGeneratedFile) || !key || status === 'EXTRACTING'}
                className="w-full py-3.5 bg-theme-text-main text-theme-base hover:opacity-90 disabled:opacity-50 rounded-xl font-medium transition-all shadow-md flex items-center justify-center gap-2 group"
              >
                {status === 'EXTRACTING' ? (
                  <span className="animate-pulse">RECONSTRUCTING SIGNAL...</span>
                ) : (
                  <span className="flex items-center gap-2">Initialize Extraction <ArrowRight size={18} className="group-hover:translate-x-1 transition-transform" /></span>
                )}
              </button>
            </div>
          </SectionCard>
        </div>
      </div>

      {/* BOTTOM: Output Section */}
      {status !== 'IDLE' && status !== 'EXTRACTING' && (
        <div className="animate-in slide-in-from-bottom-4 duration-500">
          <SectionCard title="Decoded Intelligence" icon={<Fingerprint className="text-theme-accent" size={18} />}>
            <div className="flex flex-col md:flex-row gap-8">
              <div className="flex-1 space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] uppercase tracking-[0.2em] text-theme-text-muted font-semibold">
                    Recovered Payload
                  </span>
                  
                  <div className={`flex items-center gap-2 px-3 py-1 rounded-full border ${getStatusConfig().border} ${getStatusConfig().bg}`}>
                    <StatusIcon className={`w-3.5 h-3.5 ${getStatusConfig().color}`} strokeWidth={2} />
                    <span className={`text-[10px] uppercase tracking-wider font-semibold ${getStatusConfig().color}`}>
                      {status}
                    </span>
                  </div>
                </div>

                <div className={`w-full rounded-xl p-6 font-mono text-sm leading-relaxed border transition-colors duration-500 min-h-[100px]
                  ${status === 'VERIFIED' ? 'bg-[#0f1412] dark:bg-emerald-950/20 border-emerald-900/30 text-emerald-800 dark:text-emerald-100/90' : 'bg-[#181212] dark:bg-red-950/20 border-red-900/30 text-red-800 dark:text-red-100/80'}`}>
                  {extractedData?.text || 'No data recovered.'}
                </div>
              </div>

              <div className="md:w-64 space-y-4">
                <div className="p-4 rounded-xl border border-theme-border bg-theme-base/30 space-y-4">
                  <div>
                    <span className="block text-[9px] uppercase tracking-[0.2em] text-theme-text-muted font-semibold mb-1">Status</span>
                    <div className="flex items-center gap-2">
                      <ShieldCheck className="w-3.5 h-3.5 text-theme-text-muted" />
                      <span className="font-mono text-[10px] text-theme-text-muted truncate">
                        {extractedData?.metadata}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </SectionCard>
        </div>
      )}
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
