import { Square } from 'lucide-react';
import { useTrafficStore } from '../store/useTrafficStore';

export default function DataStream() {
  const { stats, isRunning, pauseAnalysis } = useTrafficStore();

  const formatNum = (num) => num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");

  return (
    <>
      <div className="pb-8 border-b border-zinc-800/60 group">
        <div className="flex items-baseline justify-between mb-2">
          <h3 className="text-sm font-medium text-zinc-500 uppercase tracking-widest">
            Cars <span className="text-sky-400/80 text-xs ml-2">(Lane 1)</span>
          </h3>
        </div>
        <div className="text-[5rem] xl:text-[6.5rem] leading-none font-mono tracking-tighter text-zinc-100 transition-all duration-300">
          {formatNum(stats.car)}
        </div>
      </div>

      <div className="py-8 border-b border-zinc-800/60 group">
        <div className="flex items-baseline justify-between mb-2">
          <h3 className="text-sm font-medium text-zinc-500 uppercase tracking-widest">
            Motorcycles <span className="text-emerald-400/80 text-xs ml-2">(Lane 2)</span>
          </h3>
        </div>
        <div className="text-[5rem] xl:text-[6.5rem] leading-none font-mono tracking-tighter text-zinc-100 transition-all duration-300">
          {formatNum((stats.motorcycle || 0) + (stats.moto || 0))}
        </div>
      </div>

      <div className="py-8 border-b border-zinc-800/60 group">
        <div className="flex items-baseline justify-between mb-2">
          <h3 className="text-sm font-medium text-zinc-500 uppercase tracking-widest">
            Bus & Trucks
          </h3>
        </div>
        <div className="text-[5rem] xl:text-[6.5rem] leading-none font-mono tracking-tighter text-zinc-100 transition-all duration-300">
          {formatNum(stats.bus + stats.truck)}
        </div>
      </div>

      <div className="mt-12">
        <button 
          onClick={pauseAnalysis}
          disabled={!isRunning}
          className={`group flex items-center gap-3 text-sm font-medium transition-colors active:scale-95 ${
            isRunning ? 'text-zinc-400 hover:text-rose-400' : 'text-emerald-400 opacity-50 cursor-not-allowed'
          }`}
        >
          <div className={`w-8 h-8 rounded-full border flex items-center justify-center transition-all ${
            isRunning ? 'border-zinc-800 group-hover:border-rose-400/50 group-hover:bg-rose-400/10' : 'border-emerald-400/30 bg-emerald-400/10'
          }`}>
            <div className={`w-2.5 h-2.5 rounded-sm transition-all duration-300 ${
              isRunning ? 'bg-current' : 'bg-emerald-400 rounded-full'
            }`} />
          </div>
          <span>{isRunning ? "Halt Analysis" : "Analysis Halted"}</span>
        </button>
      </div>
    </>
  );
}
