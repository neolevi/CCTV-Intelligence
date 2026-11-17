import React, { useState, useEffect } from 'react';
import { MotionEvent } from '../types';
import { api } from '../services/api';
import { EventDetailModal } from '../components/EventDetailModal';
import { ConfirmModal } from '../components/ConfirmModal';
import { BellRing, Calendar, Search, Trash2, Eye, Filter, ShieldAlert } from 'lucide-react';

export const Events: React.FC = () => {
  const [events, setEvents] = useState<MotionEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [dateFilter, setDateFilter] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [activeEvent, setActiveEvent] = useState<MotionEvent | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<MotionEvent | null>(null);

  const fetchEvents = async () => {
    setLoading(true);
    try {
      const data = await api.listEvents({
        date: dateFilter || undefined,
        search: searchQuery || undefined,
      });
      setEvents(data);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEvents();
  }, [dateFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchEvents();
  };

  const handleDeleteConfirm = async () => {
    if (!deleteTarget) return;
    try {
      await api.deleteEvent(deleteTarget.id);
      setEvents((prev) => prev.filter((e) => e.id !== deleteTarget.id));
      setDeleteTarget(null);
    } catch (err: any) {
      alert(err.message || 'Failed to delete event.');
    }
  };

  return (
    <div className="page-wrapper" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* Header and Filter Toolbar */}
      <div className="card" style={{ padding: '1rem 1.25rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
            <BellRing size={22} style={{ color: '#ef4444' }} />
            <div>
              <h2 style={{ fontSize: '1.15rem', fontWeight: 600 }}>Motion Surveillance Events</h2>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                {events.length} detected event{events.length !== 1 ? 's' : ''} with correlated keyframes
              </p>
            </div>
          </div>

          <form onSubmit={handleSearchSubmit} style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <Calendar size={15} style={{ color: 'var(--text-muted)' }} />
              <input
                type="date"
                className="input"
                style={{ padding: '0.4rem 0.65rem', fontSize: '0.825rem' }}
                value={dateFilter}
                onChange={(e) => setDateFilter(e.target.value)}
              />
            </div>

            <div style={{ position: 'relative' }}>
              <input
                type="text"
                placeholder="Search description..."
                className="input"
                style={{ padding: '0.4rem 0.65rem', paddingLeft: '1.85rem', fontSize: '0.825rem', width: '200px' }}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
              <Search size={14} style={{ position: 'absolute', left: '0.6rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
            </div>

            <button type="submit" className="btn btn-secondary btn-sm">
              Search
            </button>

            {(dateFilter || searchQuery) && (
              <button
                type="button"
                onClick={() => {
                  setDateFilter('');
                  setSearchQuery('');
                }}
                className="btn btn-secondary btn-sm"
              >
                Clear
              </button>
            )}
          </form>
        </div>
      </div>

      {/* Events Table */}
      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        {loading ? (
          <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
            Loading surveillance events...
          </div>
        ) : events.length > 0 ? (
          <div style={{ overflowX: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th style={{ width: '80px' }}>Thumbnail</th>
                  <th>Event ID</th>
                  <th>Timestamp</th>
                  <th>Classification</th>
                  <th>Peak Score</th>
                  <th>Sampled Frames</th>
                  <th>Description</th>
                  <th style={{ textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {events.map((ev) => (
                  <tr key={ev.id}>
                    <td>
                      <div
                        onClick={() => setActiveEvent(ev)}
                        style={{
                          width: '64px',
                          height: '48px',
                          backgroundColor: '#000000',
                          borderRadius: '0.35rem',
                          overflow: 'hidden',
                          cursor: 'pointer',
                        }}
                      >
                        {ev.thumbnail_path ? (
                          <img
                            src={api.getEventThumbnailUrl(ev.id)}
                            alt={`Event ${ev.id}`}
                            style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                          />
                        ) : (
                          <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
                            <BellRing size={16} />
                          </div>
                        )}
                      </div>
                    </td>
                    <td>
                      <strong>#{ev.id}</strong>
                    </td>
                    <td>
                      <div>{new Date(ev.start_time).toLocaleDateString()}</div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        {new Date(ev.start_time).toLocaleTimeString()}
                      </div>
                    </td>
                    <td>
                      <span className="badge badge-active">{ev.activity_state}</span>
                    </td>
                    <td>
                      <span style={{ color: '#f87171', fontWeight: 600 }}>{ev.peak_motion_score.toFixed(1)}%</span>
                    </td>
                    <td>
                      <span>{ev.frame_count} frames</span>
                    </td>
                    <td style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                      {ev.description || 'Motion activity detected'}
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <div style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem' }}>
                        <button
                          onClick={() => setActiveEvent(ev)}
                          className="btn btn-secondary btn-sm"
                          title="Inspect Frames"
                          style={{ padding: '0.25rem 0.55rem' }}
                        >
                          <Eye size={14} />
                          <span>Inspect</span>
                        </button>
                        <button
                          onClick={() => setDeleteTarget(ev)}
                          className="btn btn-danger btn-sm"
                          title="Delete Event"
                          style={{ padding: '0.25rem 0.55rem' }}
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div style={{ padding: '3.5rem', textAlign: 'center', color: 'var(--text-muted)' }}>
            <BellRing size={36} style={{ margin: '0 auto 0.75rem', opacity: 0.5 }} />
            <h3 style={{ fontSize: '1rem', fontWeight: 600 }}>No motion events found</h3>
            <p style={{ fontSize: '0.8rem', marginTop: '0.25rem' }}>
              Motion events will be automatically recorded when movement exceeds the sensitivity threshold.
            </p>
          </div>
        )}
      </div>

      {/* Modals */}
      <EventDetailModal event={activeEvent} onClose={() => setActiveEvent(null)} />
      <ConfirmModal
        isOpen={deleteTarget !== null}
        title="Delete Motion Event?"
        message={`Are you sure you want to remove Event #${deleteTarget?.id}? Associated thumbnail assets will also be deleted.`}
        onConfirm={handleDeleteConfirm}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
};
