import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useStego } from '../context/StegoContext';
import { useAuth } from '../context/AuthContext';
import { Shield, Download, Activity, Unlock, Lock, Clock, FileAudio, LogOut } from 'lucide-react';
import { API_BASE } from '../lib/api';

export default function VaultDashboardPage() {
  const { generatedFiles, refreshGeneratedFiles } = useStego();
  const { logout } = useAuth();
  const navigate = useNavigate();
  const [expandedFiles, setExpandedFiles] = useState({});

  const toggleExpand = (stego_filename) => {
    setExpandedFiles(prev => ({
      ...prev,
      [stego_filename]: !prev[stego_filename]
    }));
  };

  useEffect(() => {
    refreshGeneratedFiles();
  }, [refreshGeneratedFiles]);

  const handleLogout = async () => {
    await logout();
    navigate('/vault/login', { replace: true });
  };

  const handleExtract = (file) => {
    // Navigate to extract page and pass the selected file state
    navigate('/extract', { state: { selectedStegoFile: file } });
  };

  const handleVisualize = (file) => {
    // Navigate to visualization page and pass the selected file state
    navigate('/visuals', { state: { selectedCover: file.cover_filename, selectedStego: file.stego_filename } });
  };

  const handleDownload = (filename) => {
    window.location.href = `${API_BASE}/api/download/${filename}`;
  };

  const formatDate = (timestamp) => {
    return new Date(timestamp * 1000).toLocaleString();
  };

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-theme-text-main flex items-center gap-3">
            <Shield className="text-theme-accent" /> SECURE VAULT
          </h1>
          <p className="text-theme-text-muted mt-1">
            Access and manage your generated steganography artifacts securely.
          </p>
        </div>
        
        <button 
          onClick={handleLogout}
          className="flex items-center gap-2 px-4 py-2 bg-theme-border/30 hover:bg-red-500/20 hover:text-red-400 border border-theme-border hover:border-red-500/50 rounded-lg transition-all duration-300 text-sm font-medium"
        >
          <LogOut size={16} /> Lock Vault
        </button>
      </div>

      <div className="glass-panel p-6 border border-theme-border shadow-lg">
        <h2 className="text-xl font-semibold mb-6 flex items-center gap-2">
          <FileAudio className="text-theme-accent" size={20} /> Stored Artifacts
        </h2>

        {generatedFiles.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-theme-text-muted bg-theme-base/30 rounded-xl border border-dashed border-theme-border">
            <Shield size={48} className="mb-4 opacity-50" strokeWidth={1} />
            <p>Your vault is empty.</p>
            <p className="text-sm">Generate stego files to see them stored here securely.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {generatedFiles.map((file, idx) => (
              <div 
                key={idx} 
                className="bg-theme-base/50 border border-theme-border rounded-xl p-5 hover:border-theme-accent/50 transition-all duration-300 hover:shadow-[0_0_20px_rgba(0,255,255,0.05)] group relative overflow-hidden"
              >
                {/* Decoration */}
                <div className="absolute top-0 right-0 p-2 opacity-10 group-hover:opacity-20 transition-opacity">
                  <Shield size={64} />
                </div>

                <div className="mb-4">
                  <div className="flex flex-wrap items-center gap-2 mb-1">
                    <span className="text-xs font-mono text-theme-accent bg-theme-accent/10 px-2 py-0.5 rounded border border-theme-accent/20">
                      ID: {file.id || file.stego_filename.replace(/\.wav$/i, '').substring(0, 8) || 'unknown'}
                    </span>
                    {file.encrypt && (
                      <span className="text-[10px] font-mono text-green-400 flex items-center gap-1 bg-green-400/10 px-1.5 py-0.5 rounded border border-green-400/20">
                        <Lock size={10} /> ENCRYPTED
                      </span>
                    )}
                    {file.energy_percentile > 0 && (
                      <span className="text-[10px] font-mono text-blue-400 flex items-center gap-1 bg-blue-400/10 px-1.5 py-0.5 rounded border border-blue-400/20">
                        ADAPTIVE
                      </span>
                    )}
                  </div>
                  
                  <div 
                    className="cursor-pointer group/title flex items-center justify-between mt-2 mb-1" 
                    onClick={() => toggleExpand(file.stego_filename)}
                  >
                    <h3 className="font-medium text-theme-text-main truncate group-hover/title:text-theme-accent transition-colors" title={file.stego_filename}>
                      {file.stego_filename}
                    </h3>
                    <span className="text-[10px] text-theme-accent/70 group-hover/title:text-theme-accent px-2">
                      {expandedFiles[file.stego_filename] ? '▲' : '▼'}
                    </span>
                  </div>
                  
                  <div className="flex items-center gap-1 text-xs text-theme-text-muted">
                    <Clock size={12} /> {formatDate(file.timestamp)}
                  </div>
                </div>

                {expandedFiles[file.stego_filename] && (
                  <div className="space-y-1 mb-4 text-xs font-mono animate-in fade-in slide-in-from-top-2">
                    <div className="flex justify-between border-b border-theme-border/50 pb-1">
                      <span className="text-theme-text-muted">Carrier</span>
                      <span className="truncate max-w-30" title={file.original_cover_name || file.original_name || file.cover_filename}>
                        {file.original_cover_name || file.original_name || file.cover_filename}
                      </span>
                    </div>
                    <div className="flex justify-between border-b border-theme-border/50 pb-1">
                      <span className="text-theme-text-muted">Stego Output</span>
                      <span className="truncate max-w-30" title={file.stego_filename}>
                        {file.stego_filename}
                      </span>
                    </div>
                    <div className="flex justify-between border-b border-theme-border/50 pb-1">
                      <span className="text-theme-text-muted">Capacity</span>
                      <span>
                        {file.energy_percentile === 40 ? '60% (High Adaptivity)' :
                         file.energy_percentile === 20 ? '80% (Medium Adaptivity)' :
                         file.energy_percentile === 0 ? '100% (Low Adaptivity)' :
                         `${100 - (file.energy_percentile || 0)}%`}
                      </span>
                    </div>
                    <div className="flex justify-between border-b border-theme-border/50 pb-1">
                      <span className="text-theme-text-muted">Encryption</span>
                      <span className={file.encrypt ? "text-green-400" : "text-theme-text-muted"}>{file.encrypt ? 'Enabled' : 'Disabled'}</span>
                    </div>
                    <div className="flex justify-between border-b border-theme-border/50 pb-1">
                      <span className="text-theme-text-muted">Payload Size</span>
                      <span>{file.payload_size ? `${file.payload_size} bytes` : 'N/A'}</span>
                    </div>
                    <div className="flex justify-between pb-1 mt-1">
                      <span className="text-theme-text-muted">SNR</span>
                      <span className="text-theme-accent font-semibold">{file.snr_db ? `${file.snr_db.toFixed(1)} dB` : 'N/A'}</span>
                    </div>
                  </div>
                )}

                <div className="grid grid-cols-5 gap-2 mt-auto">
                  <button 
                    onClick={() => handleExtract(file)}
                    className="flex flex-col items-center justify-center py-2 bg-theme-border/30 hover:bg-theme-accent/20 text-theme-text-main hover:text-theme-accent rounded-lg transition-colors border border-transparent hover:border-theme-accent/30 gap-1 text-xs"
                    title="Extract Payload"
                  >
                    <Unlock size={16} />
                    <span>Extract</span>
                  </button>
                  <button 
                    onClick={() => handleVisualize(file)}
                    className="flex flex-col items-center justify-center py-2 bg-theme-border/30 hover:bg-purple-500/20 text-theme-text-main hover:text-purple-400 rounded-lg transition-colors border border-transparent hover:border-purple-500/30 gap-1 text-xs"
                    title="Visualize Analysis"
                  >
                    <Activity size={16} />
                    <span>Analyze</span>
                  </button>
                  <button 
                    onClick={() => handleDownload(file.stego_filename)}
                    className="flex flex-col items-center justify-center py-2 bg-theme-border/30 hover:bg-green-500/20 text-theme-text-main hover:text-green-400 rounded-lg transition-colors border border-transparent hover:border-green-500/30 gap-1 text-xs"
                    title="Download File"
                  >
                    <Download size={16} />
                    <span>Save</span>
                  </button>
                  <button
                    onClick={async () => {
                      const newName = window.prompt('Enter new filename (with or without .wav):', file.stego_filename);
                      if (!newName) return;
                      try {
                        await fetch(`${API_BASE}/api/session/files/${encodeURIComponent(file.stego_filename)}`, {
                          method: 'PUT',
                          headers: { 'Content-Type': 'application/json' },
                          body: JSON.stringify({ new_name: newName }),
                          credentials: 'include',
                        }).then(r => r.json()).then(res => {
                          if (res.error) throw new Error(res.error);
                        });
                        await refreshGeneratedFiles();
                        setExpandedFiles(prev => ({ ...prev, [file.stego_filename]: false }));
                      } catch (err) {
                        alert('Rename failed: ' + (err.message || err));
                      }
                    }}
                    className="flex flex-col items-center justify-center py-2 bg-theme-border/30 hover:bg-yellow-500/20 text-theme-text-main hover:text-yellow-400 rounded-lg transition-colors border border-transparent hover:border-yellow-500/30 gap-1 text-xs"
                    title="Rename file"
                  >
                    <Clock size={16} />
                    <span>Rename</span>
                  </button>
                  <button
                    onClick={async () => {
                      if (!window.confirm(`Delete ${file.stego_filename}? This cannot be undone.`)) return;
                      try {
                        const res = await fetch(`${API_BASE}/api/session/files/${encodeURIComponent(file.stego_filename)}`, {
                          method: 'DELETE',
                          credentials: 'include',
                        });
                        const data = await res.json();
                        if (!res.ok) throw new Error(data.error || 'Delete failed');
                        await refreshGeneratedFiles();
                        setExpandedFiles(prev => ({ ...prev, [file.stego_filename]: false }));
                      } catch (err) {
                        alert('Delete failed: ' + (err.message || err));
                      }
                    }}
                    className="flex flex-col items-center justify-center py-2 bg-theme-border/30 hover:bg-red-500/20 text-theme-text-main hover:text-red-400 rounded-lg transition-colors border border-transparent hover:border-red-500/30 gap-1 text-xs"
                    title="Delete file"
                  >
                    <Unlock size={16} />
                    <span>Delete</span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
