import React, { useState, useEffect } from 'react';
import { Recording } from '../types';
import { api } from '../services/api';
import { VideoPlayerModal } from '../components/VideoPlayerModal';
import { ConfirmModal } from '../components/ConfirmModal';
import { Film, Download, Trash2, Play, Calendar, Filter, HardDrive } from 'lucide-react';

export const Recordings: React.FC = () => {
  const [recordings, setRecordings] = useState<Recording[]>([]);
  const [loading, setLoading] = useState(true);
  const [dateFilter, setDateFilter] = useState<string>('');
  const [stateFilter, setStateFilter] = useState<string>('');
  const [activeRecording, setActiveRecording] = useState<Recording | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Recording | null>(null);

  const fetchRecordings = async () => {
    setLoading(true);
    try {
      const data = await api.listRecordings({
        date: dateFilter || undefined,
        activity_state: stateFilter || undefined,
      });
      setRecordings(data);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRecordings();
  }, [dateFilter, stateFilter]);

  const handleDeleteConfirm = async () => {
    if (!deleteTarget) return;
    try {
      await api.deleteRecording(deleteTarget.id);
      setRecordings((prev) => prev.filter((r) => r.id !== deleteTarget.id));
      setDeleteTarget(null);
    } catch (err: any) {
      alert(err.message || 'Failed to delete recording.');
    }
  };

  return (
    <div className="page-wrapper" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* Header and Filter Bar */}
      <div className="card" style={{ padding: '1rem 1.25rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
            <Film size={22} style={{ color: 'var(--accent-blue)' }} />
            <div>
              <h2 style={{ fontSize: '1.15rem', fontWeight: 600 }}>Surveillance Video Recordings</h2>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                {recordings.length} clip{recordings.length !== 1 ? 's' : ''} stored on disk
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
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

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <Filter size={15} style={{ color: 'var(--text-muted)' }} />
              <select
                className="input"
                style={{ padding: '0.4rem 0.65rem', fontSize: '0.825rem' }}
                value={stateFilter}
                onChange={(e) => setStateFilter(e.target.value)}
              >
                <option value="">All States</option>
                <option value="ACTIVE">Active Only</option>
                <option value="IDLE">Idle</option>
              </select>
            </div>

            {(dateFilter || stateFilter) && (
              <button
                onClick={() => {
                  setDateFilter('');
                  setStateFilter('');
                }}
                className="btn btn-secondary btn-sm"
              >
                Clear Filters
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Grid of Recordings */}
      {loading ? (
        <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
          Loading recordings...
        </div>
      ) : recordings.length > 0 ? (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
            gap: '1.25rem',
          }}
        >
          {recordings.map((rec) => {
            const sizeMb = (rec.file_size_bytes / (1024 * 1024)).toFixed(2);
            return (
              <div
                key={rec.id}
                className="card"
                style={{
                  padding: 0,
                  overflow: 'hidden',
                  display: 'flex',
                  flexDirection: 'column',
                }}
              >
                {/* Thumbnail / Video cover */}
                <div
                  onClick={() => setActiveRecording(rec)}
                  style={{
                    position: 'relative',
                    height: '160px',
                    backgroundColor: '#000000',
                    cursor: 'pointer',
                  }}
                >
                  {rec.thumbnail_path ? (
                    <img
                      src={api.getRecordingThumbnailUrl(rec.id)}
                      alt={`Recording ${rec.id}`}
                      style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                    />
                  ) : (
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-muted)' }}>
                      <Film size={36} />
                    </div>
                  )}

                  {/* Play Overlay Button */}
                  <div
                    style={{
                      position: 'absolute',
                      inset: 0,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      backgroundColor: 'rgba(0,0,0,0.3)',
                      transition: 'background-color 0.15s',
                    }}
                  >
                    <div
                      style={{
                        width: '44px',
                        height: '44px',
                        borderRadius: '50%',
                        backgroundColor: 'rgba(59, 130, 246, 0.9)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: '#ffffff',
                      }}
                    >
                      <Play size={20} style={{ marginLeft: '2px' }} />
                    </div>
                  </div>

                  <div
                    style={{
                      position: 'absolute',
                      bottom: '8px',
                      right: '8px',
                      backgroundColor: 'rgba(15, 23, 42, 0.85)',
                      padding: '0.2rem 0.5rem',
                      borderRadius: '0.3rem',
                      fontSize: '0.75rem',
                      fontFamily: 'var(--font-mono)',
                    }}
                  >
                    {rec.duration_seconds.toFixed(1)}s
                  </div>

                  <div style={{ position: 'absolute', top: '8px', left: '8px' }}>
                    <span className="badge badge-active">{rec.activity_state}</span>
                  </div>
                </div>

                {/* Details */}
                <div style={{ padding: '1rem', display: 'flex', flexDirection: 'column', gap: '0.75rem', flex: 1 }}>
                  <div>
                    <div style={{ fontSize: '0.95rem', fontWeight: 600 }}>Recording #{rec.id}</div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                      {new Date(rec.start_time).toLocaleString()}
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                    <HardDrive size={14} style={{ color: 'var(--text-muted)' }} />
                    <span>File size: {sizeMb} MB</span>
                  </div>

                  <div
                    style={{
                      marginTop: 'auto',
                      paddingTop: '0.75rem',
                      borderTop: '1px solid var(--border-color)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                    }}
                  >
                    <a
                      href={api.getRecordingDownloadUrl(rec.id)}
                      download
                      className="btn btn-secondary btn-sm"
                      title="Download MP4"
                      style={{ padding: '0.3rem 0.6rem' }}
                    >
                      <Download size={14} />
                      <span>Download</span>
                    </a>

                    <button
                      onClick={() => setDeleteTarget(rec)}
                      className="btn btn-danger btn-sm"
                      title="Delete recording"
                      style={{ padding: '0.3rem 0.6rem' }}
                    >
                      <Trash2 size={14} />
                      <span>Delete</span>
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="card" style={{ padding: '3.5rem', textAlign: 'center', color: 'var(--text-muted)' }}>
          <Film size={36} style={{ margin: '0 auto 0.75rem', opacity: 0.5 }} />
          <h3 style={{ fontSize: '1rem', fontWeight: 600 }}>No video recordings match your criteria</h3>
          <p style={{ fontSize: '0.8rem', marginTop: '0.25rem' }}>
            Recordings are automatically generated and saved when motion occurs while monitoring is active.
          </p>
        </div>
      )}

      {/* Modals */}
      <VideoPlayerModal recording={activeRecording} onClose={() => setActiveRecording(null)} />
      <ConfirmModal
        isOpen={deleteTarget !== null}
        title="Delete Surveillance Recording?"
        message={`Are you sure you want to permanently delete Recording #${deleteTarget?.id}? The MP4 file will be removed from physical disk storage.`}
        onConfirm={handleDeleteConfirm}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
};
