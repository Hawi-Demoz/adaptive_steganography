import { useState } from 'react';
import axios from 'axios';
import { UploadCloud, Settings, Shield, FileAudio } from 'lucide-react';

export default function EmbedPage() {
  const [file, setFile] = useState(null);
  const [message, setMessage] = useState('');
  const [password, setPassword] = useState('');
  const [encrypt, setEncrypt] = useState(true);
  const [energyPercentile, setEnergyPercentile] = useState(20);
  const [isLoading, setIsLoading] = useState(false);

  const handleFileChange = (e) => {
    if (e.target.files[0]) setFile(e.target.files[0]);
  };

  const handleEmbed = async () => {
    if (!file || !message || !password) return alert("Missing fields!");
    
    setIsLoading(true);
    const formData = new FormData();
    formData.append('cover', file);
    formData.append('message', message);
    formData.append('password', password);
    formData.append('encrypt', encrypt);
    formData.append('energy_percentile', energyPercentile);

    try {
      const response = await axios.post('http://localhost:5000/api/embed', formData, {
        responseType: 'blob', // Important for file downloads
      });
      
      // Create a URL and trigger download of the stego wav
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'stego_output.wav');
      document.body.appendChild(link);
      link.click();
      
    } catch (error) {
      console.error(error);
      alert("Error generating stego file.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <header className="mb-8">
        <h2 className="text-3xl font-bold">Embed Data</h2>
        <p className="text-gray-400 mt-2">Adaptively hide a secret message within a WAV cover signal.</p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Left Column: Data Input */}
        <div className="space-y-6">
          <div className="bg-dark-card border border-dark-border p-6 rounded-xl">
            <h3 className="text-lg font-semibold flex items-center gap-2 mb-4">
              <UploadCloud size={20} className="text-blue-400"/> Cover Audio
            </h3>
            <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-dark-border hover:border-blue-500 rounded-lg cursor-pointer bg-dark-bg/50 transition-colors">
              <div className="flex flex-col items-center justify-center pt-5 pb-6">
                <FileAudio size={28} className="text-gray-400 mb-2" />
                <p className="text-sm text-gray-400">
                  {file ? <span className="text-green-400 font-medium">{file.name}</span> : 'Click or drag WAV file here'}
                </p>
              </div>
              <input type="file" className="hidden" accept=".wav" onChange={handleFileChange} />
            </label>
          </div>

          <div className="bg-dark-card border border-dark-border p-6 rounded-xl space-y-4">
            <h3 className="text-lg font-semibold flex items-center gap-2">
              <Shield size={20} className="text-blue-400"/> Secret Payload
            </h3>
            <textarea 
              className="w-full bg-dark-bg border border-dark-border rounded-lg p-3 text-sm focus:outline-none focus:border-blue-500 min-h-[100px]"
              placeholder="Enter secret message text..."
              value={message} onChange={(e) => setMessage(e.target.value)}
            />
            <input 
              type="password" 
              className="w-full bg-dark-bg border border-dark-border rounded-lg p-3 text-sm focus:outline-none focus:border-blue-500"
              placeholder="Encryption/Ordering Key"
              value={password} onChange={(e) => setPassword(e.target.value)}
            />
            <label className="flex items-center gap-2 text-sm text-gray-300">
              <input type="checkbox" checked={encrypt} onChange={(e)=>setEncrypt(e.target.checked)} className="rounded bg-dark-bg border-dark-border text-blue-500 focus:ring-blue-500"/>
              Enable AES-CBC Encryption
            </label>
          </div>
        </div>

        {/* Right Column: Parameters and Actions */}
        <div className="bg-dark-card border border-dark-border p-6 rounded-xl flex flex-col">
          <h3 className="text-lg font-semibold flex items-center gap-2 mb-6">
            <Settings size={20} className="text-blue-400"/> Adaptive Parameters
          </h3>
          
          <div className="space-y-6 flex-1">
            <div>
              <div className="flex justify-between text-sm mb-2">
                <label className="text-gray-300">Energy Percentile</label>
                <span className="text-blue-400 font-mono">{energyPercentile}%</span>
              </div>
              <input 
                type="range" min="0" max="100" 
                value={energyPercentile} onChange={(e)=>setEnergyPercentile(e.target.value)}
                className="w-full accent-blue-500"
              />
              <p className="text-xs text-gray-500 mt-2">Higher values restrict embedding to only the loudest frames (better imperceptibility, lower capacity).</p>
            </div>
          </div>

          <button 
            onClick={handleEmbed}
            disabled={isLoading}
            className="w-full py-3 mt-6 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-600 rounded-lg font-semibold transition-colors flex items-center justify-center gap-2"
          >
            {isLoading ? 'Processing Pipeline...' : 'Generate Stego Audio'}
          </button>
        </div>
      </div>
    </div>
  );
}
