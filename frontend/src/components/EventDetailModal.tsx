import React, { useState, useEffect } from 'react';
import { MotionEvent, MotionEventDetail } from '../types';
import { api } from '../services/api';
import { X, BellRing, Image as ImageIcon, Clock, Gauge } from 'lucide-react';

interface EventDetailModalProps {
  event: MotionEvent | null;
  onClose: () => void;
}

export const EventDetailModal: React.FC<EventDetailModalProps> = ({ event, onClose }) => {
  const [detail, setDetail] = useState<MotionEventDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedImage, setSelectedImage] = useState<string | null>(null);

  useEffect(() => {
    if (event) {
      setLoading(true);
      api
        .getEventDetail(event.id)
        .then((data) => setDetail(data))
        .catch(() => {})
        .finally(() => setLoading(false));
    } else {
      setDetail(null);
    }
  }, [event]);

  if (!event) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '850px' }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '1rem 1.25rem',
            borderBottom: '1px solid var(--border-color)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
            <BellRing size={20} style={{ color: '#ef4444' }} />
            <h3 style={{ fontSize: '1rem', fontWeight: 600 }}>Motion Event #{event.id} Details</h3>
          </div>
          <button
            onClick={onClose}
            className="btn btn-secondary btn-sm"
            style={{ padding: '0.35rem', borderRadius: '0.35rem' }}
          >
            <X size={18} />
          </button>
        </div>

        <div style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          {/* Metadata Grid */}
          <div className="grid-4">
            <div style={{ backgroundColor: 'var(--bg-primary)', padding: '0.75rem', borderRadius: '0.5rem', border: '1px solid var(--border-color)' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Status</div>
              <div style={{ marginTop: '0.25rem' }}>
                <span className="badge badge-active">{event.activity_state}</span>
              </div>
            </div>

            <div style={{ backgroundColor: 'var(--bg-primary)', padding: '0.75rem', borderRadius: '0.5rem', border: '1px solid var(--border-color)' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Peak Motion</div>
              <div style={{ fontSize: '1.1rem', fontWeight: 700, marginTop: '0.25rem', color: '#f87171' }}>
                {event.peak_motion_score.toFixed(1)}%
              </div>
            </div>

            <div style={{ backgroundColor: 'var(--bg-primary)', padding: '0.75rem', borderRadius: '0.5rem', border: '1px solid var(--border-color)' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Keyframes</div>
              <div style={{ fontSize: '1.1rem', fontWeight: 700, marginTop: '0.25rem' }}>
                {event.frame_count} frames
              </div>
            </div>

            <div style={{ backgroundColor: 'var(--bg-primary)', padding: '0.75rem', borderRadius: '0.5rem', border: '1px solid var(--border-color)' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Detected At</div>
              <div style={{ fontSize: '0.85rem', fontWeight: 600, marginTop: '0.25rem' }}>
                {new Date(event.start_time).toLocaleTimeString()}
              </div>
            </div>
          </div>

          {/* Description */}
          {event.description && (
            <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              <strong>Description:</strong> {event.description}
            </div>
          )}

          {/* Large Image Preview if clicked */}
          {selectedImage && (
            <div style={{ position: 'relative', borderRadius: '0.5rem', overflow: 'hidden', border: '1px solid var(--border-color)' }}>
              <img src={selectedImage} alt="Selected keyframe" style={{ width: '100%', display: 'block' }} />
              <button
                onClick={() => setSelectedImage(null)}
                className="btn btn-secondary btn-sm"
                style={{ position: 'absolute', top: '8px', right: '8px' }}
              >
                Close Preview
              </button>
            </div>
          )}

          {/* Associated Captured Frames Gallery */}
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
              <ImageIcon size={17} style={{ color: 'var(--accent-blue)' }} />
              <h4 style={{ fontSize: '0.9rem', fontWeight: 600 }}>Correlated Adaptive Keyframes</h4>
            </div>

            {loading ? (
              <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                Loading frames...
              </div>
            ) : detail?.frames && detail.frames.length > 0 ? (
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))',
                  gap: '0.75rem',
                }}
              >
                {detail.frames.map((frame) => {
                  const imgUrl = api.getFrameImageUrl(frame.id);
                  return (
                    <div
                      key={frame.id}
                      onClick={() => setSelectedImage(imgUrl)}
                      style={{
                        borderRadius: '0.375rem',
                        overflow: 'hidden',
                        border: '1px solid var(--border-color)',
                        cursor: 'pointer',
                        backgroundColor: '#000000',
                      }}
                    >
                      <img
                        src={imgUrl}
                        alt={`Frame ${frame.id}`}
                        style={{ width: '100%', height: '110px', objectFit: 'cover', display: 'block' }}
                      />
                      <div
                        style={{
                          padding: '0.35rem 0.5rem',
                          fontSize: '0.7rem',
                          display: 'flex',
                          justifyContent: 'space-between',
                          backgroundColor: 'var(--bg-card)',
                        }}
                      >
                        <span style={{ color: 'var(--text-muted)' }}>{new Date(frame.timestamp).toLocaleTimeString()}</span>
                        <span style={{ color: '#f87171', fontWeight: 600 }}>{frame.motion_score.toFixed(1)}%</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div
                style={{
                  padding: '2rem',
                  textAlign: 'center',
                  backgroundColor: 'var(--bg-primary)',
                  borderRadius: '0.5rem',
                  border: '1px dashed var(--border-color)',
                  color: 'var(--text-muted)',
                  fontSize: '0.85rem',
                }}
              >
                No sampled frames stored for this event.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
