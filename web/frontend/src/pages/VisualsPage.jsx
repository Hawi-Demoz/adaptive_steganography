import { useState, useEffect, useMemo, useCallback } from 'react';
import { useLocation } from 'react-router-dom';
import axios from 'axios';
import { useStego } from '../context/StegoContext';
import {
  Activity,
  BarChart3,
  Download,
  Expand,
  Gauge,
  ImageIcon,
  Layers,
  Loader2,
  Maximize2,
  Radio,
  Shield,
  Sparkles,
  UploadCloud,
  Waves,
  X,
  Zap,
} from 'lucide-react';

const API = 'http://localhost:5000';

const VIZ_CATALOG = [
  { id: 'waveform', label: 'Waveform', icon: Waves, endpoint: '/api/visualize/waveform', desc: 'Cover vs stego overlay with LSB hotspot zoom' },
  { id: 'spectrogram', label: 'Spectrogram', icon: Radio, endpoint: '/api/visualize/spectrogram', desc: 'Side-by-side frequency analysis with difference layer' },
  { id: 'heatmap', label: 'Heatmap', icon: Layers, endpoint: '/api/visualize/heatmap', desc: 'Temporal LSB modification intensity map' },
  { id: 'energy', label: 'Energy', icon: Zap, endpoint: '/api/visualize/energy-profile', desc: 'RMS profile and adaptivity threshold regions' },
  { id: 'density', label: 'Density', icon: Sparkles, endpoint: '/api/visualize/embedding-density', desc: 'Payload concentration across high-energy frames' },
  { id: 'lsb', label: 'LSB Analysis', icon: BarChart3, endpoint: '/api/visualize/lsb-analysis', desc: 'Bit-flip directionality and forensic map' },
  { id: 'snr', label: 'SNR', icon: Gauge, endpoint: '/api/visualize/snr', desc: 'Signal-to-noise ratio and distortion residual' },
];

const METRIC_TOOLTIPS = {
  snr_db: 'Signal-to-noise ratio between cover and stego (higher = more imperceptible).',
  lsb_ber: 'Bit error rate on least-significant bits between cover and stego waveforms.',
  payload_ber: 'Recovered payload bit error rate from embed/extract verification (when available).',
  capacity_usage: 'Fraction of audio samples with LSB modifications.',
  energy_localization: 'Share of LSB changes occurring in high-energy preferred frames.',
};

function formatPct(v) {
  if (v == null || Number.isNaN(v)) return '—';
  return `${(v * 100).toFixed(3)}%`;
}

function Skeleton({ className = '' }) {
  return <div className={`animate-pulse rounded-xl bg-theme-border/40 ${className}`} />;
}

export default function VisualsPage() {
  const location = useLocation();
  const {
    generatedFiles,
    refreshGeneratedFiles,
    visualsMode: mode,
    setVisualsMode: setMode,
    visualsSelectedStego: selectedStego,
    setVisualsSelectedStego: setSelectedStego,
    visualsCoverFile: coverFile,
    setVisualsCoverFile: setCoverFile,
    visualsStegoFile: stegoFile,
    setVisualsStegoFile: setStegoFile,
    visualsActiveTab: activeTab,
    setVisualsActiveTab: setActiveTab,
    visualsCompareMode: compareMode,
    setVisualsCompareMode: setCompareMode,
    visualsSummary: summary,
    setVisualsSummary: setSummary,
    visualsImages: images,
    setVisualsImages: setImages,
    visualsResolvedPair: resolvedPair,
    setVisualsResolvedPair: setResolvedPair,
  } = useStego();

  const [loadingSummary, setLoadingSummary] = useState(false);
  const [loadingViz, setLoadingViz] = useState({});
  const [error, setError] = useState(null);
  const [fullscreen, setFullscreen] = useState(null);

  // Handle auto-analysis from location state (e.g., from Vault Dashboard)
  useEffect(() => {
    if (location.state?.selectedStego && generatedFiles.length > 0) {
      const stateStego = location.state.selectedStego;
      if (stateStego !== selectedStego || !summary) {
        setMode('generated');
        setSelectedStego(stateStego);

        const runAutoAnalysis = async () => {
          const files = await refreshGeneratedFiles();
          const entry = Array.isArray(files) ? files.find((f) => f.stego_filename === stateStego) : generatedFiles.find((f) => f.stego_filename === stateStego);
          if (!entry) return;

          setError(null);
          setLoadingSummary(true);
          setSummary(null);
          setImages((prev) => {
            Object.values(prev).forEach((url) => {
              try { URL.revokeObjectURL(url); } catch (e) {}
            });
            return {};
          });

          const pair = {
            cover: entry.cover_filename,
            stego: entry.stego_filename,
            energy: entry.energy_percentile,
          };
          setResolvedPair({ cover: pair.cover, stego: pair.stego, energy: pair.energy ?? 0 });

          try {
            const qs = new URLSearchParams({
              cover: pair.cover,
              stego: pair.stego,
              t: Date.now().toString(),
              energy_percentile: String(pair.energy ?? 0),
            }).toString();
            const summaryRes = await axios.get(`${API}/api/analytics/summary?${qs}`);
            setSummary(summaryRes.data);

            // Fetch visualization for the active tab
            setLoadingViz((prev) => ({ ...prev, [activeTab]: true }));
            const viz = VIZ_CATALOG.find((v) => v.id === activeTab);
            if (viz) {
              const url = `${API}${viz.endpoint}?${qs}`;
              const res = await axios.get(url, { responseType: 'blob' });
              const blobUrl = URL.createObjectURL(res.data);
              setImages((prev) => {
                if (prev[activeTab]) URL.revokeObjectURL(prev[activeTab]);
                return { ...prev, [activeTab]: blobUrl };
              });
            }
          } catch (err) {
            setError(err.response?.data?.error || err.message || 'Analysis failed');
          } finally {
            setLoadingSummary(false);
            setLoadingViz((prev) => ({ ...prev, [activeTab]: false }));
          }
        };

        runAutoAnalysis();
      }
    }
  }, [location.state, generatedFiles, selectedStego, summary, activeTab]);

  const sessionEntry = useMemo(
    () => generatedFiles.find((f) => f.stego_filename === selectedStego),
    [generatedFiles, selectedStego]
  );

  useEffect(() => {
    if (mode !== 'generated' || generatedFiles.length === 0) return;
    const exists = generatedFiles.some((f) => f.stego_filename === selectedStego);
    if (!exists) setSelectedStego(generatedFiles[generatedFiles.length - 1].stego_filename);
  }, [generatedFiles, mode, selectedStego]);

  const resolvePair = useCallback(async () => {
    if (mode === 'generated') {
      if (!sessionEntry) return null;
      return {
        cover: sessionEntry.cover_filename,
        stego: sessionEntry.stego_filename,
        energy: sessionEntry.energy_percentile,
      };
    }
    if (!coverFile || !stegoFile) return null;
    const [covRes, stegRes] = await Promise.all([
      axios.post(`${API}/api/upload`, (() => { const fd = new FormData(); fd.append('file', coverFile); return fd; })()),
      axios.post(`${API}/api/upload`, (() => { const fd = new FormData(); fd.append('file', stegoFile); return fd; })()),
    ]);
    return { cover: covRes.data.filename, stego: stegRes.data.filename, energy: 0 };
  }, [mode, sessionEntry, coverFile, stegoFile]);

  const buildQuery = (pair) => {
    const params = new URLSearchParams({ cover: pair.cover, stego: pair.stego, t: Date.now().toString() });
    if (pair.energy != null) params.set('energy_percentile', String(pair.energy));
    return params.toString();
  };

  const runAnalysis = async () => {
    setError(null);
    setLoadingSummary(true);
    setSummary(null);
    setImages((prev) => {
      Object.values(prev).forEach((url) => {
        try { URL.revokeObjectURL(url); } catch (e) {}
      });
      return {};
    });
    try {
      await refreshGeneratedFiles();
      const pair = await resolvePair();
      if (!pair) {
        setError('Select or upload cover and stego files.');
        return;
      }
      setResolvedPair({ cover: pair.cover, stego: pair.stego, energy: pair.energy ?? 0 });
      const qs = buildQuery(pair);
      const summaryRes = await axios.get(`${API}/api/analytics/summary?${qs}`);
      setSummary(summaryRes.data);
      await loadVisualization('waveform', pair);
    } catch (err) {
      setError(err.response?.data?.error || err.message || 'Analysis failed');
    } finally {
      setLoadingSummary(false);
    }
  };

  const loadVisualization = async (vizId, pairOverride = null) => {
    const pair = pairOverride || resolvedPair;
    if (!pair.cover || !pair.stego) return;
    const viz = VIZ_CATALOG.find((v) => v.id === vizId);
    if (!viz) return;

    setLoadingViz((prev) => ({ ...prev, [vizId]: true }));
    try {
      const energy = pairOverride?.energy ?? sessionEntry?.energy_percentile ?? summary?.energy_percentile ?? resolvedPair.energy ?? 0;
      const params = new URLSearchParams({
        cover: pair.cover,
        stego: pair.stego,
        t: Date.now().toString(),
        energy_percentile: String(energy),
      });
      const url = `${API}${viz.endpoint}?${params}`;
      const res = await axios.get(url, { responseType: 'blob' });
      const blobUrl = URL.createObjectURL(res.data);
      setImages((prev) => {
        if (prev[vizId]) URL.revokeObjectURL(prev[vizId]);
        return { ...prev, [vizId]: blobUrl };
      });
    } catch (err) {
      setError(err.response?.data?.error || `Failed to load ${viz.label}`);
    } finally {
      setLoadingViz((prev) => ({ ...prev, [vizId]: false }));
    }
  };

  useEffect(() => {
    if (!resolvedPair.cover || !activeTab) return;
    if (!images[activeTab] && !loadingViz[activeTab]) {
      loadVisualization(activeTab);
    }
  }, [activeTab, resolvedPair]);

  const handleTabChange = (id) => {
    setActiveTab(id);
    if (!images[id]) loadVisualization(id);
  };

  const downloadImage = (vizId) => {
    const url = images[vizId];
    if (!url) return;
    const link = document.createElement('a');
    link.href = url;
    link.download = `${vizId}_${resolvedPair.stego || 'analysis'}.png`;
    link.click();
  };

  const activeViz = VIZ_CATALOG.find((v) => v.id === activeTab);

  return (
    <div className="space-y-8 animate-in fade-in duration-700 pb-16">
      {/* Hero */}
      <header className="relative overflow-hidden rounded-3xl border border-theme-border analytics-hero p-8 md:p-10">
        <div className="absolute inset-0 analytics-grid opacity-30 pointer-events-none" />
        <div className="relative z-10 flex flex-col lg:flex-row lg:items-end lg:justify-between gap-6">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-theme-border bg-theme-border/20 text-xs font-semibold text-theme-accent mb-4 uppercase tracking-widest">
              <Activity size={12} /> Forensic Analytics
            </div>
            <h2 className="text-4xl md:text-5xl font-bold tracking-tight text-theme-text-main mb-3">
              Signal Intelligence Dashboard
            </h2>
            <p className="text-theme-text-muted max-w-2xl leading-relaxed">
              Real backend-generated forensic plots and metrics from your cover/stego audio pairs.
              No simulated data — every visualization is computed from actual waveforms.
            </p>
          </div>
          {summary && (
            <div className="flex flex-wrap gap-2">
              <Badge icon={<Shield size={14} />} label={summary.security_status} accent />
              <Badge icon={<Gauge size={14} />} label={`SNR ${summary.snr_db.toFixed(1)} dB`} />
            </div>
          )}
        </div>
      </header>

      {/* Source selector */}
      <section className="glass-panel rounded-2xl p-6 space-y-5 analytics-card">
        <div className="flex gap-4 border-b border-theme-border pb-2">
          <TabButton active={mode === 'generated'} onClick={() => setMode('generated')}>Session Files</TabButton>
          <TabButton active={mode === 'upload'} onClick={() => setMode('upload')}>Manual Upload</TabButton>
        </div>

        {mode === 'generated' ? (
          <select
            value={selectedStego}
            onChange={(e) => setSelectedStego(e.target.value)}
            className="w-full bg-theme-base border border-theme-border rounded-xl p-3 text-sm focus:ring-1 focus:ring-theme-accent/50 outline-none"
          >
            <option value="" disabled>Select stego payload...</option>
            {generatedFiles.map((gf) => (
              <option key={gf.stego_filename} value={gf.stego_filename}>
                {gf.stego_filename} — {gf.original_name}
              </option>
            ))}
          </select>
        ) : (
          <div className="grid md:grid-cols-2 gap-4">
            <UploadBox label="Cover WAV" file={coverFile} onChange={setCoverFile} />
            <UploadBox label="Stego WAV" file={stegoFile} onChange={setStegoFile} />
          </div>
        )}

        <div className="flex flex-wrap items-center gap-4">
          <label className="flex items-center gap-2 text-sm text-theme-text-muted cursor-pointer">
            <input type="checkbox" checked={compareMode} onChange={(e) => setCompareMode(e.target.checked)} className="rounded border-theme-border text-theme-accent focus:ring-theme-accent" />
            Compare Cover vs Stego
          </label>
          <button
            onClick={runAnalysis}
            disabled={loadingSummary || (mode === 'generated' ? !selectedStego : !coverFile || !stegoFile)}
            className="ml-auto px-6 py-3 rounded-xl bg-theme-accent text-theme-base font-medium shadow-lg shadow-theme-accent/20 hover:opacity-90 disabled:opacity-40 flex items-center gap-2 transition-all"
          >
            {loadingSummary ? <Loader2 className="animate-spin" size={18} /> : <Sparkles size={18} />}
            Run Forensic Analysis
          </button>
        </div>
        {error && <p className="text-red-400 text-sm">{error}</p>}
      </section>

      {/* Hero metrics */}
      {(loadingSummary || summary) && (
        <section className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-4">
          {loadingSummary
            ? Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-28" />)
            : summary && (
              <>
                <MetricCard title="SNR" value={`${summary.snr_db.toFixed(2)} dB`} tooltip={METRIC_TOOLTIPS.snr_db} />
                <MetricCard title="LSB BER" value={summary.lsb_ber.toExponential(2)} tooltip={METRIC_TOOLTIPS.lsb_ber} />
                <MetricCard title="Payload BER" value={summary.payload_ber != null ? summary.payload_ber.toExponential(2) : 'N/A'} tooltip={METRIC_TOOLTIPS.payload_ber} />
                <MetricCard title="Capacity" value={formatPct(summary.capacity_usage)} tooltip={METRIC_TOOLTIPS.capacity_usage} />
                <MetricCard title="Energy Loc." value={formatPct(summary.energy_localization)} tooltip={METRIC_TOOLTIPS.energy_localization} />
              </>
            )}
        </section>
      )}

      {/* Session info bar */}
      {summary && (
        <section className="glass-panel rounded-2xl p-5 grid md:grid-cols-4 gap-4 text-sm analytics-card">
          <InfoCell label="Stego File" value={summary.stego_filename} />
          <InfoCell label="Cover File" value={summary.cover_filename} />
          <InfoCell label="Payload Footprint" value={`~${summary.payload_bytes_estimate} bytes (${summary.embedding_bits.toLocaleString()} LSB bits)`} />
          <InfoCell label="Adaptivity" value={`${summary.energy_percentile}% | Encrypt: ${summary.encrypt ? 'Yes' : 'No'}`} />
        </section>
      )}

      {/* Visualization tabs + gallery */}
      {summary && (
        <section className="space-y-6">
          <div className="flex flex-wrap gap-2">
            {VIZ_CATALOG.map((viz) => {
              const Icon = viz.icon;
              const active = activeTab === viz.id;
              return (
                <button
                  key={viz.id}
                  onClick={() => handleTabChange(viz.id)}
                  title={viz.desc}
                  className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm border transition-all duration-300
                    ${active ? 'border-theme-accent/50 bg-theme-accent/10 text-theme-accent shadow-[0_0_20px_rgba(0,255,255,0.08)]' : 'border-theme-border text-theme-text-muted hover:border-theme-accent/30 hover:text-theme-text-main'}`}
                >
                  <Icon size={16} />
                  {viz.label}
                  {loadingViz[viz.id] && <Loader2 size={14} className="animate-spin" />}
                </button>
              );
            })}
          </div>

          {/* Primary view */}
          <div className="glass-panel rounded-2xl p-6 analytics-card min-h-105">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-lg font-semibold text-theme-text-main">{activeViz?.label}</h3>
                <p className="text-xs text-theme-text-muted mt-1">{activeViz?.desc}</p>
              </div>
              <div className="flex gap-2">
                {images[activeTab] && (
                  <>
                    <IconButton icon={<Download size={16} />} label="Download" onClick={() => downloadImage(activeTab)} />
                    <IconButton icon={<Maximize2 size={16} />} label="Fullscreen" onClick={() => setFullscreen(activeTab)} />
                  </>
                )}
              </div>
            </div>
            <div className="relative rounded-xl overflow-hidden border border-theme-border bg-black/40 min-h-90 flex items-center justify-center">
              {loadingViz[activeTab] && (
                <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-theme-base/60 backdrop-blur-sm z-10">
                  <Loader2 className="animate-spin text-theme-accent" size={32} />
                  <span className="text-xs uppercase tracking-widest text-theme-text-muted">Rendering from backend...</span>
                </div>
              )}
              {images[activeTab] ? (
                <img src={images[activeTab]} alt={activeViz?.label} className="max-w-full h-auto transition-opacity duration-500" />
              ) : !loadingViz[activeTab] ? (
                <div className="text-theme-text-muted flex flex-col items-center gap-2">
                  <ImageIcon size={40} strokeWidth={1} />
                  <span className="text-sm">Select a tab to render</span>
                </div>
              ) : null}
            </div>
          </div>

          {/* Gallery grid */}
          <div>
            <h3 className="text-sm uppercase tracking-widest text-theme-text-muted font-semibold mb-4">Visualization Gallery</h3>
            <div className="grid sm:grid-cols-2 xl:grid-cols-4 gap-4">
              {VIZ_CATALOG.map((viz) => (
                <GalleryCard
                  key={viz.id}
                  viz={viz}
                  image={images[viz.id]}
                  loading={loadingViz[viz.id]}
                  active={activeTab === viz.id}
                  onSelect={() => handleTabChange(viz.id)}
                  onExpand={() => images[viz.id] && setFullscreen(viz.id)}
                  onDownload={() => downloadImage(viz.id)}
                />
              ))}
            </div>
          </div>
        </section>
      )}

      {/* Fullscreen modal */}
      {fullscreen && images[fullscreen] && (
        <div className="fixed inset-0 z-50 bg-black/90 backdrop-blur-md flex items-center justify-center p-4 animate-in fade-in" onClick={() => setFullscreen(null)}>
          <button className="absolute top-6 right-6 p-2 rounded-full bg-white/10 text-white hover:bg-white/20" onClick={() => setFullscreen(null)}>
            <X size={24} />
          </button>
          <img src={images[fullscreen]} alt="Fullscreen viz" className="max-w-[95vw] max-h-[90vh] rounded-lg shadow-2xl" onClick={(e) => e.stopPropagation()} />
        </div>
      )}
    </div>
  );
}

function TabButton({ active, onClick, children }) {
  return (
    <button onClick={onClick} className={`text-sm py-1 border-b-2 transition-colors ${active ? 'border-theme-accent text-theme-accent' : 'border-transparent text-theme-text-muted'}`}>
      {children}
    </button>
  );
}

function Badge({ icon, label, accent }) {
  return (
    <span className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold border ${accent ? 'border-theme-accent/40 bg-theme-accent/10 text-theme-accent' : 'border-theme-border bg-theme-border/20 text-theme-text-muted'}`}>
      {icon}{label}
    </span>
  );
}

function MetricCard({ title, value, sub, tooltip }) {
  return (
    <div className="glass-panel rounded-2xl p-4 analytics-card group relative" title={tooltip}>
      <p className="text-[10px] uppercase tracking-widest text-theme-text-muted mb-2">{title}</p>
      <p className="text-xl font-bold text-theme-text-main font-mono">{value}</p>
      {sub && <p className="text-xs mt-1 font-semibold text-theme-text-muted">{sub}</p>}
    </div>
  );
}

function InfoCell({ label, value }) {
  return (
    <div>
      <p className="text-[10px] uppercase tracking-widest text-theme-text-muted mb-1">{label}</p>
      <p className="font-mono text-xs text-theme-text-main truncate" title={value}>{value}</p>
    </div>
  );
}

function UploadBox({ label, file, onChange }) {
  return (
    <label className="flex flex-col gap-2 p-4 border border-dashed border-theme-border rounded-xl cursor-pointer hover:border-theme-accent/40 transition-colors">
      <span className="text-xs text-theme-text-muted">{label}</span>
      <span className="text-sm truncate">{file ? file.name : 'Click to upload .wav'}</span>
      <input type="file" accept=".wav" className="hidden" onChange={(e) => e.target.files?.[0] && onChange(e.target.files[0])} />
    </label>
  );
}

function IconButton({ icon, label, onClick }) {
  return (
    <button onClick={onClick} title={label} className="p-2 rounded-lg border border-theme-border hover:border-theme-accent/40 hover:bg-theme-accent/10 text-theme-text-muted hover:text-theme-accent transition-all">
      {icon}
    </button>
  );
}

function GalleryCard({ viz, image, loading, active, onSelect, onExpand, onDownload }) {
  const Icon = viz.icon;
  return (
    <div
      className={`group rounded-2xl border overflow-hidden transition-all duration-300 cursor-pointer analytics-card
        ${active ? 'border-theme-accent/50 ring-1 ring-theme-accent/30' : 'border-theme-border hover:border-theme-accent/30'}`}
      onClick={onSelect}
    >
      <div className="aspect-video bg-black/50 relative flex items-center justify-center">
        {loading && <Loader2 className="animate-spin text-cyan-400 absolute" size={24} />}
        {image ? (
          <img src={image} alt={viz.label} className="w-full h-full object-cover opacity-90" />
        ) : (
          <Icon size={28} className="text-theme-text-muted/40" />
        )}
        {image && (
          <div className="absolute top-2 right-2 flex gap-1 opacity-0 group-hover:opacity-100">
            <button onClick={(e) => { e.stopPropagation(); onExpand(); }} className="p-1.5 rounded bg-black/60 text-white"><Expand size={14} /></button>
            <button onClick={(e) => { e.stopPropagation(); onDownload(); }} className="p-1.5 rounded bg-black/60 text-white"><Download size={14} /></button>
          </div>
        )}
      </div>
      <div className="p-3">
        <p className="text-sm font-medium text-theme-text-main">{viz.label}</p>
        <p className="text-[10px] text-theme-text-muted mt-0.5 line-clamp-2">{viz.desc}</p>
      </div>
    </div>
  );
}
