import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Lock, Unlock, AlertCircle, Eye, EyeOff } from 'lucide-react';

export default function VaultLoginPage() {
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isUnlocking, setIsUnlocking] = useState(false);
  
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const from = location.state?.from?.pathname || '/vault';

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setIsSubmitting(true);
    
    try {
      await login(password);
      setIsUnlocking(true);
      
      // Delay navigation slightly to show unlock animation
      setTimeout(() => {
        navigate(from, { replace: true });
      }, 800);
      
    } catch (err) {
      setError(err.response?.data?.error || 'Invalid credentials.');
      setIsSubmitting(false);
      setPassword('');
    }
  };

  return (
    <div className="flex min-h-[80vh] items-center justify-center">
      <div className={`w-full max-w-md p-8 glass-panel rounded-2xl border border-theme-border shadow-lg relative overflow-hidden transition-all duration-700 ${isUnlocking ? 'border-theme-accent/50 shadow-[0_0_50px_rgba(0,255,255,0.1)] scale-105' : ''}`}>
        
        <div className="flex flex-col items-center mb-8">
          <div className={`p-4 rounded-full border mb-4 transition-all duration-500 ${isUnlocking ? 'bg-theme-accent/10 border-theme-accent text-theme-accent' : 'bg-theme-base/50 border-theme-border text-theme-text-muted'}`}>
            {isUnlocking ? (
              <Unlock className="w-10 h-10" strokeWidth={1.5} />
            ) : (
              <Lock className="w-10 h-10" strokeWidth={1.5} />
            )}
          </div>
          <h2 className="text-2xl font-bold tracking-wider text-theme-text-main">
            {isUnlocking ? 'VAULT DECRYPTED' : 'RESTRICTED ACCESS'}
          </h2>
          <p className="text-theme-text-muted text-sm mt-2 text-center">
            {isUnlocking ? 'Establishing secure connection...' : 'Please enter your master password to unlock the vault.'}
          </p>
        </div>

        {error && (
          <div className="mb-6 p-3 rounded-lg bg-red-900/20 border border-red-500/50 flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
            <p className="text-sm text-red-200">{error}</p>
          </div>
        )}

        <form onSubmit={handleSubmit} className={`space-y-6 transition-opacity duration-500 ${isUnlocking ? 'opacity-0' : 'opacity-100'}`}>
          <div className="space-y-1">
            <div className="relative">
              <input
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-theme-base/50 border border-theme-border rounded-xl py-3 px-4 pr-12 text-center text-lg tracking-[0.5em] text-theme-text-main placeholder-theme-text-muted/50 focus:outline-none focus:border-theme-accent focus:ring-1 focus:ring-theme-accent transition-all font-mono"
                placeholder="••••••••"
                required
                autoFocus
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-theme-text-muted hover:text-theme-text-main transition-colors p-1"
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={isSubmitting || isUnlocking}
            className="w-full py-3 px-4 bg-theme-border/30 hover:bg-theme-border/50 text-theme-text-main font-medium rounded-xl transition-all duration-300 disabled:opacity-50"
          >
            {isSubmitting ? 'Verifying...' : 'Authenticate'}
          </button>
        </form>
      </div>
    </div>
  );
}
