import { useState } from 'react';
import { Routes, Route, useLocation } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import TopBar from './components/TopBar';
import Dashboard from './components/Dashboard';
import ClaimAnalyzer from './components/ClaimAnalyzer';
import AgentView from './components/AgentView';
import NetworkView from './components/NetworkView';

import EntitiesView from './components/EntitiesView';
import LoginView from './components/LoginView';
import ProtectedRoute from './components/ProtectedRoute';


function App() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const location = useLocation();
  const isLoginPage = location.pathname === '/login';

  return (
    <>
      {!isLoginPage && <Sidebar isOpen={isSidebarOpen} setIsOpen={setIsSidebarOpen} />}
      {!isLoginPage && <TopBar isSidebarOpen={isSidebarOpen} />}
      
      <main 
        className={isLoginPage ? '' : `mt-16 p-8 bg-surface-container-lowest min-h-[calc(100vh-64px)] transition-all duration-300 ${isSidebarOpen ? 'ml-[240px]' : 'ml-[80px]'}`}
      >
        <Routes>
          <Route path="/login" element={<LoginView />} />
          
          <Route path="/" element={
            <ProtectedRoute>
              <div className="flex gap-6 flex-col xl:flex-row">
                <Dashboard />
              </div>
            </ProtectedRoute>
          } />
          <Route path="/analyzer" element={<ProtectedRoute><ClaimAnalyzer /></ProtectedRoute>} />
          <Route path="/agent" element={<ProtectedRoute><AgentView /></ProtectedRoute>} />
          <Route path="/network" element={<ProtectedRoute><NetworkView /></ProtectedRoute>} />
          <Route path="/entities" element={<ProtectedRoute><EntitiesView /></ProtectedRoute>} />
          <Route path="*" element={<ProtectedRoute><div className="p-8">En construcción...</div></ProtectedRoute>} />
        </Routes>
      </main>
    </>
  );
}

export default App;
