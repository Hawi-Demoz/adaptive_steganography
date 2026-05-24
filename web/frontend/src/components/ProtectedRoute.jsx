import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function ProtectedRoute({ children }) {
  const { isAuthenticated, isSetupRequired, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-theme-base">
        <div className="flex flex-col items-center gap-4">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-theme-accent border-t-transparent"></div>
          <p className="text-theme-text-muted animate-pulse">Decrypting access...</p>
        </div>
      </div>
    );
  }

  if (isSetupRequired) {
    return <Navigate to="/vault/setup" state={{ from: location }} replace />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/vault/login" state={{ from: location }} replace />;
  }

  return children;
}
