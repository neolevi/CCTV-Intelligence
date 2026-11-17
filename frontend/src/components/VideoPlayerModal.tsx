import React from 'react';
import { Recording } from '../types';
import { api } from '../services/api';
import { X, Download, Film, HardDrive, Clock, ShieldAlert } from 'lucide-react';

interface VideoPlayerModalProps {
  recording: Recording | null;
  onClose: () => void;
}

export const VideoPlayerModal: React.FC<VideoPlayerModalProps> = ({ recording, onClose }) => {
  if (!recording) return null;

  const streamUrl = api.getRecordingStreamUrl(recording.id);
  const downloadUrl = api.getRecordingDownloadUrl(recording.id);
  const fileSizeMb = (recording.file_size_bytes / (1024 * 1024)).toFixed(2);

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '800px' }}>
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
            <Film size={20} style={{ color: 'var(--accent-blue)' }} />
            <h3 style={{ fontSize: '1rem', fontWeight: 600 }}>Surveillance Recording #{recording.id}</h3>
          </div>
          <button
            onClick={onClose}
            className="btn btn-secondary btn-sm"
            style={{ padding: '0.35rem', borderRadius: '0.35rem' }}
          >
            <X size={18} />
          </button>
        </div>

        <div style={{ padding: '1.25rem', backgroundColor: '#000000' }}>
          <video
            controls
            autoPlay
            style={{ width: '100%', maxHeight: '420px', borderRadius: '0.375rem', display: 'block' }}
            src={streamUrl}
          >
            Your browser does not support HTML5 video playback.
          </video>
        </div>

        <div style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div className="grid-3">
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem' }}>
              <Clock size={16} style={{ color: 'var(--text-muted)' }} />
              <div>
                <span style={{ color: 'var(--text-muted)' }}>Duration: </span>
                <strong>{recording.duration_seconds.toFixed(1)}s</strong>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem' }}>
              <HardDrive size={16} style={{ color: 'var(--text-muted)' }} />
              <div>
                <span style={{ color: 'var(--text-muted)' }}>Size: </span>
                <strong>{fileSizeMb} MB</strong>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem' }}>
              <ShieldAlert size={16} style={{ color: 'var(--text-muted)' }} />
              <div>
                <span style={{ color: 'var(--text-muted)' }}>State: </span>
                <span className="badge badge-active">{recording.activity_state}</span>
              </div>
            </div>
          </div>

          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              paddingTop: '1rem',
              borderTop: '1px solid var(--border-color)',
            }}
          >
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Captured on {new Date(recording.start_time).toLocaleString()}
            </span>
            <a
              href={downloadUrl}
              download
              className="btn btn-primary btn-sm"
              style={{ textDecoration: 'none' }}
            >
              <Download size={15} />
              <span>Download MP4</span>
            </a>
          </div>
        </div>
      </div>
    </div>
  );
};
