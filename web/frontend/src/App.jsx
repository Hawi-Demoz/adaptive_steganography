import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import { useState, useEffect } from 'react';
import EmbedPage from './pages/EmbedPage';
import ExtractPage from './pages/ExtractPage';
import MLPage from './pages/MLPage';
import VisualsPage from './pages/VisualsPage';
import { StegoProvider } from './context/StegoContext';
import { Activity, Lock, Unlock, BarChart, Moon, Sun } from 'lucide-react';

function App() {
  const [theme, setTheme] = useState('dark'); // Default to cinematic dark

  useEffect(() => {
    if (theme === 'dark') document.documentElement.classList.add('dark');
    else document.documentElement.classList.remove('dark');
  }, [theme]);

  const toggleTheme = () => setTheme(prev => prev === 'dark' ? 'light' : 'dark');

  return (
    <StegoProvider>
      <Router>
        <div className="min-h-screen flex bg-theme-base text-theme-text-main transition-colors duration-500 bg-cinematic">
          {/* Sidebar Navigation */}
          <aside className="w-64 glass-panel border-r border-theme-border flex flex-col z-10 relative">
          <div className="p-6">
            <h1 className="text-xl font-bold tracking-tight text-theme-text-main flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-theme-accent"></span>
              Stego<span className="text-theme-text-muted font-normal">Research</span>
            </h1>
          </div>
          
          <nav className="flex flex-col gap-1 px-3 mt-4 flex-1">
            <NavItem to="/" icon={<Lock size={18} strokeWidth={1.5}/>} label="Embed Payload" />
            <NavItem to="/extract" icon={<Unlock size={18} strokeWidth={1.5}/>} label="Extract Data" />
            <NavItem to="/visuals" icon={<Activity size={18} strokeWidth={1.5}/>} label="Visualizations" />
            <NavItem to="/ml-detect" icon={<BarChart size={18} strokeWidth={1.5}/>} label="Detectability" />
          </nav>

          {/* Theme Toggle Footer */}
          <div className="p-4 border-t border-theme-border">
            <button 
              onClick={toggleTheme}
              className="flex items-center justify-between w-full p-3 rounded-lg text-theme-text-muted hover:text-theme-text-main hover:bg-theme-border/30 transition-all text-sm font-medium"
            >
              <span>{theme === 'dark' ? 'Dark Mode' : 'Light Mode'}</span>
              {theme === 'dark' ? <Moon size={16} /> : <Sun size={16} />}
            </button>
          </div>
        </aside>

        {/* Main Content Area */}
        <main className="flex-1 p-8 md:p-12 overflow-y-auto relative z-10">
          <div className="max-w-5xl mx-auto">
            <Routes>
              <Route path="/" element={<EmbedPage />} />
              <Route path="/extract" element={<ExtractPage />} />
              <Route path="/visuals" element={<VisualsPage />} />
              <Route path="/ml-detect" element={<MLPage />} />
            </Routes>
          </div>
        </main>
      </div>
      </Router>
    </StegoProvider>
  );
}

function NavItem({ to, icon, label }) {
  const location = useLocation();
  const isActive = location.pathname === to;

  return (
    <Link 
      to={to} 
      className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-300 font-medium text-sm
        ${isActive 
          ? 'bg-theme-border/50 text-theme-text-main shadow-sm' 
          : 'text-theme-text-muted hover:text-theme-text-main hover:bg-theme-border/20'}`}
    >
      <span className={isActive ? 'text-theme-accent' : ''}>{icon}</span>
      {label}
    </Link>
  );
}

export default App;
