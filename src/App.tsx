import { AnimatePresence } from 'framer-motion';
import { Navbar } from './components/Layout/Navbar';
import { Sidebar } from './components/Layout/Sidebar';
import { StatusBar } from './components/Layout/StatusBar';
import { ProjectDashboard } from './components/Dashboard/ProjectDashboard';
import { ProjectGenerator } from './components/Generator/ProjectGenerator';
import { ProjectBuilder } from './components/Builder/ProjectBuilder';
import { ProjectPusher } from './components/Pusher/ProjectPusher';
import { useProjectStore } from './store/projectStore';

function App() {
  const { activeView } = useProjectStore();

  const renderView = () => {
    switch (activeView) {
      case 'dashboard':
        return <ProjectDashboard />;
      case 'generator':
        return <ProjectGenerator />;
      case 'builder':
        return <ProjectBuilder />;
      case 'pusher':
        return <ProjectPusher />;
      default:
        return <ProjectDashboard />;
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0e17] text-[#f1f5f9] font-sans flex flex-col">
      <Navbar />
      <div className="flex flex-1 min-h-0">
        <Sidebar />
        <main className="flex-1 min-h-0 overflow-auto bg-gradient-to-br from-[#0a0e17] via-[#0f1219] to-[#0a0e17]">
          <AnimatePresence mode="wait">
            {renderView()}
          </AnimatePresence>
        </main>
      </div>
      <StatusBar />
    </div>
  );
}

export default App;
