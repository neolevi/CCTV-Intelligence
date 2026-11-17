import React, { useState, useEffect } from 'react';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { ThemeProvider } from './contexts/ThemeContext';
import { Navbar } from './components/Navbar';
import { Sidebar, NavTab } from './components/Sidebar';
import { Login } from './pages/Login';
import { Register } from './pages/Register';
import { Dashboard } from './pages/Dashboard';
import { LiveMonitoring } from './pages/LiveMonitoring';
import { Recordings } from './pages/Recordings';
import { Events } from './pages/Events';
import { DailySummaryPage } from './pages/DailySummaryPage';
import { Analytics } from './pages/Analytics';
import { Settings } from './pages/Settings';
import { CameraStatus } from './types';
import { api } from './services/api';

const MainApplication: React.FC = () => {
  const { user, isLoading } = useAuth();
  const [authView, setAuthView] = useState<'login' | 'register'>('login');
  const [currentTab, setCurrentTab] = useState<NavTab>('overview');
  const [cameraStatus, setCameraStatus] = useState<CameraStatus | null>(null);

  // Poll camera status for global Navbar indicator
  useEffect(() => {
    if (!user) return;

    const pollCamera = async () => {
      try {
        const s = await api.getCameraStatus();
        setCameraStatus(s);
      } catch {}
    };

    pollCamera();
    const interval = setInterval(pollCamera, 3000);
    return () => clearInterval(interval);
  }, [user]);

  if (isLoading) {
    return (
      <div
        style={{
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: 'var(--bg-primary)',
          color: 'var(--text-muted)',
          fontSize: '0.9rem',
        }}
      >
        Initializing CCTV Intelligence System...
      </div>
    );
  }

  // If not authenticated, render Login / Register
  if (!user) {
    if (authView === 'register') {
      return <Register onSwitchToLogin={() => setAuthView('login')} />;
    }
    return <Login onSwitchToRegister={() => setAuthView('register')} />;
  }

  return (
    <div className="app-container">
      <Sidebar currentTab={currentTab} onSelectTab={setCurrentTab} />

      <div className="main-content">
        <Navbar cameraStatus={cameraStatus} />

        <main style={{ flex: 1, paddingBottom: '2rem' }}>
          {currentTab === 'overview' && (
            <Dashboard
              onNavigateToSummary={() => setCurrentTab('summaries')}
              onNavigateToLive={() => setCurrentTab('live')}
            />
          )}
          {currentTab === 'live' && <LiveMonitoring />}
          {currentTab === 'recordings' && <Recordings />}
          {currentTab === 'events' && <Events />}
          {currentTab === 'summaries' && <DailySummaryPage />}
          {currentTab === 'analytics' && <Analytics />}
          {currentTab === 'settings' && <Settings />}
        </main>
      </div>
    </div>
  );
};

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <MainApplication />
      </AuthProvider>
    </ThemeProvider>
  );
}
