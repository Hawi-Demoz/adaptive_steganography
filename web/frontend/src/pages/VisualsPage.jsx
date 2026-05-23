import { useState, useRef } from 'react';
import { useStego } from '../context/StegoContext';
import { Activity, Image as ImageIcon, Loader2 } from 'lucide-react';

export default function VisualsPage() {
  const { generatedFiles } = useStego();
  const [selectedFileMode, setSelectedFileMode] = useState('generated');
  const [selectedGenerated, setSelectedGenerated] = useState('');
  
  const [coverFile, setCoverFile] = useState(null);
  const [stegoFile, setStegoFile] = useState(null);
  const [plotType, setPlotType] = useState('waveform');
  
  const [imageUrl, setImageUrl] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleGenerate = async () => {
    setLoading(true);
    setImageUrl(null);
    let coverName = '';
    let stegoName = '';

    if (selectedFileMode === 'generated') {
      const gf = generatedFiles.find(f => f.stego_filename === selectedGenerated);
      if (gf) {
        coverName = gf.cover_filename;
        stegoName = gf.stego_filename;
      }
    } else {
      if (!coverFile || !stegoFile) {
        setLoading(false);
        return alert("Both cover and stego files are required for visualization.");
      }
      const dataCov = new FormData();
      dataCov.append('file', coverFile);
      const resCov = await fetch('http://localhost:5000/api/upload', { method: 'POST', body: dataCov }).then(r=>r.json());
      coverName = resCov.filename;
      
      const dataSte = new FormData();
      dataSte.append('file', stegoFile);
      const resSte = await fetch('http://localhost:5000/api/upload', { method: 'POST', body: dataSte }).then(r=>r.json());
      stegoName = resSte.filename;
    }

    if (coverName && stegoName) {
      const url = `http://localhost:5000/api/visualize/${plotType}?cover=${coverName}&stego=${stegoName}&t=${Date.now()}`;
      setImageUrl(url);
    }
    setLoading(false);
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-700">
      <header className="mb-10">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-theme-border bg-theme-border/20 text-xs font-semibold text-theme-accent mb-4 uppercase tracking-wider">
          <Activity size={12} /> Signal Analysis
        </div>
        <h2 className="text-4xl font-bold tracking-tight text-theme-text-main mb-3">Acoustic Telemetry</h2>
        <p className="text-theme-text-muted max-w-2xl leading-relaxed">
          Examine the steganographic footprint with backend-generated diagnostic plots comparing cover and stego carriers.
        </p>
      </header>

      <div className="glass-panel p-6 rounded-2xl space-y-6">
        <div className="flex gap-4 border-b border-theme-border pb-2">
          <button onClick={() => setSelectedFileMode('generated')} className={`text-sm py-1 border-b-2 transition-colors ${selectedFileMode === 'generated' ? 'border-theme-accent text-theme-accent' : 'border-transparent text-theme-text-muted'}`}>Session Files</button>
          <button onClick={() => setSelectedFileMode('upload')} className={`text-sm py-1 border-b-2 transition-colors ${selectedFileMode === 'upload' ? 'border-theme-accent text-theme-accent' : 'border-transparent text-theme-text-muted'}`}>Manual Upload</button>
        </div>

        {selectedFileMode === 'generated' ? (
          <div>
            <select value={selectedGenerated} onChange={(e) => setSelectedGenerated(e.target.value)} className="w-full bg-theme-base border border-theme-border rounded-xl p-3 text-sm text-theme-text-main focus:ring-1 focus:ring-theme-accent outline-none">
                <option value="" disabled>Select a generated payload...</option>
                {generatedFiles.map((gf, i) => (
                    <option key={i} value={gf.stego_filename}>{gf.stego_filename} (Cover: {gf.original_name})</option>
                ))}
            </select>
          </div>
        ) : (
          <div className="flex gap-4">
             <div className="flex flex-col gap-1 w-1/2">
                <span className="text-xs text-theme-text-muted">Cover File</span>
                <input type="file" onChange={(e)=>setCoverFile(e.target.files[0])} className="text-sm border border-theme-border p-2 rounded" title="Cover File"/>
             </div>
             <div className="flex flex-col gap-1 w-1/2">
                <span className="text-xs text-theme-text-muted">Stego File</span>
                <input type="file" onChange={(e)=>setStegoFile(e.target.files[0])} className="text-sm border border-theme-border p-2 rounded" title="Stego File"/>
             </div>
          </div>
        )}

        <div>
            <label className="text-xs uppercase tracking-wider font-semibold text-theme-text-muted mb-2 block">Diagnostic Render Type</label>
            <div className="flex gap-3">
                {['waveform', 'spectrogram', 'snr', 'heatmap'].map(pt => (
                    <button key={pt} onClick={()=>setPlotType(pt)} className={`px-4 py-2 rounded-lg text-sm border capitalize transition-colors ${plotType === pt ? 'bg-theme-accent/20 border-theme-accent text-theme-accent' : 'border-theme-border text-theme-text-muted hover:border-theme-accent/50'}`}>
                        {pt}
                    </button>
                ))}
            </div>
        </div>

        <button onClick={handleGenerate} disabled={loading || (selectedFileMode==='generated' && !selectedGenerated) || (selectedFileMode==='upload' && (!coverFile || !stegoFile))} className="w-full py-3 bg-theme-text-main text-theme-base rounded-xl font-medium flex items-center justify-center gap-2 hover:opacity-90 disabled:opacity-50 transition-all">
          {loading ? <Loader2 className="animate-spin" size={18}/> : 'Generate Telemetry Rendition'}
        </button>
      </div>

      {(imageUrl || loading) && (
        <div className="glass-panel p-6 rounded-2xl min-h-[400px] flex items-center justify-center relative">
          {loading ? (
             <div className="text-theme-text-muted flex flex-col items-center gap-4">
               <Loader2 className="animate-spin w-8 h-8 text-theme-accent" />
               <span className="text-sm font-mono tracking-widest uppercase">Rendering Data...</span>
             </div>
          ) : imageUrl ? (
             <img src={imageUrl} alt="Visualization Result" className="max-w-full h-auto rounded-xl shadow-lg border border-theme-border" />
          ) : null}
        </div>
      )}
    </div>
  );
}
