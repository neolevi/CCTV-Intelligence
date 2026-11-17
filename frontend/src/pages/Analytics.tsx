import React, { useState, useEffect } from 'react';
import { AnalyticsOverview, AnalyticsTrends } from '../types';
import { api } from '../services/api';
import {
  BarChart3,
  TrendingUp,
  Clock,
  HardDrive,
  BellRing,
  PieChart,
  Calendar,
  Layers,
} from 'lucide-react';

export const Analytics: React.FC = () => {
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [trends, setTrends] = useState<AnalyticsTrends | null>(null);
  const [days, setDays] = useState<number>(7);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const [ov, tr] = await Promise.all([
          api.getAnalyticsOverview(),
          api.getAnalyticsTrends(days),
        ]);
        setOverview(ov);
        setTrends(tr);
      } catch {
        // ignore
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [days]);

  const formatSeconds = (sec: number) => {
    const h = Math.floor(sec / 3600);
    const m = Math.floor((sec % 3600) / 60);
    if (h > 0) return `${h}h ${m}m`;
    return `${m}m`;
  };

  const formatStorageMb = (bytes: number) => {
    return (bytes / (1024 * 1024)).toFixed(1);
  };

  return (
    <div className="page-wrapper" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Header and Date Range Picker */}
      <div className="card" style={{ padding: '1rem 1.25rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
            <BarChart3 size={22} style={{ color: 'var(--accent-blue)' }} />
            <div>
              <h2 style={{ fontSize: '1.15rem', fontWeight: 600 }}>Surveillance Analytics & Trends</h2>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                Activity patterns, storage utilization, and historical motion frequency
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Time Horizon:</span>
            {[7, 14, 30].map((d) => (
              <button
                key={d}
                onClick={() => setDays(d)}
                className={`btn btn-sm ${days === d ? 'btn-primary' : 'btn-secondary'}`}
              >
                {d} Days
              </button>
            ))}
          </div>
        </div>
      </div>

      {loading ? (
        <div style={{ padding: '4rem', textAlign: 'center', color: 'var(--text-muted)' }}>
          Aggregating surveillance analytics...
        </div>
      ) : overview && trends ? (
        <>
          {/* Top KPI Grid */}
          <div className="grid-4">
            <div className="stat-card">
              <div className="stat-icon-wrapper" style={{ backgroundColor: 'rgba(239, 68, 68, 0.15)', color: '#ef4444' }}>
                <Clock size={22} />
              </div>
              <div>
                <div className="stat-label">Active Time Today</div>
                <div className="stat-value">{formatSeconds(overview.today_active_seconds)}</div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                  {overview.active_ratio_today.toFixed(1)}% of monitored day
                </div>
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-icon-wrapper" style={{ backgroundColor: 'rgba(245, 158, 11, 0.15)', color: '#f59e0b' }}>
                <BellRing size={22} />
              </div>
              <div>
                <div className="stat-label">Motion Events Today</div>
                <div className="stat-value">{overview.total_motion_events_today}</div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Verified motion triggers</div>
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-icon-wrapper" style={{ backgroundColor: 'rgba(59, 130, 246, 0.15)', color: 'var(--accent-blue)' }}>
                <TrendingUp size={22} />
              </div>
              <div>
                <div className="stat-label">Weekly Coverage</div>
                <div className="stat-value">{overview.total_monitoring_hours_week.toFixed(1)} hrs</div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Across past 7 days</div>
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-icon-wrapper" style={{ backgroundColor: 'rgba(6, 182, 212, 0.15)', color: '#06b6d4' }}>
                <HardDrive size={22} />
              </div>
              <div>
                <div className="stat-label">Storage Consumed</div>
                <div className="stat-value">{formatStorageMb(overview.total_storage_used_bytes)} MB</div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                  {overview.total_recordings_count} recorded video clips
                </div>
              </div>
            </div>
          </div>

          {/* Historical Trend Charts */}
          <div className="grid-2">
            {/* Motion Events Trend Chart */}
            <div className="card">
              <div className="card-header">
                <div className="card-title">
                  <TrendingUp size={18} style={{ color: 'var(--accent-blue)' }} />
                  <span>Daily Motion Events Trend</span>
                </div>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Past {days} days</span>
              </div>

              <div style={{ height: '220px', width: '100%', display: 'flex', alignItems: 'flex-end', gap: '8px', paddingBottom: '24px', position: 'relative' }}>
                {trends.dates.map((date, idx) => {
                  const count = trends.motion_event_counts[idx] || 0;
                  const maxCount = Math.max(...trends.motion_event_counts, 5);
                  const heightPercent = Math.max(5, (count / maxCount) * 100);

                  return (
                    <div
                      key={date}
                      style={{
                        flex: 1,
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        height: '100%',
                        justifyContent: 'flex-end',
                      }}
                    >
                      <div
                        style={{
                          width: '100%',
                          maxWidth: '28px',
                          height: `${heightPercent}%`,
                          backgroundColor: count > 0 ? '#3b82f6' : '#1e293b',
                          borderRadius: '4px 4px 0 0',
                          transition: 'height 0.3s ease',
                        }}
                        title={`${date}: ${count} events`}
                      />
                      <span
                        style={{
                          position: 'absolute',
                          bottom: 0,
                          fontSize: '0.65rem',
                          color: 'var(--text-muted)',
                          fontFamily: 'var(--font-mono)',
                        }}
                      >
                        {date.slice(5)}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Daily Active Minutes Trend */}
            <div className="card">
              <div className="card-header">
                <div className="card-title">
                  <Clock size={18} style={{ color: '#f87171' }} />
                  <span>Daily Active Duration (Minutes)</span>
                </div>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>High-FPS activity</span>
              </div>

              <div style={{ height: '220px', width: '100%', display: 'flex', alignItems: 'flex-end', gap: '8px', paddingBottom: '24px', position: 'relative' }}>
                {trends.dates.map((date, idx) => {
                  const activeMins = trends.active_durations[idx] || 0;
                  const maxMins = Math.max(...trends.active_durations, 10);
                  const heightPercent = Math.max(5, (activeMins / maxMins) * 100);

                  return (
                    <div
                      key={date}
                      style={{
                        flex: 1,
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        height: '100%',
                        justifyContent: 'flex-end',
                      }}
                    >
                      <div
                        style={{
                          width: '100%',
                          maxWidth: '28px',
                          height: `${heightPercent}%`,
                          backgroundColor: activeMins > 0 ? '#ef4444' : '#1e293b',
                          borderRadius: '4px 4px 0 0',
                          transition: 'height 0.3s ease',
                        }}
                        title={`${date}: ${activeMins.toFixed(1)} active minutes`}
                      />
                      <span
                        style={{
                          position: 'absolute',
                          bottom: 0,
                          fontSize: '0.65rem',
                          color: 'var(--text-muted)',
                          fontFamily: 'var(--font-mono)',
                        }}
                      >
                        {date.slice(5)}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Detailed Historical Data Table */}
          <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
            <div style={{ padding: '1rem 1.25rem', borderBottom: '1px solid var(--border-color)', fontWeight: 600 }}>
              Surveillance History Archive
            </div>
            <div style={{ overflowX: 'auto' }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Motion Events</th>
                    <th>Active Duration</th>
                    <th>Idle Duration</th>
                    <th>Deep Idle Duration</th>
                    <th>Cumulative Storage</th>
                  </tr>
                </thead>
                <tbody>
                  {trends.dates.map((d, idx) => (
                    <tr key={d}>
                      <td><strong>{d}</strong></td>
                      <td>{trends.motion_event_counts[idx]} events</td>
                      <td style={{ color: '#f87171' }}>{trends.active_durations[idx].toFixed(1)} mins</td>
                      <td style={{ color: '#fbbf24' }}>{trends.idle_durations[idx].toFixed(1)} mins</td>
                      <td style={{ color: '#34d399' }}>{trends.deep_idle_durations[idx].toFixed(1)} mins</td>
                      <td style={{ fontFamily: 'var(--font-mono)' }}>
                        {formatStorageMb(trends.storage_trend_bytes[idx] || 0)} MB
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      ) : null}
    </div>
  );
};
