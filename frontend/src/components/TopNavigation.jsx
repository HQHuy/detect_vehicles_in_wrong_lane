import { Download } from 'lucide-react';
import { useTrafficStore } from '../store/useTrafficStore';

export default function TopNavigation() {
  const { isRunning, finished, csvUrl } = useTrafficStore();
  
  const canExport = finished;

  return (
    <header className="flex justify-between items-center w-full max-w-[1600px] mx-auto mb-10">
      <div className="flex items-center gap-3">
        <div 
          className={`w-3 h-3 rounded-full transition-colors duration-300 ${
            isRunning 
              ? 'bg-emerald-500 shadow-[0_0_12px_rgba(16,185,129,0.8)] animate-pulse' 
              : 'bg-zinc-700'
          }`}
        />
        <h1 className="text-xl font-medium tracking-tight">TrafficAI<span className="text-zinc-500">_</span></h1>
      </div>
      
      <button 
        disabled={!canExport}
        className={`text-sm font-medium transition-colors flex items-center gap-2 group ${
          canExport 
            ? 'text-emerald-400 hover:text-emerald-300 cursor-pointer' 
            : 'text-zinc-500 cursor-not-allowed'
        }`}
        onClick={() => {
            if (csvUrl) {
                // In reality, this would trigger a download from the backend
                window.open(`http://127.0.0.1:8000${csvUrl}`, '_blank');
            }
        }}
      >
        <span>{canExport ? "Download CSV" : "Export CSV (Pending)"}</span>
        <Download size={16} className={canExport ? "" : "opacity-50"} />
      </button>
    </header>
  );
}
