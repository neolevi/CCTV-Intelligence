import React, { useState, useEffect } from 'react';
import { DailySummary, MotionEvent } from '../types';
import { api } from '../services/api';
import { Timeline24h } from '../components/Timeline24h';
import { ActivityChart } from '../components/ActivityChart';
import { EventDetailModal } from '../components/EventDetailModal';
import {
  FileText,
  Calendar,
  ChevronLeft,
  ChevronRight,
  Download,
  RotateCw,
  Sparkles,
  Clock,
  Layers,
  HardDrive,
  BellRing,
  ShieldCheck,
} from 'lucide-react';

export const DailySummaryPage: React.FC = () => {
  const [selectedDate, setSelectedDate] = useState<string>(() => {
    return new Date().toISOString().slice(0, 10);
  });
  const [summary, setSummary] = useState<DailySummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeEvent, setActiveEvent] = useState<MotionEvent | null>(null);

  const fetchSummary = async (dateStr: string) => {
    setLoading(true);
    try {
      const data = await api.getDailySummary(dateStr);
      setSummary(data);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSummary(selectedDate);
  }, [selectedDate]);

  const handlePrevDay = () => {
    const d = new Date(selectedDate);
    d.setDate(d.getDate() - 1);
    setSelectedDate(d.toISOString().slice(0, 10));
  };

  const handleNextDay = () => {
    const d = new Date(selectedDate);
    d.setDate(d.getDate() + 1);
    setSelectedDate(d.toISOString().slice(0, 10));
  };

  const handleRegenerate = async () => {
    setLoading(true);
    try {
      const refreshed = await api.generateDailySummary(selectedDate);
      setSummary(refreshed);
    } catch (err: any) {
      alert(err.message || 'Failed to regenerate summary.');
    } finally {
      setLoading(false);
    }
  };

  const formatSeconds = (sec: number) => {
    const h = Math.floor(sec / 3600);
    const m = Math.floor((sec % 3600) / 60);
    const s = Math.floor(sec % 60);
    if (h > 0) return `${h}h ${m}m ${s}s`;
    return `${m}m ${s}s`;
  };

  return (
    <div className="page-wrapper" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Date Navigation & Actions Header */}
      <div className="card" style={{ padding: '1rem 1.25rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
            <FileText size={22} style={{ color: 'var(--accent-blue)' }} />
            <div>
              <h2 style={{ fontSize: '1.15rem', fontWeight: 600 }}>Surveillance Daily Intelligence Summary</h2>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                Automated activity classification & surveillance report for {selectedDate}
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
            {/* Prev / Next Day controls */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
              <button onClick={handlePrevDay} className="btn btn-secondary btn-sm" title="Previous Day">
                <ChevronLeft size={16} />
              </button>
              <input
                type="date"
                className="input"
                style={{ padding: '0.4rem 0.65rem', fontSize: '0.85rem' }}
                value={selectedDate}
                onChange={(e) => setSelectedDate(e.target.value)}
              />
              <button onClick={handleNextDay} className="btn btn-secondary btn-sm" title="Next Day">
                <ChevronRight size={16} />
              </button>
            </div>

            <button onClick={handleRegenerate} className="btn btn-secondary btn-sm" title="Recalculate Summary">
              <RotateCw size={14} />
              <span>Regenerate</span>
            </button>

            <a
              href={api.getSummaryDownloadUrl(selectedDate)}
              download
              className="btn btn-primary btn-sm"
              style={{ textDecoration: 'none' }}
            >
              <Download size={14} />
              <span>Download Markdown Report</span>
            </a>
          </div>
        </div>
      </div>

      {loading ? (
        <div style={{ padding: '4rem', textAlign: 'center', color: 'var(--text-muted)' }}>
          Calculating daily intelligence metrics...
        </div>
      ) : summary ? (
        <>
          {/* Executive Narrative */}
          <div className="card" style={{ borderLeft: '4px solid var(--accent-blue)' }}>
            <div className="card-header" style={{ marginBottom: '0.5rem' }}>
              <div className="card-title">
                <Sparkles size={18} style={{ color: '#f59e0b' }} />
                <span>Executive Daily Surveillance Narrative</span>
              </div>
              <span className="badge badge-active">{summary.total_motion_events} Verified Events</span>
            </div>
            <p style={{ fontSize: '0.95rem', lineHeight: '1.7', color: 'var(--text-primary)' }}>
              {summary.narrative_summary}
            </p>
          </div>

          {/* Key Metrics Grid */}
          <div className="grid-4">
            <div className="card">
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Total Monitoring Time</div>
              <div style={{ fontSize: '1.35rem', fontWeight: 700, marginTop: '0.25rem' }}>
                {formatSeconds(summary.total_monitoring_seconds)}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
                Active: {formatSeconds(summary.active_seconds)}
              </div>
            </div>

            <div className="card">
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Idle & Deep Idle Time</div>
              <div style={{ fontSize: '1.35rem', fontWeight: 700, marginTop: '0.25rem', color: '#34d399' }}>
                {formatSeconds(summary.idle_seconds + summary.deep_idle_seconds)}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
                Adaptive 1-2 FPS
              </div>
            </div>

            <div className="card">
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Frames Evaluated & Saved</div>
              <div style={{ fontSize: '1.35rem', fontWeight: 700, marginTop: '0.25rem', color: '#38bdf8' }}>
                {summary.total_frames_saved.toLocaleString()}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
                Out of {summary.total_frames_captured.toLocaleString()} evaluated
              </div>
            </div>

            <div className="card">
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Storage Consumed</div>
              <div style={{ fontSize: '1.35rem', fontWeight: 700, marginTop: '0.25rem', color: '#06b6d4' }}>
                {(summary.storage_consumed_bytes / (1024 * 1024)).toFixed(2)} MB
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
                Peak Hour:{' '}
                {summary.peak_activity_hour !== null && summary.peak_activity_hour !== undefined
                  ? `${summary.peak_activity_hour}:00`
                  : 'N/A'}
              </div>
            </div>
          </div>

          {/* 24-Hour Timeline */}
          <Timeline24h segments={summary.timeline_segments} />

          {/* Hourly Distribution Chart */}
          <ActivityChart hourlyData={summary.hourly_distribution} />

          {/* Significant Events of the Day */}
          <div className="card">
            <div className="card-header">
              <div className="card-title">
                <BellRing size={18} style={{ color: '#ef4444' }} />
                <span>Significant Recorded Events of {selectedDate}</span>
              </div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                {summary.important_events.length} major event{summary.important_events.length !== 1 ? 's' : ''}
              </span>
            </div>

            {summary.important_events && summary.important_events.length > 0 ? (
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))',
                  gap: '1rem',
                }}
              >
                {summary.important_events.map((ev) => (
                  <div
                    key={ev.id}
                    onClick={() => setActiveEvent(ev)}
                    style={{
                      backgroundColor: 'var(--bg-primary)',
                      border: '1px solid var(--border-color)',
                      borderRadius: '0.5rem',
                      overflow: 'hidden',
                      cursor: 'pointer',
                    }}
                  >
                    <div style={{ height: '130px', backgroundColor: '#000000' }}>
                      {ev.thumbnail_path ? (
                        <img
                          src={api.getEventThumbnailUrl(ev.id)}
                          alt={`Event ${ev.id}`}
                          style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                        />
                      ) : (
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-muted)' }}>
                          <BellRing size={28} />
                        </div>
                      )}
                    </div>
                    <div style={{ padding: '0.75rem' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontWeight: 600, fontSize: '0.85rem' }}>Event #{ev.id}</span>
                        <span style={{ color: '#f87171', fontWeight: 700, fontSize: '0.8rem' }}>
                          {ev.peak_motion_score.toFixed(1)}% Peak
                        </span>
                      </div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                        {new Date(ev.start_time).toLocaleTimeString()} ({ev.frame_count} frames)
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                No significant motion events logged for this date.
              </div>
            )}
          </div>
        </>
      ) : (
        <div className="card" style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
          No surveillance records found for {selectedDate}.
        </div>
      )}

      {/* Modal */}
      <EventDetailModal event={activeEvent} onClose={() => setActiveEvent(null)} />
    </div>
  );
};
