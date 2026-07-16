import { useEffect } from 'react';
import TopNavigation from './components/TopNavigation';
import VideoArea from './components/VideoArea';
import CapturesLog from './components/CapturesLog';
import DataStream from './components/DataStream';
import { useTrafficStore } from './store/useTrafficStore';

export default function App() {
  const { sessionId, isRunning, updateStats } = useTrafficStore();

  useEffect(() => {
    let interval;
    if (sessionId && isRunning) {
      interval = setInterval(async () => {
        try {
          // Poll the FastAPI backend for stats
          const res = await fetch(`http://127.0.0.1:8000/api/stream_stats/${sessionId}`);
          if (res.ok) {
            const data = await res.json();
            updateStats(data);
            if (data.finished) {
               useTrafficStore.setState({ isRunning: false });
            }
          }
        } catch (error) {
          console.error("Error fetching stats:", error);
        }
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [sessionId, isRunning, updateStats]);

  return (
    <>
      <TopNavigation />
      <main className="flex-1 flex flex-col lg:flex-row gap-8 lg:gap-16 w-full max-w-[1600px] mx-auto px-4 lg:px-8 pb-12">
        
        {/* Left Side: Focus Zone (70%) */}
        <section className="w-full lg:w-[70%] flex flex-col relative group min-w-0">
          <VideoArea />
          <CapturesLog />
        </section>

        {/* Right Side: Data Stream (30%) */}
        <section className="w-full lg:w-[30%] flex flex-col justify-start pt-4">
          <DataStream />
        </section>
        
      </main>
    </>
  );
}
