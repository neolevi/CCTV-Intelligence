import React, { useState, useEffect } from 'react';
import {
  CameraStatus,
  DailySummary,
  MotionEvent,
  Recording,
  CameraDevice,
} from '../types';
import { api } from '../services/api';
import { Timeline24h } from '../components/Timeline24h';
import { ActivityChart } from '../components/ActivityChart';
import { VideoPlayerModal } from '../components/VideoPlayerModal';
import { EventDetailModal } from '../components/EventDetailModal';
import {
  Video,
  Play,
  Square,
  Clock,
  BellRing,
  HardDrive,
  Layers,
  Sparkles,
  Download,
  Maximize2,
  Zap,
  Film,
  ExternalLink,
} from 'lucide-react';

interface DashboardProps {
  onNavigateToSummary: () => void;
  onNavigateToLive: () => void;
}

export const Dashboard: React.FC<DashboardProps> = ({
  onNavigateToSummary,
  onNavigateToLive,
}) => {
  const [cameraStatus, setCameraStatus] = useState<CameraStatus | null>(null);
  const [devices, setDevices] = useState<CameraDevice[]>([]);
  const [selectedDeviceIndex, setSelectedDeviceIndex] = useState<number>(0);
  const [dailySummary, setDailySummary] = useState<DailySummary | null>(null);
  const [recentEvents, setRecentEvents] = useState<MotionEvent[]>([]);
  const [recentRecordings, setRecentRecordings] = useState<Recording[]>([]);
  const [isSimulatedMotion, setIsSimulatedMotion] = useState<boolean>(false);

  // Modals
  const [activeRecording, setActiveRecording] = useState<Recording | null>(null);
  const [activeEvent, setActiveEvent] = useState<MotionEvent | null>(null);

  const fetchSummary = async () => {
    try {
      const summary = await api.getDailySummary();
      setDailySummary(summary);
    } catch {
      // transient network error
    }
  };

  // Fetch initial data & periodic refresh
  useEffect(() => {
    // 1. Fetch available devices
    api.getCameraDevices().then((devs) => {
      setDevices(devs);
      if (devs.length > 0) {
        setSelectedDeviceIndex(devs[0].index);
      }
    }).catch(() => {});

    // 2. Initial summary load
    fetchSummary();

    // 3. Fast telemetry refresh (camera status, recent events & recordings)
    const refreshData = async () => {
      try {
        const [status, events, recordings] = await Promise.all([
          api.getCameraStatus(),
          api.listEvents({ limit: 6 }),
          api.listRecordings({ limit: 6 }),
        ]);
        setCameraStatus(status);
        setRecentEvents(events);
        setRecentRecordings(recordings);
      } catch (err) {
        // handle or ignore transient network error
      }
    };

    refreshData();
    const telemetryInterval = setInterval(refreshData, 3000); // 3-second polling for live status only
    const summaryInterval = setInterval(fetchSummary, 60000); // 60-second polling for daily summary (avoids 3s re-writes)

    return () => {
      clearInterval(telemetryInterval);
      clearInterval(summaryInterval);
    };
  }, []);

  const handleStartMonitoring = async () => {
    try {
      const resp = await api.startMonitoring(1, selectedDeviceIndex);
      setCameraStatus(resp.status);
      setTimeout(fetchSummary, 1000);
    } catch (err: any) {
      alert(err.message || 'Failed to start camera monitoring.');
    }
  };

  const handleStopMonitoring = async () => {
    try {
      const resp = await api.stopMonitoring();
      setCameraStatus(resp.status);
      setTimeout(fetchSummary, 1000);
    } catch (err: any) {
      alert(err.message || 'Failed to stop camera monitoring.');
    }
  };

  const handleToggleSimulatedMotion = async () => {
    const nextVal = !isSimulatedMotion;
    setIsSimulatedMotion(nextVal);
    await api.triggerSimulatedMotion(nextVal);
  };

  const formatSeconds = (sec: number) => {
    const h = Math.floor(sec / 3600);
    const m = Math.floor((sec % 3600) / 60);
    const s = Math.floor(sec % 60);
    if (h > 0) return `${h}h ${m}m ${s}s`;
    return `${m}m ${s}s`;
  };

  const formatStorageMb = (bytes: number) => {
    return (bytes / (1024 * 1024)).toFixed(1);
  };

  return (
    <div className="page-wrapper" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* 1. TOP SECTION: KPI STAT CARDS */}
      <div className="grid-4">
        {/* State Card */}
        <div className="stat-card">
          <div
            className="stat-icon-wrapper"
            style={{
              backgroundColor:
                cameraStatus?.activity_state === 'ACTIVE'
                  ? 'rgba(239, 68, 68, 0.15)'
                  : cameraStatus?.activity_state === 'IDLE'
                  ? 'rgba(245, 158, 11, 0.15)'
                  : 'rgba(16, 185, 129, 0.15)',
              color:
                cameraStatus?.activity_state === 'ACTIVE'
                  ? '#ef4444'
                  : cameraStatus?.activity_state === 'IDLE'
                  ? '#f59e0b'
                  : '#10b981',
            }}
          >
            <Zap size={22} />
          </div>
          <div>
            <div className="stat-label">Activity Classification</div>
            <div className="stat-value" style={{ fontSize: '1.25rem' }}>
              {cameraStatus?.is_monitoring ? cameraStatus.activity_state : 'STANDBY'}
            </div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
              Rate: {cameraStatus?.sampling_fps?.toFixed(1) || 2.0} FPS
            </div>
          </div>
        </div>

        {/* Uptime Card */}
        <div className="stat-card">
          <div
            className="stat-icon-wrapper"
            style={{ backgroundColor: 'rgba(59, 130, 246, 0.15)', color: 'var(--accent-blue)' }}
          >
            <Clock size={22} />
          </div>
          <div>
            <div className="stat-label">Monitoring Duration</div>
            <div className="stat-value">
              {formatSeconds(cameraStatus?.uptime_seconds || 0)}
            </div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
              {cameraStatus?.current_fps?.toFixed(1) || 0} Native FPS
            </div>
          </div>
        </div>

        {/* Motion Events Card */}
        <div className="stat-card">
          <div
            className="stat-icon-wrapper"
            style={{ backgroundColor: 'rgba(239, 68, 68, 0.15)', color: '#ef4444' }}
          >
            <BellRing size={22} />
          </div>
          <div>
            <div className="stat-label">Motion Events Today</div>
            <div className="stat-value">
              {dailySummary?.total_motion_events || 0}
            </div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
              Peak Motion: {cameraStatus?.motion_score?.toFixed(1) || 0}%
            </div>
          </div>
        </div>

        {/* Storage Consumed Card */}
        <div className="stat-card">
          <div
            className="stat-icon-wrapper"
            style={{ backgroundColor: 'rgba(6, 182, 212, 0.15)', color: '#06b6d4' }}
          >
            <HardDrive size={22} />
          </div>
          <div>
            <div className="stat-label">Storage Consumed</div>
            <div className="stat-value">
              {formatStorageMb(dailySummary?.storage_consumed_bytes || 0)} MB
            </div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
              {dailySummary?.total_frames_saved || 0} Adaptive Frames Saved
            </div>
          </div>
        </div>
      </div>

      {/* 2. MAIN SECTION: LIVE CAMERA PREVIEW & PROMINENT DAILY SUMMARY */}
      <div className="grid-2">
        {/* Left Column: Live Camera Preview & Controls */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column' }}>
          <div className="card-header">
            <div className="card-title">
              <Video size={18} style={{ color: 'var(--accent-blue)' }} />
              <span>Live Surveillance Feed</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span className={`badge ${cameraStatus?.is_monitoring ? 'badge-active' : 'badge-offline'}`}>
                {cameraStatus?.is_monitoring ? 'LIVE' : 'OFFLINE'}
              </span>
              <button
                onClick={onNavigateToLive}
                className="btn btn-secondary btn-sm"
                title="Expand Full View"
                style={{ padding: '0.35rem' }}
              >
                <Maximize2 size={15} />
              </button>
            </div>
          </div>

          {/* Live Video Surface */}
          <div
            style={{
              position: 'relative',
              width: '100%',
              backgroundColor: '#000000',
              borderRadius: '0.5rem',
              overflow: 'hidden',
              aspectRatio: '4 / 3',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              border: '1px solid var(--border-color)',
            }}
          >
            {cameraStatus?.is_monitoring ? (
              <img
                src={api.getLiveStreamUrl()}
                alt="CCTV Surveillance Stream"
                style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
                onError={(e) => {
                  // If stream reconnecting
                }}
              />
            ) : (
              <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                <Video size={48} style={{ margin: '0 auto 1rem', opacity: 0.4 }} />
                <h4 style={{ color: 'var(--text-primary)', marginBottom: '0.5rem', fontWeight: 600 }}>Surveillance Standby</h4>
                <p style={{ fontSize: '0.875rem', marginBottom: '1.25rem' }}>Camera monitoring is currently inactive.</p>
                <button
                  className="btn btn-primary"
                  onClick={handleStartMonitoring}
                  style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', margin: '0 auto' }}
                >
                  <Play size={16} /> Start Live Monitoring
                </button>
              </div>
            )}

            {/* Motion Intensity Gauge Overlay */}
            {cameraStatus?.is_monitoring && (
              <div
                style={{
                  position: 'absolute',
                  bottom: '10px',
                  left: '10px',
                  right: '10px',
                  backgroundColor: 'rgba(15, 23, 42, 0.75)',
                  backdropFilter: 'blur(4px)',
                  padding: '0.4rem 0.75rem',
                  borderRadius: '0.35rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.75rem',
                }}
              >
                <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', fontWeight: 600 }}>
                  MOTION SCORE:
                </span>
                <div
                  style={{
                    flex: 1,
                    height: '6px',
                    backgroundColor: 'rgba(255, 255, 255, 0.15)',
                    borderRadius: '3px',
                    overflow: 'hidden',
                  }}
                >
                  <div
                    style={{
                      height: '100%',
                      width: `${Math.min(100, (cameraStatus.motion_score || 0) * 10)}%`,
                      backgroundColor: cameraStatus.motion_score > 1.5 ? '#ef4444' : '#10b981',
                      transition: 'width 0.2s',
                    }}
                  />
                </div>
                <span style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', fontWeight: 700 }}>
                  {(cameraStatus.motion_score || 0).toFixed(1)}%
                </span>
              </div>
            )}
          </div>

          {/* Controls Toolbar */}
          <div style={{ marginTop: '1rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <select
                className="input"
                style={{ flex: 1 }}
                value={selectedDeviceIndex}
                onChange={(e) => setSelectedDeviceIndex(Number(e.target.value))}
              >
                {devices.map((d) => (
                  <option key={d.index} value={d.index}>
                    {d.name} {d.index >= 0 ? `(Dev ${d.index})` : ''}
                  </option>
                ))}
              </select>

              {cameraStatus?.is_monitoring ? (
                <button onClick={handleStopMonitoring} className="btn btn-danger">
                  <Square size={16} />
                  <span>Stop Monitoring</span>
                </button>
              ) : (
                <button onClick={handleStartMonitoring} className="btn btn-primary">
                  <Play size={16} />
                  <span>Start Monitoring</span>
                </button>
              )}
            </div>

            {/* Test Simulation Controls */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '0.5rem 0.75rem',
                backgroundColor: 'var(--bg-primary)',
                borderRadius: '0.45rem',
                fontSize: '0.8rem',
              }}
            >
              <span style={{ color: 'var(--text-muted)' }}>Interactive Test:</span>
              <button
                onClick={handleToggleSimulatedMotion}
                className={`btn btn-sm ${isSimulatedMotion ? 'btn-danger' : 'btn-secondary'}`}
              >
                <Zap size={14} />
                <span>{isSimulatedMotion ? 'Reset Motion Target' : 'Inject Motion Event'}</span>
              </button>
            </div>
          </div>
        </div>

        {/* Right Column: TODAY'S DAILY SURVEILLANCE SUMMARY (PROMINENT CORE FEATURE) */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column' }}>
          <div className="card-header">
            <div className="card-title">
              <Sparkles size={18} style={{ color: '#f59e0b' }} />
              <span>Today's Daily Surveillance Summary</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <a
                href={api.getSummaryDownloadUrl(dailySummary?.date || new Date().toISOString().slice(0, 10))}
                className="btn btn-secondary btn-sm"
                title="Download Summary Report (.md)"
              >
                <Download size={14} />
                <span>Report</span>
              </a>
              <button
                onClick={onNavigateToSummary}
                className="btn btn-secondary btn-sm"
                title="View Full Daily Summary Details"
              >
                <ExternalLink size={14} />
                <span>Full View</span>
              </button>
            </div>
          </div>

          {/* Narrative Summary Block */}
          <div
            style={{
              padding: '1rem',
              backgroundColor: 'var(--bg-primary)',
              borderRadius: '0.5rem',
              border: '1px solid var(--border-color)',
              marginBottom: '1rem',
              borderLeft: '4px solid var(--accent-blue)',
            }}
          >
            <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--accent-blue)', marginBottom: '0.35rem', textTransform: 'uppercase' }}>
              Surveillance Narrative ({dailySummary?.date || 'Today'})
            </div>
            <p style={{ fontSize: '0.875rem', lineHeight: '1.6', color: 'var(--text-primary)' }}>
              {dailySummary?.narrative_summary ||
                'Monitoring session is actively analyzing the live surveillance feed. Automated narrative synthesis will update dynamically.'}
            </p>
          </div>

          {/* Key Summary Breakdown Chips */}
          <div className="grid-2" style={{ gap: '0.75rem', flex: 1 }}>
            <div style={{ backgroundColor: 'var(--bg-primary)', padding: '0.75rem', borderRadius: '0.45rem', border: '1px solid var(--border-color)' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Active Surveillance Time</div>
              <div style={{ fontSize: '1.05rem', fontWeight: 700, color: '#f87171', marginTop: '0.2rem' }}>
                {formatSeconds(dailySummary?.active_seconds || 0)}
              </div>
            </div>

            <div style={{ backgroundColor: 'var(--bg-primary)', padding: '0.75rem', borderRadius: '0.45rem', border: '1px solid var(--border-color)' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Idle / Deep Idle Time</div>
              <div style={{ fontSize: '1.05rem', fontWeight: 700, color: '#34d399', marginTop: '0.2rem' }}>
                {formatSeconds((dailySummary?.idle_seconds || 0) + (dailySummary?.deep_idle_seconds || 0))}
              </div>
            </div>

            <div style={{ backgroundColor: 'var(--bg-primary)', padding: '0.75rem', borderRadius: '0.45rem', border: '1px solid var(--border-color)' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>First / Last Detected Motion</div>
              <div style={{ fontSize: '0.8rem', fontWeight: 600, marginTop: '0.2rem' }}>
                {dailySummary?.first_activity_time ? new Date(dailySummary.first_activity_time).toLocaleTimeString() : 'None'}
                {' → '}
                {dailySummary?.last_activity_time ? new Date(dailySummary.last_activity_time).toLocaleTimeString() : 'None'}
              </div>
            </div>

            <div style={{ backgroundColor: 'var(--bg-primary)', padding: '0.75rem', borderRadius: '0.45rem', border: '1px solid var(--border-color)' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Peak Activity Window</div>
              <div style={{ fontSize: '1.05rem', fontWeight: 700, color: '#fbbf24', marginTop: '0.2rem' }}>
                {dailySummary?.peak_activity_hour !== null && dailySummary?.peak_activity_hour !== undefined
                  ? `${dailySummary.peak_activity_hour.toString().padStart(2, '0')}:00 - ${(dailySummary.peak_activity_hour + 1).toString().padStart(2, '0')}:00`
                  : 'No motion detected'}
              </div>
            </div>
          </div>

          <div style={{ marginTop: '1rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            <span>Deterministic Analysis Engine</span>
            <span>Refreshed in real-time</span>
          </div>
        </div>
      </div>

      {/* 3. BOTTOM SECTION: 24-HOUR TIMELINE & HOURLY CHART */}
      <Timeline24h segments={dailySummary?.timeline_segments || []} />

      <div className="grid-2">
        {/* Hourly Chart */}
        <ActivityChart
          hourlyData={dailySummary?.hourly_distribution || []}
          title="Hourly Motion Activity Distribution"
        />

        {/* Recent Events Table */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">
              <BellRing size={18} style={{ color: '#ef4444' }} />
              <span>Recent Motion Events</span>
            </div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              {recentEvents.length} recorded
            </span>
          </div>

          {recentEvents.length > 0 ? (
            <div style={{ overflowX: 'auto' }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Time</th>
                    <th>Activity</th>
                    <th>Peak Motion</th>
                    <th>Frames</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {recentEvents.map((ev) => (
                    <tr key={ev.id}>
                      <td>{new Date(ev.start_time).toLocaleTimeString()}</td>
                      <td>
                        <span className="badge badge-active">{ev.activity_state}</span>
                      </td>
                      <td style={{ color: '#f87171', fontWeight: 600 }}>{ev.peak_motion_score.toFixed(1)}%</td>
                      <td>{ev.frame_count}</td>
                      <td>
                        <button
                          onClick={() => setActiveEvent(ev)}
                          className="btn btn-secondary btn-sm"
                          style={{ padding: '0.2rem 0.5rem' }}
                        >
                          View
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
              No motion events recorded yet.
            </div>
          )}
        </div>
      </div>

      {/* Recent Recordings Row */}
      <div className="card">
        <div className="card-header">
          <div className="card-title">
            <Film size={18} style={{ color: 'var(--accent-blue)' }} />
            <span>Recent Video Clips</span>
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Playable surveillance recordings
          </span>
        </div>

        {recentRecordings.length > 0 ? (
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
              gap: '1rem',
            }}
          >
            {recentRecordings.map((rec) => (
              <div
                key={rec.id}
                onClick={() => setActiveRecording(rec)}
                style={{
                  backgroundColor: 'var(--bg-primary)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '0.5rem',
                  overflow: 'hidden',
                  cursor: 'pointer',
                  transition: 'transform 0.15s, border-color 0.15s',
                }}
              >
                <div style={{ position: 'relative', height: '120px', backgroundColor: '#000000' }}>
                  {rec.thumbnail_path ? (
                    <img
                      src={api.getRecordingThumbnailUrl(rec.id)}
                      alt={`Recording ${rec.id}`}
                      style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                    />
                  ) : (
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-muted)' }}>
                      <Film size={28} />
                    </div>
                  )}
                  <div
                    style={{
                      position: 'absolute',
                      bottom: '6px',
                      right: '6px',
                      backgroundColor: 'rgba(0,0,0,0.7)',
                      padding: '0.15rem 0.4rem',
                      borderRadius: '0.25rem',
                      fontSize: '0.7rem',
                      fontFamily: 'var(--font-mono)',
                    }}
                  >
                    {rec.duration_seconds.toFixed(1)}s
                  </div>
                </div>

                <div style={{ padding: '0.65rem 0.75rem' }}>
                  <div style={{ fontSize: '0.8rem', fontWeight: 600 }}>Recording #{rec.id}</div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                    {new Date(rec.start_time).toLocaleString()}
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
            No video recordings generated yet.
          </div>
        )}
      </div>

      {/* Modals */}
      <VideoPlayerModal recording={activeRecording} onClose={() => setActiveRecording(null)} />
      <EventDetailModal event={activeEvent} onClose={() => setActiveEvent(null)} />
    </div>
  );
};
