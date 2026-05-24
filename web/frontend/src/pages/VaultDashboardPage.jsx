import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useStego } from '../context/StegoContext';
import { useAuth } from '../context/AuthContext';
import { Shield, Download, Activity, Unlock, Lock, Clock, FileAudio, LogOut } from 'lucide-react';

export default function VaultDashboardPage() {
  const { generatedFiles, refreshGeneratedFiles } = useStego();
  const { logout } = useAuth();
  const navigate = useNavigate();

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
    window.location.href = `http://localhost:5000/api/download/${filename}`;
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
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-mono text-theme-accent bg-theme-accent/10 px-2 py-0.5 rounded border border-theme-accent/20">
                      ID: {file.stego_filename.split('_')[1]?.substring(0, 8) || 'unknown'}
                    </span>
                    {file.encrypt && (
                      <span className="text-xs font-mono text-green-400 flex items-center gap-1">
                        <Lock size={10} /> ENCRYPTED
                      </span>
                    )}
                  </div>
                  <h3 className="font-medium text-theme-text-main truncate" title={file.stego_filename}>
                    {file.stego_filename}
                  </h3>
                  <div className="flex items-center gap-1 text-xs text-theme-text-muted mt-2">
                    <Clock size={12} /> {formatDate(file.timestamp)}
                  </div>
                </div>

                <div className="space-y-1 mb-4 text-xs font-mono">
                  <div className="flex justify-between border-b border-theme-border/50 pb-1">
                    <span className="text-theme-text-muted">Carrier</span>
                    <span className="truncate max-w-[120px]" title={file.original_name || file.cover_filename}>
                      {file.original_name || file.cover_filename}
                    </span>
                  </div>
                  <div className="flex justify-between border-b border-theme-border/50 pb-1">
                    <span className="text-theme-text-muted">Energy</span>
                    <span>{file.energy_percentile}%</span>
                  </div>
                  <div className="flex justify-between pb-1">
                    <span className="text-theme-text-muted">Robustness</span>
                    <span>{file.robust_repeat}x</span>
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-2 mt-auto">
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
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
