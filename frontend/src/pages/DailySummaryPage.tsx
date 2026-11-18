import React, { useState, useEffect, useMemo } from 'react';
import { DailySummary, MotionEvent, DailySummaryDateItem } from '../types';
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
  History,
  Image as ImageIcon,
  Eye,
  SlidersHorizontal,
  Flame,
  CheckCircle2,
} from 'lucide-react';

export const DailySummaryPage: React.FC = () => {
  const [selectedDate, setSelectedDate] = useState<string>(() => {
    return new Date().toISOString().slice(0, 10);
  });
  const [summary, setSummary] = useState<DailySummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeEvent, setActiveEvent] = useState<MotionEvent | null>(null);
  const [availableDates, setAvailableDates] = useState<DailySummaryDateItem[]>([]);
  const [showHistoryDrawer, setShowHistoryDrawer] = useState<boolean>(false);
  const [filterMode, setFilterMode] = useState<'all' | 'high_motion' | 'long_duration'>('all');
  const [sortOrder, setSortOrder] = useState<'time_desc' | 'time_asc' | 'motion_desc'>('time_desc');

  const fetchDates = async () => {
    try {
      const dates = await api.getAvailableSummaryDates();
      setAvailableDates(dates);
    } catch {
      // ignore
    }
  };

  const fetchSummary = async (dateStr: string) => {
    setLoading(true);
    try {
      const data = await api.getDailySummary(dateStr);
      setSummary(data);
    } catch {
      setSummary(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDates();
  }, []);

  useEffect(() => {
    fetchSummary(selectedDate);
  }, [selectedDate]);

  const handlePrevDay = () => {
    const d = new Date(selectedDate);
    d.setDate(d.getDate() - 1);
    setSelectedDate(d.toISOString().slice(0, 10));
  };

  const handleNextDay = () => {
    if (selectedDate >= todayStr) return;
    const d = new Date(selectedDate);
    d.setDate(d.getDate() + 1);
    const nextStr = d.toISOString().slice(0, 10);
    if (nextStr <= todayStr) {
      setSelectedDate(nextStr);
    }
  };

  const handleRegenerate = async () => {
    setLoading(true);
    try {
      const refreshed = await api.generateDailySummary(selectedDate);
      setSummary(refreshed);
      fetchDates();
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

  const formatTimestamp = (dateStr: string) => {
    try {
      const d = new Date(dateStr);
      return {
        time: d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
        date: d.toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' }),
      };
    } catch {
      return { time: dateStr, date: '' };
    }
  };

  const getEventDuration = (start: string, end?: string) => {
    if (!end) return null;
    const s = new Date(start).getTime();
    const e = new Date(end).getTime();
    const diffSec = Math.max(0, Math.round((e - s) / 1000));
    return `${diffSec}s`;
  };

  // Combine and sort events
  const allEvents = useMemo(() => {
    if (!summary) return [];
    const source = summary.events && summary.events.length > 0 ? summary.events : summary.important_events || [];
    let filtered = [...source];

    if (filterMode === 'high_motion') {
      filtered = filtered.filter((ev) => ev.peak_motion_score >= 40);
    } else if (filterMode === 'long_duration') {
      filtered = filtered.filter((ev) => {
        if (!ev.end_time) return false;
        const diff = (new Date(ev.end_time).getTime() - new Date(ev.start_time).getTime()) / 1000;
        return diff >= 15;
      });
    }

    if (sortOrder === 'time_desc') {
      filtered.sort((a, b) => new Date(b.start_time).getTime() - new Date(a.start_time).getTime());
    } else if (sortOrder === 'time_asc') {
      filtered.sort((a, b) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime());
    } else if (sortOrder === 'motion_desc') {
      filtered.sort((a, b) => (b.peak_motion_score || 0) - (a.peak_motion_score || 0));
    }

    return filtered;
  }, [summary, filterMode, sortOrder]);

  const todayStr = useMemo(() => new Date().toISOString().slice(0, 10), []);
  const isToday = selectedDate === todayStr;

  const pastAvailableDates = useMemo(() => {
    return availableDates.filter((item) => item.date <= todayStr);
  }, [availableDates, todayStr]);

  return (
    <div className="page-wrapper" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* 1. Header & Navigation Controls */}
      <div className="card" style={{ padding: '1rem 1.25rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
            <FileText size={24} style={{ color: 'var(--accent-blue)' }} />
            <div>
              <h2 style={{ fontSize: '1.2rem', fontWeight: 600 }}>Surveillance Daily Intelligence Summary</h2>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                Activity classification, snapshot gallery & surveillance report for {selectedDate} {isToday && '(Today)'}
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', flexWrap: 'wrap' }}>
            {/* Quick history toggle */}
            <button
              onClick={() => setShowHistoryDrawer(!showHistoryDrawer)}
              className={`btn btn-sm ${showHistoryDrawer ? 'btn-primary' : 'btn-secondary'}`}
              title="Browse previous days surveillance summaries"
            >
              <History size={15} />
              <span>Previous Days ({pastAvailableDates.length})</span>
            </button>

            {/* Date Picker & Prev/Next (restricted to past dates & today) */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
              <button onClick={handlePrevDay} className="btn btn-secondary btn-sm" title="Previous Day">
                <ChevronLeft size={16} />
              </button>
              <input
                type="date"
                className="input"
                style={{ padding: '0.35rem 0.65rem', fontSize: '0.85rem' }}
                value={selectedDate}
                max={todayStr}
                onChange={(e) => {
                  const val = e.target.value;
                  if (!val) return;
                  if (val > todayStr) {
                    setSelectedDate(todayStr);
                  } else {
                    setSelectedDate(val);
                  }
                }}
              />
              <button
                onClick={handleNextDay}
                disabled={selectedDate >= todayStr}
                className="btn btn-secondary btn-sm"
                title={selectedDate >= todayStr ? 'Future dates are disabled' : 'Next Day'}
                style={selectedDate >= todayStr ? { opacity: 0.35, cursor: 'not-allowed' } : {}}
              >
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
              <span>Download Report</span>
            </a>
          </div>
        </div>

        {/* 2. Previous Days Quick-Select Bar (strictly past dates & today) */}
        <div style={{ marginTop: '0.85rem', paddingTop: '0.85rem', borderTop: '1px solid var(--border-color)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', overflowX: 'auto', paddingBottom: '0.25rem' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
              Jump to Day:
            </span>
            {pastAvailableDates.slice(0, 10).map((item) => {
              const isSelected = item.date === selectedDate;
              const isDateToday = item.date === todayStr;
              let label = item.date;
              if (isDateToday) label = 'Today';
              else {
                const parts = item.date.split('-');
                if (parts.length === 3) {
                  label = `${parts[1]}/${parts[2]}`;
                }
              }

              return (
                <button
                  key={item.date}
                  onClick={() => setSelectedDate(item.date)}
                  style={{
                    padding: '0.3rem 0.65rem',
                    borderRadius: '0.35rem',
                    fontSize: '0.75rem',
                    fontWeight: isSelected ? 600 : 400,
                    border: isSelected ? '1px solid var(--accent-blue)' : '1px solid var(--border-color)',
                    backgroundColor: isSelected ? 'var(--accent-blue-subtle, rgba(59, 130, 246, 0.15))' : 'var(--bg-primary)',
                    color: isSelected ? 'var(--accent-blue)' : 'var(--text-primary)',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.35rem',
                    whiteSpace: 'nowrap',
                  }}
                >
                  <Calendar size={12} />
                  <span>{label}</span>
                  {item.total_events > 0 && (
                    <span
                      style={{
                        backgroundColor: isSelected ? 'var(--accent-blue)' : 'var(--border-color)',
                        color: isSelected ? '#ffffff' : 'var(--text-muted)',
                        borderRadius: '0.25rem',
                        padding: '0.05rem 0.3rem',
                        fontSize: '0.65rem',
                        fontWeight: 700,
                      }}
                    >
                      {item.total_events}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* 3. Collapsible Previous Days Archive Drawer */}
        {showHistoryDrawer && (
          <div
            style={{
              marginTop: '1rem',
              padding: '1rem',
              backgroundColor: 'var(--bg-primary)',
              borderRadius: '0.5rem',
              border: '1px solid var(--border-color)',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <History size={16} style={{ color: 'var(--accent-blue)' }} />
                <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>Archived Daily Surveillance History</span>
              </div>
              <button
                onClick={() => setShowHistoryDrawer(false)}
                className="btn btn-secondary btn-sm"
                style={{ fontSize: '0.75rem', padding: '0.2rem 0.5rem' }}
              >
                Close Drawer
              </button>
            </div>

            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
                gap: '0.65rem',
                maxHeight: '220px',
                overflowY: 'auto',
                paddingRight: '0.25rem',
              }}
            >
              {pastAvailableDates.map((item) => {
                const isSelected = item.date === selectedDate;
                return (
                  <div
                    key={item.date}
                    onClick={() => {
                      setSelectedDate(item.date);
                      setShowHistoryDrawer(false);
                    }}
                    style={{
                      padding: '0.65rem',
                      borderRadius: '0.4rem',
                      border: isSelected ? '1px solid var(--accent-blue)' : '1px solid var(--border-color)',
                      backgroundColor: isSelected ? 'rgba(59, 130, 246, 0.1)' : 'var(--bg-secondary)',
                      cursor: 'pointer',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '0.25rem',
                      transition: 'border-color 0.15s ease',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontWeight: 600, fontSize: '0.85rem', color: isSelected ? 'var(--accent-blue)' : 'inherit' }}>
                        {item.date}
                      </span>
                      <span
                        className="badge"
                        style={{
                          fontSize: '0.7rem',
                          backgroundColor: item.total_events > 0 ? 'rgba(239, 68, 68, 0.15)' : 'rgba(100, 116, 139, 0.15)',
                          color: item.total_events > 0 ? '#ef4444' : 'var(--text-muted)',
                        }}
                      >
                        {item.total_events} event{item.total_events !== 1 ? 's' : ''}
                      </span>
                    </div>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                      Active: {formatSeconds(item.active_seconds)} • Monitored: {formatSeconds(item.total_monitoring_seconds)}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {loading ? (
        <div className="card" style={{ padding: '4rem', textAlign: 'center', color: 'var(--text-muted)' }}>
          <div style={{ display: 'inline-block', marginBottom: '0.75rem' }}>
            <RotateCw size={24} className="spin" style={{ color: 'var(--accent-blue)' }} />
          </div>
          <div>Calculating daily intelligence metrics and compiling event gallery for {selectedDate}...</div>
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

          {/* 4. Event Snapshots & Images Gallery for this Day */}
          <div className="card">
            <div className="card-header" style={{ flexWrap: 'wrap', gap: '0.75rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.75rem', marginBottom: '1rem' }}>
              <div className="card-title">
                <ImageIcon size={19} style={{ color: '#ef4444' }} />
                <span>Event Footage & Surveillance Snapshots for {selectedDate}</span>
                <span className="badge" style={{ backgroundColor: 'rgba(239, 68, 68, 0.12)', color: '#ef4444', marginLeft: '0.5rem' }}>
                  {allEvents.length} Event{allEvents.length !== 1 ? 's' : ''}
                </span>
              </div>

              {/* Filters and Sorting Controls */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                  <button
                    onClick={() => setFilterMode('all')}
                    className={`btn btn-sm ${filterMode === 'all' ? 'btn-primary' : 'btn-secondary'}`}
                    style={{ fontSize: '0.75rem', padding: '0.25rem 0.55rem' }}
                  >
                    All ({summary.events?.length || summary.important_events?.length || 0})
                  </button>
                  <button
                    onClick={() => setFilterMode('high_motion')}
                    className={`btn btn-sm ${filterMode === 'high_motion' ? 'btn-primary' : 'btn-secondary'}`}
                    style={{ fontSize: '0.75rem', padding: '0.25rem 0.55rem' }}
                  >
                    High Motion &gt;40%
                  </button>
                  <button
                    onClick={() => setFilterMode('long_duration')}
                    className={`btn btn-sm ${filterMode === 'long_duration' ? 'btn-primary' : 'btn-secondary'}`}
                    style={{ fontSize: '0.75rem', padding: '0.25rem 0.55rem' }}
                  >
                    Duration &gt;15s
                  </button>
                </div>

                <select
                  className="input"
                  value={sortOrder}
                  onChange={(e) => setSortOrder(e.target.value as any)}
                  style={{ fontSize: '0.75rem', padding: '0.25rem 0.5rem', borderRadius: '0.35rem' }}
                >
                  <option value="time_desc">Newest First</option>
                  <option value="time_asc">Oldest First</option>
                  <option value="motion_desc">Highest Motion Score</option>
                </select>
              </div>
            </div>

            {allEvents && allEvents.length > 0 ? (
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
                  gap: '1.25rem',
                }}
              >
                {allEvents.map((ev) => {
                  const ts = formatTimestamp(ev.start_time);
                  const duration = getEventDuration(ev.start_time, ev.end_time);

                  return (
                    <div
                      key={ev.id}
                      onClick={() => setActiveEvent(ev)}
                      style={{
                        backgroundColor: 'var(--bg-primary)',
                        border: '1px solid var(--border-color)',
                        borderRadius: '0.5rem',
                        overflow: 'hidden',
                        cursor: 'pointer',
                        display: 'flex',
                        flexDirection: 'column',
                        transition: 'transform 0.15s ease, box-shadow 0.15s ease',
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.transform = 'translateY(-2px)';
                        e.currentTarget.style.boxShadow = '0 6px 16px rgba(0,0,0,0.2)';
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.transform = 'none';
                        e.currentTarget.style.boxShadow = 'none';
                      }}
                    >
                      {/* Image Thumbnail with Overlay */}
                      <div
                        style={{
                          height: '160px',
                          backgroundColor: '#0a0a0c',
                          position: 'relative',
                          overflow: 'hidden',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                        }}
                      >
                        <img
                          src={api.getEventThumbnailUrl(ev.id)}
                          alt={`Event ${ev.id} snapshot`}
                          style={{
                            width: '100%',
                            height: '100%',
                            objectFit: 'cover',
                            display: 'block',
                          }}
                          onError={(e) => {
                            // Fallback if image fails or missing
                            e.currentTarget.style.display = 'none';
                            const fallback = e.currentTarget.parentElement?.querySelector('.img-fallback') as HTMLElement;
                            if (fallback) fallback.style.display = 'flex';
                          }}
                        />

                        {/* Fallback container */}
                        <div
                          className="img-fallback"
                          style={{
                            display: 'none',
                            flexDirection: 'column',
                            alignItems: 'center',
                            justifyContent: 'center',
                            gap: '0.4rem',
                            color: 'var(--text-muted)',
                            height: '100%',
                            width: '100%',
                          }}
                        >
                          <BellRing size={32} style={{ opacity: 0.6 }} />
                          <span style={{ fontSize: '0.75rem' }}>Snapshot Captured</span>
                        </div>

                        {/* Top Overlay Badges */}
                        <div
                          style={{
                            position: 'absolute',
                            top: '0.5rem',
                            left: '0.5rem',
                            right: '0.5rem',
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            pointerEvents: 'none',
                          }}
                        >
                          <span
                            style={{
                              backgroundColor: 'rgba(0, 0, 0, 0.75)',
                              color: ev.peak_motion_score >= 50 ? '#f87171' : '#fbbf24',
                              fontSize: '0.7rem',
                              fontWeight: 700,
                              padding: '0.2rem 0.5rem',
                              borderRadius: '0.3rem',
                              backdropFilter: 'blur(4px)',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '0.25rem',
                            }}
                          >
                            <Flame size={12} />
                            {ev.peak_motion_score.toFixed(1)}% Motion
                          </span>

                          <span
                            style={{
                              backgroundColor: 'rgba(239, 68, 68, 0.85)',
                              color: '#ffffff',
                              fontSize: '0.65rem',
                              fontWeight: 700,
                              padding: '0.15rem 0.45rem',
                              borderRadius: '0.25rem',
                              textTransform: 'uppercase',
                              letterSpacing: '0.5px',
                            }}
                          >
                            {ev.activity_state || 'ACTIVE'}
                          </span>
                        </div>

                        {/* Bottom Overlay Timestamp Pill */}
                        <div
                          style={{
                            position: 'absolute',
                            bottom: '0.5rem',
                            left: '0.5rem',
                            right: '0.5rem',
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            pointerEvents: 'none',
                          }}
                        >
                          <span
                            style={{
                              backgroundColor: 'rgba(0, 0, 0, 0.8)',
                              color: '#ffffff',
                              fontSize: '0.75rem',
                              fontWeight: 600,
                              padding: '0.2rem 0.5rem',
                              borderRadius: '0.3rem',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '0.3rem',
                              backdropFilter: 'blur(4px)',
                            }}
                          >
                            <Clock size={12} />
                            {ts.time}
                          </span>

                          {ev.frame_count > 0 && (
                            <span
                              style={{
                                backgroundColor: 'rgba(0, 0, 0, 0.7)',
                                color: 'var(--text-secondary, #cbd5e1)',
                                fontSize: '0.65rem',
                                padding: '0.15rem 0.4rem',
                                borderRadius: '0.25rem',
                              }}
                            >
                              {ev.frame_count} frames
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Card Body with Timestamp & Action */}
                      <div style={{ padding: '0.85rem', display: 'flex', flexDirection: 'column', gap: '0.4rem', flex: 1 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <span style={{ fontWeight: 600, fontSize: '0.9rem' }}>Event #{ev.id}</span>
                          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Camera #{ev.camera_id}</span>
                        </div>

                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                          <strong>Occurred:</strong> {ts.date} at {ts.time}
                          {duration && <span> • <strong>Duration:</strong> {duration}</span>}
                        </div>

                        {ev.description && (
                          <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                            {ev.description}
                          </div>
                        )}

                        <div style={{ marginTop: 'auto', paddingTop: '0.5rem' }}>
                          <button
                            className="btn btn-secondary btn-sm"
                            style={{ width: '100%', justifyContent: 'center', fontSize: '0.75rem' }}
                            onClick={(e) => {
                              e.stopPropagation();
                              setActiveEvent(ev);
                            }}
                          >
                            <Eye size={13} />
                            <span>Inspect Frames & Video</span>
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div
                style={{
                  padding: '3rem',
                  textAlign: 'center',
                  backgroundColor: 'var(--bg-primary)',
                  borderRadius: '0.5rem',
                  border: '1px dashed var(--border-color)',
                }}
              >
                <CheckCircle2 size={32} style={{ color: '#34d399', margin: '0 auto 0.75rem auto' }} />
                <h4 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '0.25rem' }}>
                  No Motion Events on {selectedDate}
                </h4>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', maxWidth: '420px', margin: '0 auto' }}>
                  The surveillance cameras recorded no active security anomalies or motion alerts on this day. The system remained in energy-efficient adaptive idle state.
                </p>
              </div>
            )}
          </div>
        </>
      ) : (
        <div className="card" style={{ padding: '3.5rem', textAlign: 'center', color: 'var(--text-muted)' }}>
          <Calendar size={36} style={{ color: 'var(--text-muted)', margin: '0 auto 0.75rem auto', opacity: 0.6 }} />
          <h3 style={{ fontSize: '1.05rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.35rem' }}>
            No Intelligence Summary for {selectedDate}
          </h3>
          <p style={{ fontSize: '0.85rem', maxWidth: '480px', margin: '0 auto 1.25rem auto' }}>
            No pre-computed daily intelligence report exists for this date. You can generate one on demand using the surveillance event records.
          </p>
          <button onClick={handleRegenerate} className="btn btn-primary btn-sm">
            <RotateCw size={14} />
            <span>Calculate Intelligence Summary for {selectedDate}</span>
          </button>
        </div>
      )}

      {/* Modal */}
      <EventDetailModal event={activeEvent} onClose={() => setActiveEvent(null)} />
    </div>
  );
};
