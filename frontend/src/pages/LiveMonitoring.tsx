import React, { useState, useEffect } from 'react';
import { CameraStatus, CameraDevice } from '../types';
import { api } from '../services/api';
import { Video, Play, Square, Zap, Camera, Clock, Layers, ShieldCheck } from 'lucide-react';

export const LiveMonitoring: React.FC = () => {
  const [cameraStatus, setCameraStatus] = useState<CameraStatus | null>(null);
  const [devices, setDevices] = useState<CameraDevice[]>([]);
  const [selectedDeviceIndex, setSelectedDeviceIndex] = useState<number>(0);
  const [isSimulatedMotion, setIsSimulatedMotion] = useState<boolean>(false);

  useEffect(() => {
    api.getCameraDevices().then((devs) => {
      setDevices(devs);
      if (devs.length > 0) setSelectedDeviceIndex(devs[0].index);
    }).catch(() => {});

    const poll = async () => {
      try {
        const s = await api.getCameraStatus();
        setCameraStatus(s);
      } catch {}
    };

    poll();
    const interval = setInterval(poll, 1500);
    return () => clearInterval(interval);
  }, []);

  const handleStart = async () => {
    try {
      const resp = await api.startMonitoring(1, selectedDeviceIndex);
      setCameraStatus(resp.status);
    } catch (err: any) {
      alert(err.message || 'Failed to start camera.');
    }
  };

  const handleStop = async () => {
    try {
      const resp = await api.stopMonitoring();
      setCameraStatus(resp.status);
    } catch (err: any) {
      alert(err.message || 'Failed to stop camera.');
    }
  };

  const handleToggleMotion = async () => {
    const nextVal = !isSimulatedMotion;
    setIsSimulatedMotion(nextVal);
    await api.triggerSimulatedMotion(nextVal);
  };

  const formatSeconds = (sec: number) => {
    const h = Math.floor(sec / 3600);
    const m = Math.floor((sec % 3600) / 60);
    const s = Math.floor(sec % 60);
    return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  return (
    <div className="page-wrapper" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* Top Controls Bar */}
      <div className="card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0.85rem 1.25rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Camera size={18} style={{ color: 'var(--accent-blue)' }} />
            <select
              className="input"
              style={{ width: '280px', padding: '0.45rem 0.75rem', fontSize: '0.85rem' }}
              value={selectedDeviceIndex}
              onChange={(e) => setSelectedDeviceIndex(Number(e.target.value))}
            >
              {devices.map((d) => (
                <option key={d.index} value={d.index}>
                  {d.name} {d.index >= 0 ? `(Index ${d.index})` : ''}
                </option>
              ))}
            </select>
          </div>

          <div className="badge badge-active">
            {cameraStatus?.is_monitoring ? cameraStatus.activity_state : 'OFFLINE'}
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <button
            onClick={handleToggleMotion}
            className={`btn btn-sm ${isSimulatedMotion ? 'btn-danger' : 'btn-secondary'}`}
          >
            <Zap size={14} />
            <span>{isSimulatedMotion ? 'Active Motion Target ON' : 'Trigger Test Motion'}</span>
          </button>

          {cameraStatus?.is_monitoring ? (
            <button onClick={handleStop} className="btn btn-danger btn-sm">
              <Square size={14} />
              <span>Stop Stream</span>
            </button>
          ) : (
            <button onClick={handleStart} className="btn btn-primary btn-sm">
              <Play size={14} />
              <span>Start Stream</span>
            </button>
          )}
        </div>
      </div>

      {/* Main Full CCTV Video Canvas */}
      <div
        className="card"
        style={{
          padding: 0,
          overflow: 'hidden',
          backgroundColor: '#000000',
          position: 'relative',
          borderRadius: '0.625rem',
        }}
      >
        <div style={{ width: '100%', minHeight: '520px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          {cameraStatus?.is_monitoring ? (
            <img
              src={api.getLiveStreamUrl()}
              alt="Live Surveillance Video"
              style={{ width: '100%', maxHeight: '720px', objectFit: 'contain', display: 'block' }}
            />
          ) : (
            <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
              <Video size={56} style={{ margin: '0 auto 1.25rem', opacity: 0.35 }} />
              <h3 style={{ color: 'var(--text-primary)', marginBottom: '0.5rem', fontWeight: 600 }}>Camera Stream Inactive</h3>
              <p style={{ fontSize: '0.95rem', marginBottom: '1.5rem', maxWidth: '420px', margin: '0 auto 1.5rem' }}>
                Live camera monitoring is currently paused. Select a device above and click start to initiate live surveillance.
              </p>
              <button
                className="btn btn-primary"
                onClick={handleStart}
                style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', margin: '0 auto' }}
              >
                <Play size={16} /> Start Live Monitoring
              </button>
            </div>
          )}
        </div>

        {/* Real-time Telemetry Overlay Bar */}
        <div
          style={{
            position: 'absolute',
            bottom: 0,
            left: 0,
            right: 0,
            backgroundColor: 'rgba(15, 23, 42, 0.85)',
            backdropFilter: 'blur(6px)',
            borderTop: '1px solid var(--border-color)',
            padding: '0.65rem 1.25rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontSize: '0.8rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <Clock size={15} style={{ color: 'var(--text-muted)' }} />
              <span style={{ color: 'var(--text-muted)' }}>Uptime:</span>
              <strong style={{ fontFamily: 'var(--font-mono)' }}>{formatSeconds(cameraStatus?.uptime_seconds || 0)}</strong>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <span style={{ color: 'var(--text-muted)' }}>FPS:</span>
              <strong style={{ fontFamily: 'var(--font-mono)', color: '#38bdf8' }}>{cameraStatus?.current_fps?.toFixed(1) || 0}</strong>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <span style={{ color: 'var(--text-muted)' }}>Sampling Rate:</span>
              <strong style={{ fontFamily: 'var(--font-mono)', color: '#34d399' }}>{cameraStatus?.sampling_fps?.toFixed(1) || 2.0} FPS</strong>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
            <div>
              <span style={{ color: 'var(--text-muted)' }}>Motion: </span>
              <strong style={{ fontFamily: 'var(--font-mono)', color: (cameraStatus?.motion_score || 0) > 1.5 ? '#f87171' : '#34d399' }}>
                {(cameraStatus?.motion_score || 0).toFixed(1)}%
              </strong>
            </div>

            <div>
              <span style={{ color: 'var(--text-muted)' }}>Processed: </span>
              <strong style={{ fontFamily: 'var(--font-mono)' }}>{cameraStatus?.total_frames_processed?.toLocaleString() || 0}</strong>
            </div>

            <div>
              <span style={{ color: 'var(--text-muted)' }}>Saved: </span>
              <strong style={{ fontFamily: 'var(--font-mono)', color: '#38bdf8' }}>{cameraStatus?.total_frames_saved?.toLocaleString() || 0}</strong>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
