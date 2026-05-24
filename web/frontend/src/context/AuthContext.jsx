import { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';

const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isSetupRequired, setIsSetupRequired] = useState(false);
  const [loading, setLoading] = useState(true);

  // Configure axios to always send credentials (cookies)
  axios.defaults.withCredentials = true;

  const checkStatus = async () => {
    try {
      const res = await axios.get('http://localhost:5000/api/auth/status');
      setIsSetupRequired(res.data.setupRequired);
      setIsAuthenticated(res.data.authenticated);
    } catch (err) {
      console.error('Failed to check auth status', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkStatus();
  }, []);

  const login = async (password) => {
    const res = await axios.post('http://localhost:5000/api/auth/login', { password });
    if (res.data.success) {
      setIsAuthenticated(true);
    }
    return res.data;
  };

  const setup = async (password) => {
    const res = await axios.post('http://localhost:5000/api/auth/setup', { password });
    if (res.data.success) {
      setIsSetupRequired(false);
      setIsAuthenticated(true);
    }
    return res.data;
  };

  const logout = async () => {
    await axios.post('http://localhost:5000/api/auth/logout');
    setIsAuthenticated(false);
  };

  return (
    <AuthContext.Provider value={{
      isAuthenticated,
      isSetupRequired,
      loading,
      login,
      setup,
      logout,
      checkStatus
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
