import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Shield, Key, AlertCircle } from 'lucide-react';

export default function VaultSetupPage() {
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  const { setup } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (password.length < 8) {
      setError('Password must be at least 8 characters long.');
      return;
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    setIsSubmitting(true);
    try {
      await setup(password);
      navigate('/vault', { replace: true });
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to initialize vault.');
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-[80vh] items-center justify-center">
      <div className="w-full max-w-md p-8 glass-panel rounded-2xl border border-theme-accent/30 shadow-[0_0_40px_rgba(0,255,255,0.05)] relative overflow-hidden">
        {/* Decorative background glow */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-32 h-1 bg-theme-accent/50 blur-xl"></div>

        <div className="flex flex-col items-center mb-8">
          <div className="p-4 rounded-full bg-theme-base/50 border border-theme-border mb-4">
            <Shield className="w-10 h-10 text-theme-accent" strokeWidth={1.5} />
          </div>
          <h2 className="text-2xl font-bold tracking-wider text-theme-text-main">INITIALIZE VAULT</h2>
          <p className="text-theme-text-muted text-sm mt-2 text-center">
            Create a master password to secure your steganography artifacts. 
            This password will be required to access generated files.
          </p>
        </div>

        {error && (
          <div className="mb-6 p-3 rounded-lg bg-red-900/20 border border-red-500/50 flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
            <p className="text-sm text-red-200">{error}</p>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="space-y-1">
            <label className="text-xs font-semibold text-theme-text-muted uppercase tracking-wider pl-1">Master Password</label>
            <div className="relative">
              <Key className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-theme-text-muted" />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-theme-base/50 border border-theme-border rounded-xl py-3 pl-10 pr-4 text-theme-text-main placeholder-theme-text-muted focus:outline-none focus:border-theme-accent focus:ring-1 focus:ring-theme-accent transition-all"
                placeholder="Enter a strong password"
                required
              />
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-xs font-semibold text-theme-text-muted uppercase tracking-wider pl-1">Confirm Password</label>
            <div className="relative">
              <Key className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-theme-text-muted" />
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="w-full bg-theme-base/50 border border-theme-border rounded-xl py-3 pl-10 pr-4 text-theme-text-main placeholder-theme-text-muted focus:outline-none focus:border-theme-accent focus:ring-1 focus:ring-theme-accent transition-all"
                placeholder="Re-enter password"
                required
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full py-3 px-4 bg-theme-accent/10 hover:bg-theme-accent/20 border border-theme-accent text-theme-accent font-medium rounded-xl transition-all duration-300 disabled:opacity-50 flex items-center justify-center gap-2 group shadow-[0_0_15px_rgba(0,255,255,0.1)] hover:shadow-[0_0_25px_rgba(0,255,255,0.2)]"
          >
            {isSubmitting ? 'Encrypting...' : 'Secure Vault'}
          </button>
        </form>
      </div>
    </div>
  );
}
