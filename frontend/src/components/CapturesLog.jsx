import { useTrafficStore } from '../store/useTrafficStore';
import { useRef, useEffect } from 'react';

export default function CapturesLog() {
  const { captures } = useTrafficStore();
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({
        left: scrollRef.current.scrollWidth,
        behavior: 'smooth'
      });
    }
  }, [captures.length]);

  return (
    <div className="mt-8 shrink-0">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-xs font-medium text-zinc-500 uppercase tracking-widest">Recent Captures (Violations)</h3>
        <span className="text-xs font-mono text-zinc-600">{captures.length} events</span>
      </div>
      
      <div ref={scrollRef} className="flex gap-4 overflow-x-auto pb-4 snap-x">
        {/* Render captures sequentially (left to right) */}
        {captures.map((cap) => (
          <div key={cap.id} className="min-w-[160px] md:min-w-[200px] aspect-video bg-zinc-900 rounded-xl border border-zinc-800/50 relative overflow-hidden group snap-start shrink-0">
            <img 
              src={cap.image_url.startsWith('http') ? cap.image_url : `http://127.0.0.1:8000${cap.image_url}`} 
              alt={cap.event}
              className="w-full h-full object-cover opacity-60 group-hover:opacity-100 transition-opacity duration-300 grayscale group-hover:grayscale-0"
            />
            <div className="absolute bottom-0 inset-x-0 bg-gradient-to-t from-zinc-950 to-transparent p-3 pt-6">
              <span className="text-[10px] font-mono text-rose-400 block mb-0.5">{cap.time}</span>
              <span className="text-xs font-medium text-zinc-100 capitalize">{cap.event} - {cap.type}</span>
            </div>
          </div>
        ))}
        {captures.length === 0 && (
          <div className="w-full h-24 flex items-center justify-center border border-dashed border-zinc-800/50 rounded-xl text-zinc-600 text-sm">
            No violations captured yet
          </div>
        )}
      </div>
    </div>
  );
}
