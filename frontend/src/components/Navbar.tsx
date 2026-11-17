import React from 'react';
import { Shield, Sun, Moon, LogOut, Video, Activity } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useTheme } from '../contexts/ThemeContext';
import { CameraStatus } from '../types';

interface NavbarProps {
  cameraStatus?: CameraStatus | null;
}

export const Navbar: React.FC<NavbarProps> = ({ cameraStatus }) => {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();

  const isMonitoring = cameraStatus?.is_monitoring;
  const activityState = cameraStatus?.activity_state || 'OFFLINE';

  const getBadgeClass = () => {
    if (!isMonitoring) return 'badge-offline';
    switch (activityState) {
      case 'ACTIVE':
        return 'badge-active';
      case 'IDLE':
        return 'badge-idle';
      case 'DEEP_IDLE':
        return 'badge-deep-idle';
      default:
        return 'badge-offline';
    }
  };

  return (
    <header
      style={{
        height: '64px',
        backgroundColor: 'var(--bg-secondary)',
        borderBottom: '1px solid var(--border-color)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 1.5rem',
        position: 'sticky',
        top: 0,
        zIndex: 40,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
        <div
          style={{
            width: '38px',
            height: '38px',
            borderRadius: '0.5rem',
            backgroundColor: 'rgba(59, 130, 246, 0.15)',
            border: '1px solid rgba(59, 130, 246, 0.3)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--accent-blue)',
          }}
        >
          <Shield size={22} />
        </div>
        <div>
          <h1 style={{ fontSize: '1.15rem', fontWeight: 700, letterSpacing: '-0.02em', color: 'var(--text-primary)' }}>
            CCTV <span style={{ color: 'var(--accent-blue)' }}>Intelligence</span>
          </h1>
          <p style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Motion-Adaptive Surveillance</p>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        {/* Live Status Pill */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
          <div className={`badge ${getBadgeClass()}`}>
            <span
              style={{
                width: '7px',
                height: '7px',
                borderRadius: '50%',
                backgroundColor: 'currentColor',
                display: 'inline-block',
              }}
            />
            {isMonitoring ? activityState : 'STANDBY'}
          </div>

          {cameraStatus?.sampling_fps && (
            <span
              style={{
                fontSize: '0.75rem',
                fontFamily: 'var(--font-mono)',
                color: 'var(--text-secondary)',
                backgroundColor: 'var(--bg-primary)',
                padding: '0.2rem 0.5rem',
                borderRadius: '0.35rem',
                border: '1px solid var(--border-color)',
              }}
            >
              {cameraStatus.sampling_fps.toFixed(1)} FPS
            </span>
          )}
        </div>

        {/* Theme Toggle */}
        <button
          onClick={toggleTheme}
          className="btn btn-secondary btn-sm"
          title={`Switch to ${theme === 'dark' ? 'Light' : 'Dark'} Mode`}
          style={{ padding: '0.45rem', borderRadius: '0.45rem' }}
        >
          {theme === 'dark' ? <Sun size={17} /> : <Moon size={17} />}
        </button>

        {/* User Info & Logout */}
        {user && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginLeft: '0.5rem' }}>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                {user.full_name || user.email}
              </div>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'capitalize' }}>
                {user.role}
              </div>
            </div>

            <button
              onClick={logout}
              className="btn btn-secondary btn-sm"
              title="Sign Out"
              style={{ color: '#ef4444' }}
            >
              <LogOut size={16} />
              <span>Logout</span>
            </button>
          </div>
        )}
      </div>
    </header>
  );
};
