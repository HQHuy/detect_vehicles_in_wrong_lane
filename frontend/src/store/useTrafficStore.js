import { create } from 'zustand'

export const useTrafficStore = create((set, get) => ({
  sessionId: null,
  isRunning: false,
  isPolygonMode: false,
  
  // Real stats mapped from backend
  stats: { car: 0, moto: 0, bus: 0, truck: 0, motorcycle: 0 },
  captures: [],
  finished: false,
  csvUrl: "",

  setSessionId: (id) => set({ sessionId: id, isRunning: true, finished: false }),
  setPolygonMode: (mode) => set({ isPolygonMode: mode }),
  
  updateStats: (data) => set((state) => ({
    stats: data.stats || state.stats, 
    captures: data.captures || state.captures,
    finished: data.finished ?? state.finished,
    csvUrl: data.csv_url || state.csvUrl
  })),

  // Polygon drawing state
  polygons: {
    car: [[10,95], [45,95], [40,40], [25,40]],
    moto: [[55,95], [90,95], [75,40], [45,40]],
    wrongway_down: [[45,95], [55,95], [45,40], [40,40]],
    wrongway_up: []
  },
  setPolygons: (updater) => set((state) => ({ 
    polygons: typeof updater === 'function' ? updater(state.polygons) : updater 
  })),

  pauseAnalysis: async () => {
    const { sessionId, isRunning } = get();
    if (!isRunning) return; 
    
    if (sessionId) {
      try {
          await fetch(`http://127.0.0.1:8000/api/pause_stream/${sessionId}`, { method: 'POST' });
      } catch (e) {
          console.error("Failed to pause stream on backend", e);
      }
    }
    set({ isRunning: false, isPolygonMode: true });
  },

  resumeAnalysis: async () => {
    const { sessionId, isRunning, polygons } = get();
    if (isRunning) return; 
    
    if (sessionId) {
      try {
          // Send updated polygons
          await fetch(`http://127.0.0.1:8000/api/update_polygons/${sessionId}`, { 
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ mode: 0, ...polygons })
          });
          // Resume stream
          await fetch(`http://127.0.0.1:8000/api/resume_stream/${sessionId}`, { method: 'POST' });
      } catch (e) {
          console.error("Failed to resume stream on backend", e);
      }
    }
    set({ isRunning: true, isPolygonMode: false });
  }
}))
