import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import EmbedPage from './pages/EmbedPage';
// import ExtractPage from './pages/ExtractPage';
// import VisualsPage from './pages/VisualsPage';
// import MLPage from './pages/MLPage';
import { Activity, Lock, Unlock, BarChart } from 'lucide-react';

function App() {
  return (
    <Router>
      <div className="min-h-screen flex text-gray-100 font-sans">
        {/* Sidebar Navigation */}
        <aside className="w-64 bg-dark-card border-r border-dark-border p-5 flex flex-col gap-6">
          <h1 className="text-xl font-bold text-blue-400 tracking-wider mb-6">
            STEGO<span className="text-white">RESEARCH</span>
          </h1>
          <nav className="flex flex-col gap-2">
            <NavItem to="/" icon={<Lock size={18}/>} label="Embed Message" />
            <NavItem to="/extract" icon={<Unlock size={18}/>} label="Extract Message" />
            <NavItem to="/visuals" icon={<Activity size={18}/>} label="Visualizations" />
            <NavItem to="/ml-detect" icon={<BarChart size={18}/>} label="ML Detectability" />
          </nav>
        </aside>

        {/* Main Content Area */}
        <main className="flex-1 p-8 overflow-y-auto">
          <Routes>
            <Route path="/" element={<EmbedPage />} />
            {/* <Route path="/extract" element={<ExtractPage />} /> */}
            {/* <Route path="/visuals" element={<VisualsPage />} /> */}
            {/* <Route path="/ml-detect" element={<MLPage />} /> */}
          </Routes>
        </main>
      </div>
    </Router>
  );
}

function NavItem({ to, icon, label }) {
  return (
    <Link to={to} className="flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-blue-600/20 hover:text-blue-400 transition-colors">
      {icon}
      <span className="font-medium">{label}</span>
    </Link>
  );
}

export default App;
