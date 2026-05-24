import { useState } from 'react';
import { useStego } from '../context/StegoContext';
import { BarChart, Loader2, Target, Cpu } from 'lucide-react';

export default function MLPage() {
  const { generatedFiles } = useStego();
  const [selectedFileMode, setSelectedFileMode] = useState('generated');
  const [selectedGenerated, setSelectedGenerated] = useState('');
  
  const [coverFile, setCoverFile] = useState(null);
  const [stegoFile, setStegoFile] = useState(null);
  
  const [mlData, setMlData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState('');

  const handleAnalyze = async () => {
    setLoading(true);
    setError(null);
    setSuccessMsg('');
    setMlData(null);
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
        return alert("Both cover and stego files are required for analysis.");
      }
      try {
        const dataCov = new FormData();
        dataCov.append('file', coverFile);
        const resCov = await fetch('http://localhost:5000/api/upload', { method: 'POST', body: dataCov }).then(r=>r.json());
        coverName = resCov.filename;
        
        const dataSte = new FormData();
        dataSte.append('file', stegoFile);
        const resSte = await fetch('http://localhost:5000/api/upload', { method: 'POST', body: dataSte }).then(r=>r.json());
        stegoName = resSte.filename;
        setSuccessMsg('Upload successful! Beginning engine scan...');
      } catch (err) {
        setError("File upload failed.");
        setLoading(false);
        return;
      }
    }

    if (coverName && stegoName) {
      try {
        const [featuresRes, mseRes] = await Promise.all([
          fetch(`http://localhost:5000/api/ml/features?audio=${stegoName}`).then(r => r.json()),
          fetch(`http://localhost:5000/api/ml/mse?cover=${coverName}&stego=${stegoName}`).then(r => r.json())
        ]);
        
        if (featuresRes.error || mseRes.error) {
           setError(featuresRes.error || mseRes.error);
        } else {
           setMlData({ features: featuresRes, mse: mseRes.mse });
           setSuccessMsg('Analysis completed successfully.');
        }
      } catch (err) {
        setError(err.message);
      }
    }
    setLoading(false);
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-700">
      <header className="mb-10">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-theme-border bg-theme-border/20 text-xs font-semibold text-theme-accent mb-4 uppercase tracking-wider">
          <BarChart size={12} /> ML Analysis
        </div>
        <h2 className="text-4xl font-bold tracking-tight text-theme-text-main mb-3">Model Inference</h2>
        <p className="text-theme-text-muted max-w-2xl leading-relaxed">
          Extract acoustic feature markers and analyze predicted metrics against the original cover signal using the backend engine.
        </p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        <div className="lg:col-span-5 space-y-6">
          <div className="glass-panel p-6 rounded-2xl space-y-6">
            <h3 className="text-sm font-semibold flex items-center gap-2 mb-5 uppercase tracking-wider text-theme-text-muted">
              <Target size={18} className="text-theme-accent" /> Analysis Target
            </h3>

            <div className="flex gap-4 border-b border-theme-border pb-2">
              <button onClick={() => setSelectedFileMode('generated')} className={`text-sm py-1 border-b-2 transition-colors ${selectedFileMode === 'generated' ? 'border-theme-accent text-theme-accent' : 'border-transparent text-theme-text-muted'}`}>Session Files</button>
              <button onClick={() => setSelectedFileMode('upload')} className={`text-sm py-1 border-b-2 transition-colors ${selectedFileMode === 'upload' ? 'border-theme-accent text-theme-accent' : 'border-transparent text-theme-text-muted'}`}>Manual Upload</button>
            </div>

            {selectedFileMode === 'generated' ? (
              <div>
                <select value={selectedGenerated} onChange={(e) => setSelectedGenerated(e.target.value)} className="w-full bg-theme-base border border-theme-border rounded-xl p-3 text-sm text-theme-text-main outline-none focus:ring-1 focus:ring-theme-accent">
                    <option value="" disabled>Select generated payload...</option>
                    {generatedFiles.map((gf, i) => (
                        <option key={i} value={gf.stego_filename}>{gf.stego_filename} (Cover: {gf.original_name})</option>
                    ))}
                </select>
              </div>
            ) : (
              <div className="space-y-4">
                 <div className="flex flex-col gap-1 w-full">
                    <span className="text-xs text-theme-text-muted">Cover File</span>
                    <input type="file" onChange={(e)=>{setCoverFile(e.target.files[0]); setError(null);}} className="text-sm border border-theme-border p-2 rounded bg-theme-base/50"/>
                 </div>
                 <div className="flex flex-col gap-1 w-full">
                    <span className="text-xs text-theme-text-muted">Stego File</span>
                    <input type="file" onChange={(e)=>{setStegoFile(e.target.files[0]); setError(null);}} className="text-sm border border-theme-border p-2 rounded bg-theme-base/50"/>
                 </div>
              </div>
            )}

            <button onClick={handleAnalyze} disabled={loading || (selectedFileMode==='generated' && !selectedGenerated) || (selectedFileMode==='upload' && (!coverFile || !stegoFile))} className="w-full py-3 mt-4 bg-theme-text-main text-theme-base rounded-xl font-medium flex items-center justify-center gap-2 hover:opacity-90 disabled:opacity-50 transition-all">
              {loading ? <Loader2 className="animate-spin" size={18}/> : 'Run Engine Scan'}
            </button>

            {error && (
              <div className="mt-4 p-3 bg-red-950/30 border border-red-900/50 text-red-400 text-sm rounded-lg text-center">
                {error}
              </div>
            )}

            {successMsg && !error && (
              <div className="mt-4 p-3 bg-green-950/30 border border-green-900/50 text-green-400 text-sm rounded-lg text-center">
                {successMsg}
              </div>
            )}
          </div>
        </div>

        <div className="lg:col-span-7">
          <div className="glass-panel p-6 rounded-2xl min-h-100">
            <h3 className="text-sm font-semibold flex items-center gap-2 mb-5 uppercase tracking-wider text-theme-text-muted">
              <Cpu size={18} className="text-theme-accent" /> Acoustic Metrics
            </h3>

            {!mlData && !loading && (
              <div className="flex flex-col items-center justify-center h-75 text-theme-text-muted">
                <BarChart size={32} className="mb-2 opacity-50" />
                <p className="text-sm">Awaiting analysis target...</p>
              </div>
            )}

            {loading && (
              <div className="flex flex-col items-center justify-center h-75 text-theme-text-muted">
                 <Loader2 className="animate-spin w-8 h-8 text-theme-accent mb-4" />
                 <span className="text-sm font-mono tracking-widest uppercase">Processing Features...</span>
              </div>
            )}

            {mlData && !loading && (
              <div className="space-y-8 fade-in animate-in">
                <div className="p-5 border border-theme-border bg-theme-base/50 rounded-xl">
                   <div className="text-xs text-theme-text-muted uppercase tracking-wider font-semibold mb-1">Mean Squared Error (MSE)</div>
                   <div className="font-mono text-3xl text-red-400">
                     {Number(mlData.mse).toExponential(4)}
                   </div>
                   <p className="text-xs text-theme-text-muted mt-2">Divergence signature between absolute cover constraints and modified stego payload.</p>
                </div>

                <div>
                   <h4 className="text-sm font-medium text-theme-text-main mb-4 border-b border-theme-border pb-2">Audio Feature Map</h4>
                   <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-h-87.5 overflow-y-auto pr-2 custom-scrollbar">
                     {Object.entries(mlData.features).map(([key, val]) => (
                        <div key={key} className="flex justify-between items-center bg-theme-base/30 p-2.5 rounded-lg border border-theme-border/50">
                           <span className="text-xs font-medium text-theme-text-muted truncate mr-2" title={key}>{key}</span>
                           <span className="font-mono text-xs text-theme-accent">{Number(val).toFixed(6)}</span>
                        </div>
                     ))}
                   </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
