import { useState } from 'react';
import { Routes, Route } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import TopBar from './components/TopBar';
import Dashboard from './components/Dashboard';
import ClaimAnalyzer from './components/ClaimAnalyzer';
import AgentView from './components/AgentView';
import NetworkView from './components/NetworkView';

import EntitiesView from './components/EntitiesView';


function App() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  return (
    <>
      <Sidebar isOpen={isSidebarOpen} setIsOpen={setIsSidebarOpen} />
      <TopBar isSidebarOpen={isSidebarOpen} />
      <main 
        className={`mt-16 p-8 bg-surface-container-lowest min-h-[calc(100vh-64px)] transition-all duration-300 ${isSidebarOpen ? 'ml-[240px]' : 'ml-[80px]'}`}
      >
        <Routes>
          <Route path="/" element={
            <div className="flex gap-6 flex-col xl:flex-row">
              <Dashboard />
              {/* <AlertsPanel />  // Si quieres que el panel de alertas siga, o se quite */}
            </div>
          } />
          <Route path="/analyzer" element={<ClaimAnalyzer />} />
          <Route path="/agent" element={<AgentView />} />
          <Route path="/network" element={<NetworkView />} />
          <Route path="/entities" element={<EntitiesView />} />
          <Route path="*" element={<div className="p-8">En construcción...</div>} />
        </Routes>
      </main>
    </>
  );
}

export default App;
