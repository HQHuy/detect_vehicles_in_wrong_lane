import { Upload, PenTool, Play, Trash2 } from 'lucide-react';
import { useTrafficStore } from '../store/useTrafficStore';
import { useRef, useState, useEffect } from 'react';

export default function VideoArea() {
  const { sessionId, isRunning, isPolygonMode, setPolygonMode, setSessionId, polygons, setPolygons, resumeAnalysis } = useTrafficStore();
  const fileInputRef = useRef(null);
  const [isProcessing, setIsProcessing] = useState(false);

  const [selectedFile, setSelectedFile] = useState(null);
  const [localVideoUrl, setLocalVideoUrl] = useState(null);
  
  const [activeDrawing, setActiveDrawing] = useState('car');

  // Cleanup local object url
  useEffect(() => {
    return () => {
      if (localVideoUrl) URL.revokeObjectURL(localVideoUrl);
    };
  }, [localVideoUrl]);

  const handleFileUpload = (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    
    setSelectedFile(file);
    if (localVideoUrl) URL.revokeObjectURL(localVideoUrl);
    setLocalVideoUrl(URL.createObjectURL(file));
    setPolygonMode(true);
    setSessionId(null); // Clear previous session
    useTrafficStore.setState({ isRunning: false, finished: false });
  };

  const startAnalysis = async () => {
    if (!selectedFile) return;

    setIsProcessing(true);
    setPolygonMode(false);
    
    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('poly_data', JSON.stringify({
      mode: 0,
      car: polygons.car,
      moto: polygons.moto,
      wrongway_down: polygons.wrongway_down,
      wrongway_up: polygons.wrongway_up
    }));

    try {
      const response = await fetch('http://127.0.0.1:8000/api/prepare_stream/', {
        method: 'POST',
        body: formData,
      });
      if (response.ok) {
        const data = await response.json();
        setSessionId(data.session_id);
      } else {
        console.error("Backend returned error");
      }
    } catch (err) {
      console.error("Failed to connect to backend", err);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleSvgClick = (e) => {
    if (!isPolygonMode || !activeDrawing) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * 100;
    const y = ((e.clientY - rect.top) / rect.height) * 100;
    
    setPolygons(prev => ({
      ...prev,
      [activeDrawing]: [...prev[activeDrawing], [x, y]]
    }));
  };

  const clearCurrentPolygon = () => {
    if (activeDrawing) {
      setPolygons(prev => ({ ...prev, [activeDrawing]: [] }));
    }
  };

  const videoSrc = sessionId 
    ? `http://127.0.0.1:8000/api/video_feed/${sessionId}`
    : null;

  // Helpers to render polygons
  const colors = {
    car: { fill: 'rgba(56, 189, 248, 0.1)', stroke: 'rgba(56, 189, 248, 0.8)', name: 'CAR LANE' },
    moto: { fill: 'rgba(16, 185, 129, 0.1)', stroke: 'rgba(16, 185, 129, 0.8)', name: 'MOTO LANE' },
    wrongway_down: { fill: 'rgba(239, 68, 68, 0.15)', stroke: 'rgba(239, 68, 68, 0.8)', name: 'WW DOWN' },
    wrongway_up: { fill: 'rgba(245, 158, 11, 0.15)', stroke: 'rgba(245, 158, 11, 0.8)', name: 'WW UP' }
  };

  return (
    <div className="relative w-full aspect-video bg-zinc-900 rounded-[2rem] overflow-hidden border border-zinc-800/50 shadow-2xl shrink-0 group flex flex-col">
      {/* Video / Image Display */}
      <div className="relative w-full h-full">
        {!sessionId && localVideoUrl && (
          <video 
            src={localVideoUrl} 
            className="w-full h-full object-cover opacity-60 mix-blend-luminosity"
            controls={false}
            autoPlay={false}
            muted
          />
        )}
        
        {sessionId && (
          <img 
            src={videoSrc} 
            alt="Traffic Feed" 
            className="w-full h-full object-cover opacity-60 mix-blend-luminosity transition-opacity duration-1000"
          />
        )}
        
        {!sessionId && !localVideoUrl && (
          <img 
            src="https://images.unsplash.com/photo-1515162816999-a0c47dc192f7?q=80&w=2070&auto=format&fit=crop"
            alt="Placeholder"
            className="w-full h-full object-cover opacity-60 mix-blend-luminosity"
          />
        )}

        <svg 
          className={`absolute inset-0 w-full h-full transition-opacity duration-300 ${isPolygonMode ? 'opacity-100' : (isRunning ? 'opacity-30' : 'opacity-0')} ${isPolygonMode ? 'cursor-crosshair' : 'pointer-events-none'}`} 
          viewBox="0 0 100 100" 
          preserveAspectRatio="none"
          onClick={handleSvgClick}
        >
          {Object.entries(polygons).map(([key, pts]) => {
            if (pts.length === 0) return null;
            const pointsStr = pts.map(p => `${p[0]},${p[1]}`).join(' ');
            const conf = colors[key];
            const isSelected = isPolygonMode && activeDrawing === key;
            return (
              <g key={key}>
                <polygon 
                  points={pointsStr} 
                  fill={isPolygonMode ? conf.fill : 'transparent'} 
                  stroke={conf.stroke} 
                  strokeWidth={isSelected ? "0.6" : "0.3"} 
                  strokeDasharray="1 1"
                />
                {pts.length > 0 && (
                  <text x={pts[0][0]} y={pts[0][1] - 2} fill={conf.stroke} fontSize="3" fontFamily="monospace" fontWeight="bold">
                    {conf.name}
                  </text>
                )}
                {isPolygonMode && pts.map((p, i) => (
                  <circle key={i} cx={p[0]} cy={p[1]} r="0.8" fill={conf.stroke} />
                ))}
              </g>
            );
          })}
        </svg>
      </div>

      {/* Status Overlay */}
      <div className="absolute top-6 left-6 flex items-center gap-2 bg-zinc-950/60 backdrop-blur px-3 py-1.5 rounded-full border border-white/5">
        <span className={`w-2 h-2 rounded-full ${isRunning ? 'bg-emerald-500' : (localVideoUrl && !sessionId ? 'bg-amber-500' : 'bg-rose-500')}`}></span>
        <span className="text-xs font-mono text-zinc-300 uppercase tracking-widest">
          {isRunning ? "Live Stream" : (localVideoUrl && !sessionId ? "Setup Phase" : (sessionId ? "Halted (Draw & Resume)" : "Ready"))}
        </span>
      </div>

      {/* Polygon Drawing Toolbar */}
      {isPolygonMode && (
        <div className="absolute top-6 right-6 flex flex-col gap-2 bg-zinc-950/80 backdrop-blur p-3 rounded-xl border border-white/5 z-20">
          <div className="text-xs font-mono text-zinc-400 mb-1 uppercase tracking-widest text-center">Draw Lanes</div>
          <div className="flex flex-col gap-2">
            {Object.keys(colors).map((key) => (
              <button 
                key={key}
                onClick={(e) => {
                  e.stopPropagation();
                  setActiveDrawing(key);
                }}
                className={`text-xs px-3 py-1.5 rounded font-mono uppercase text-left border ${
                  activeDrawing === key ? 'bg-zinc-800 border-zinc-600 text-white' : 'bg-transparent border-transparent text-zinc-500 hover:text-zinc-300'
                }`}
              >
                {colors[key].name}
              </button>
            ))}
          </div>
          <button 
            onClick={(e) => {
              e.stopPropagation();
              clearCurrentPolygon();
            }}
            className="mt-2 text-xs px-3 py-1.5 rounded font-mono uppercase bg-rose-500/20 text-rose-400 hover:bg-rose-500/30 flex items-center justify-center gap-1"
          >
            <Trash2 size={12} /> Clear Current
          </button>
        </div>
      )}

      {/* Toolbar */}
      <div className="absolute bottom-8 left-1/2 -translate-x-1/2 liquid-glass rounded-full px-2 py-2 flex items-center gap-1 transition-transform duration-300 hover:scale-105 z-10 opacity-0 group-hover:opacity-100">
        <input 
          type="file" 
          accept="video/*" 
          className="hidden" 
          ref={fileInputRef} 
          onChange={handleFileUpload} 
        />
        <button 
          onClick={() => fileInputRef.current?.click()} 
          disabled={isProcessing || isRunning}
          className="px-5 py-2.5 rounded-full text-sm font-medium text-zinc-300 hover:text-white hover:bg-white/10 transition-colors flex items-center gap-2 disabled:opacity-50"
        >
          <Upload size={18} />
          <span>{localVideoUrl ? "Change Source" : "Select Source"}</span>
        </button>
        
        <div className="w-px h-6 bg-zinc-700"></div>
        
        <button 
          onClick={() => setPolygonMode(!isPolygonMode)}
          disabled={isRunning || !localVideoUrl}
          className={`px-5 py-2.5 rounded-full text-sm font-medium transition-colors flex items-center gap-2 disabled:opacity-50 ${
            isPolygonMode 
              ? 'bg-zinc-800 text-white' 
              : 'text-zinc-400 hover:text-white hover:bg-white/10'
          }`}
        >
          <PenTool size={18} />
          <span>{isPolygonMode ? "Finish Setup" : "Setup Lanes"}</span>
        </button>

        {localVideoUrl && !isRunning && !sessionId && (
          <>
            <div className="w-px h-6 bg-zinc-700"></div>
            <button 
              onClick={startAnalysis}
              disabled={isProcessing}
              className="px-5 py-2.5 rounded-full text-sm font-medium bg-emerald-500 text-white hover:bg-emerald-400 transition-colors flex items-center gap-2 disabled:opacity-50"
            >
              <Play size={18} />
              <span>{isProcessing ? "Processing..." : "Start Analysis"}</span>
            </button>
          </>
        )}

        {sessionId && !isRunning && (
          <>
            <div className="w-px h-6 bg-zinc-700"></div>
            <button 
              onClick={resumeAnalysis}
              disabled={isProcessing}
              className="px-5 py-2.5 rounded-full text-sm font-medium bg-emerald-500 text-white hover:bg-emerald-400 transition-colors flex items-center gap-2 disabled:opacity-50"
            >
              <Play size={18} />
              <span>Resume Analysis</span>
            </button>
          </>
        )}
      </div>
    </div>
  );
}
