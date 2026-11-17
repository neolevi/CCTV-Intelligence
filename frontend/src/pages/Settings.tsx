import React, { useState, useEffect } from 'react';
import { SystemSettings, CameraDevice } from '../types';
import { api } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import { useTheme } from '../contexts/ThemeContext';
import {
  Settings as SettingsIcon,
  Camera,
  Eye,
  Sliders,
  HardDrive,
  Palette,
  User,
  Save,
  CheckCircle2,
  Lock,
} from 'lucide-react';

export const Settings: React.FC = () => {
  const { user, logout } = useAuth();
  const { theme, setTheme } = useTheme();

  const [settings, setSettings] = useState<SystemSettings | null>(null);
  const [devices, setDevices] = useState<CameraDevice[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Form states
  const [motionSensitivity, setMotionSensitivity] = useState<number>(25);
  const [motionThreshold, setMotionThreshold] = useState<number>(1.5);
  const [idleTimeout, setIdleTimeout] = useState<number>(5.0);
  const [deepIdleTimeout, setDeepIdleTimeout] = useState<number>(20.0);
  const [activeFps, setActiveFps] = useState<number>(5.0);
  const [idleFps, setIdleFps] = useState<number>(2.0);
  const [deepIdleFps, setDeepIdleFps] = useState<number>(1.0);
  const [retentionDays, setRetentionDays] = useState<number>(30);

  useEffect(() => {
    Promise.all([api.getSettings(), api.getCameraDevices()])
      .then(([s, d]) => {
        setSettings(s);
        setDevices(d);
        setMotionSensitivity(s.motion_sensitivity);
        setMotionThreshold(s.motion_threshold_percent);
        setIdleTimeout(s.idle_timeout_seconds);
        setDeepIdleTimeout(s.deep_idle_timeout_seconds);
        setActiveFps(s.active_sampling_fps);
        setIdleFps(s.idle_sampling_fps);
        setDeepIdleFps(s.deep_idle_sampling_fps);
        setRetentionDays(s.storage_retention_days);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setSuccessMsg(null);

    try {
      const updated = await api.updateSettings({
        motion_sensitivity: motionSensitivity,
        motion_threshold_percent: motionThreshold,
        idle_timeout_seconds: idleTimeout,
        deep_idle_timeout_seconds: deepIdleTimeout,
        active_sampling_fps: activeFps,
        idle_sampling_fps: idleFps,
        deep_idle_sampling_fps: deepIdleFps,
        storage_retention_days: retentionDays,
        theme: theme,
      });
      setSettings(updated);
      setSuccessMsg('Surveillance settings successfully applied and persisted.');
      setTimeout(() => setSuccessMsg(null), 4000);
    } catch (err: any) {
      alert(err.message || 'Failed to save settings.');
    } finally {
      setSaving(false);
    }
  };

  const usedGb = settings ? (settings.storage_used_bytes / (1024 ** 3)).toFixed(2) : '0';
  const freeGb = settings ? (settings.storage_free_bytes / (1024 ** 3)).toFixed(2) : '0';
  const totalGb = settings
    ? ((settings.storage_used_bytes + settings.storage_free_bytes) / (1024 ** 3)).toFixed(2)
    : '0';

  return (
    <div className="page-wrapper" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', maxWidth: '1000px' }}>
      {/* Header */}
      <div className="card" style={{ padding: '1rem 1.25rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
            <SettingsIcon size={22} style={{ color: 'var(--accent-blue)' }} />
            <div>
              <h2 style={{ fontSize: '1.15rem', fontWeight: 600 }}>System & Surveillance Settings</h2>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                Configure computer vision thresholds, adaptive sampling rates, and storage parameters
              </p>
            </div>
          </div>

          <button onClick={handleSave} disabled={saving} className="btn btn-primary btn-sm">
            <Save size={15} />
            <span>{saving ? 'Applying...' : 'Save Settings'}</span>
          </button>
        </div>
      </div>

      {successMsg && (
        <div
          style={{
            padding: '0.75rem 1rem',
            backgroundColor: 'rgba(16, 185, 129, 0.15)',
            border: '1px solid rgba(16, 185, 129, 0.3)',
            borderRadius: '0.45rem',
            color: '#34d399',
            fontSize: '0.85rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
          }}
        >
          <CheckCircle2 size={17} />
          <span>{successMsg}</span>
        </div>
      )}

      {loading ? (
        <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
          Loading system parameters...
        </div>
      ) : (
        <form onSubmit={handleSave} style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* Motion Detection Configuration */}
          <div className="card">
            <div className="card-header">
              <div className="card-title">
                <Sliders size={18} style={{ color: '#ef4444' }} />
                <span>Motion Detection Engine (OpenCV MOG2)</span>
              </div>
            </div>

            <div className="grid-2">
              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 500, marginBottom: '0.35rem' }}>
                  MOG2 Variance Sensitivity Threshold: <strong>{motionSensitivity}</strong>
                </label>
                <input
                  type="range"
                  min="5"
                  max="60"
                  step="1"
                  value={motionSensitivity}
                  onChange={(e) => setMotionSensitivity(Number(e.target.value))}
                  style={{ width: '100%' }}
                />
                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                  Lower values increase sensitivity to minute movements; higher values suppress noise.
                </span>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 500, marginBottom: '0.35rem' }}>
                  Motion Trigger Threshold (% of Frame): <strong>{motionThreshold}%</strong>
                </label>
                <input
                  type="range"
                  min="0.5"
                  max="10.0"
                  step="0.1"
                  value={motionThreshold}
                  onChange={(e) => setMotionThreshold(Number(e.target.value))}
                  style={{ width: '100%' }}
                />
                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                  Percentage of frame pixels required to trigger an ACTIVE recording state.
                </span>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 500, marginBottom: '0.35rem' }}>
                  Idle Transition Timeout (Seconds)
                </label>
                <input
                  type="number"
                  min="1"
                  max="60"
                  step="0.5"
                  className="input"
                  value={idleTimeout}
                  onChange={(e) => setIdleTimeout(Number(e.target.value))}
                />
                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                  Duration of stillness before stepping down from ACTIVE to IDLE.
                </span>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 500, marginBottom: '0.35rem' }}>
                  Deep Idle Timeout (Seconds)
                </label>
                <input
                  type="number"
                  min="10"
                  max="300"
                  step="1"
                  className="input"
                  value={deepIdleTimeout}
                  onChange={(e) => setDeepIdleTimeout(Number(e.target.value))}
                />
                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                  Duration before transitioning to ultra-low sampling DEEP IDLE.
                </span>
              </div>
            </div>
          </div>

          {/* Adaptive Sampling Rates */}
          <div className="card">
            <div className="card-header">
              <div className="card-title">
                <Eye size={18} style={{ color: 'var(--accent-blue)' }} />
                <span>Adaptive Frame Sampling Rates (FPS)</span>
              </div>
            </div>

            <div className="grid-3">
              <div style={{ backgroundColor: 'var(--bg-primary)', padding: '1rem', borderRadius: '0.5rem', border: '1px solid var(--border-color)' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                  <span className="badge badge-active">ACTIVE State</span>
                  <strong style={{ color: '#ef4444' }}>{activeFps} FPS</strong>
                </div>
                <input
                  type="range"
                  min="3"
                  max="15"
                  step="0.5"
                  value={activeFps}
                  onChange={(e) => setActiveFps(Number(e.target.value))}
                  style={{ width: '100%' }}
                />
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '0.35rem' }}>
                  Captures rich motion frames for evidence during verified movement.
                </div>
              </div>

              <div style={{ backgroundColor: 'var(--bg-primary)', padding: '1rem', borderRadius: '0.5rem', border: '1px solid var(--border-color)' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                  <span className="badge badge-idle">IDLE State</span>
                  <strong style={{ color: '#f59e0b' }}>{idleFps} FPS</strong>
                </div>
                <input
                  type="range"
                  min="1"
                  max="5"
                  step="0.5"
                  value={idleFps}
                  onChange={(e) => setIdleFps(Number(e.target.value))}
                  style={{ width: '100%' }}
                />
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '0.35rem' }}>
                  Standard baseline monitoring rate during calm periods.
                </div>
              </div>

              <div style={{ backgroundColor: 'var(--bg-primary)', padding: '1rem', borderRadius: '0.5rem', border: '1px solid var(--border-color)' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                  <span className="badge badge-deep-idle">DEEP IDLE</span>
                  <strong style={{ color: '#10b981' }}>{deepIdleFps} FPS</strong>
                </div>
                <input
                  type="range"
                  min="0.2"
                  max="2"
                  step="0.1"
                  value={deepIdleFps}
                  onChange={(e) => setDeepIdleFps(Number(e.target.value))}
                  style={{ width: '100%' }}
                />
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '0.35rem' }}>
                  Conserves up to 90% storage during extended dormant hours.
                </div>
              </div>
            </div>
          </div>

          {/* Storage & Disk Management */}
          <div className="card">
            <div className="card-header">
              <div className="card-title">
                <HardDrive size={18} style={{ color: '#06b6d4' }} />
                <span>Storage & Storage Retention</span>
              </div>
            </div>

            <div className="grid-2">
              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 500, marginBottom: '0.35rem' }}>
                  Storage Retention Policy (Days)
                </label>
                <input
                  type="number"
                  min="1"
                  max="365"
                  className="input"
                  value={retentionDays}
                  onChange={(e) => setRetentionDays(Number(e.target.value))}
                />
                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                  Recordings and keyframes older than this threshold will be pruned.
                </span>
              </div>

              <div>
                <div style={{ fontSize: '0.8rem', fontWeight: 500, marginBottom: '0.35rem' }}>
                  Physical Disk Utilization
                </div>
                <div
                  style={{
                    height: '10px',
                    backgroundColor: 'var(--bg-primary)',
                    borderRadius: '5px',
                    overflow: 'hidden',
                    border: '1px solid var(--border-color)',
                    marginTop: '0.5rem',
                  }}
                >
                  <div
                    style={{
                      height: '100%',
                      width: `${Math.min(100, (Number(usedGb) / (Number(totalGb) || 1)) * 100)}%`,
                      backgroundColor: 'var(--accent-blue)',
                    }}
                  />
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.4rem' }}>
                  <span>Used: {usedGb} GB</span>
                  <span>Free: {freeGb} GB</span>
                  <span>Total: {totalGb} GB</span>
                </div>
              </div>
            </div>
          </div>

          {/* Appearance & Account */}
          <div className="grid-2">
            {/* Appearance */}
            <div className="card">
              <div className="card-header">
                <div className="card-title">
                  <Palette size={18} style={{ color: 'var(--accent-blue)' }} />
                  <span>Appearance</span>
                </div>
              </div>

              <div style={{ display: 'flex', gap: '1rem' }}>
                <button
                  type="button"
                  onClick={() => setTheme('dark')}
                  className={`btn ${theme === 'dark' ? 'btn-primary' : 'btn-secondary'}`}
                  style={{ flex: 1 }}
                >
                  Dark Mode (Default)
                </button>
                <button
                  type="button"
                  onClick={() => setTheme('light')}
                  className={`btn ${theme === 'light' ? 'btn-primary' : 'btn-secondary'}`}
                  style={{ flex: 1 }}
                >
                  Light Mode
                </button>
              </div>
            </div>

            {/* Account */}
            <div className="card">
              <div className="card-header">
                <div className="card-title">
                  <User size={18} style={{ color: 'var(--accent-blue)' }} />
                  <span>Operator Profile</span>
                </div>
              </div>

              <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                <div><strong>Email:</strong> {user?.email}</div>
                <div style={{ marginTop: '0.25rem' }}><strong>Role:</strong> {user?.role}</div>
                <button
                  type="button"
                  onClick={logout}
                  className="btn btn-secondary btn-sm"
                  style={{ marginTop: '0.75rem', color: '#ef4444' }}
                >
                  Sign Out of Account
                </button>
              </div>
            </div>
          </div>
        </form>
      )}
    </div>
  );
};
