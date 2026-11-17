import React, { useState } from 'react';
import { TimelineSegment } from '../types';
import { Clock, Info } from 'lucide-react';

interface Timeline24hProps {
  segments: TimelineSegment[];
}

export const Timeline24h: React.FC<Timeline24hProps> = ({ segments }) => {
  const [hoveredSegment, setHoveredSegment] = useState<TimelineSegment | null>(null);
  const [selectedSegment, setSelectedSegment] = useState<TimelineSegment | null>(null);

  const activeInspect = hoveredSegment || selectedSegment;

  const getColor = (state: string) => {
    switch (state.toUpperCase()) {
      case 'ACTIVE':
        return '#ef4444';
      case 'IDLE':
        return '#f59e0b';
      case 'DEEP_IDLE':
        return '#10b981';
      default:
        return '#334155'; // OFFLINE
    }
  };

  return (
    <div className="card" style={{ padding: '1.25rem' }}>
      <div className="card-header">
        <div className="card-title">
          <Clock size={18} style={{ color: 'var(--accent-blue)' }} />
          <span>24-Hour Surveillance Activity Timeline</span>
        </div>
        {activeInspect && (
          <div
            style={{
              fontSize: '0.8rem',
              color: 'var(--text-secondary)',
              display: 'flex',
              alignItems: 'center',
              gap: '0.75rem',
            }}
          >
            <span>
              <strong>{activeInspect.start_time} - {activeInspect.end_time}</strong>
            </span>
            <span
              style={{
                color: getColor(activeInspect.activity_state),
                fontWeight: 600,
                textTransform: 'uppercase',
              }}
            >
              {activeInspect.activity_state}
            </span>
            {activeInspect.event_count > 0 && (
              <span style={{ color: '#f87171' }}>({activeInspect.event_count} motion events)</span>
            )}
          </div>
        )}
      </div>

      {/* Timeline track */}
      <div
        style={{
          display: 'flex',
          height: '32px',
          borderRadius: '0.375rem',
          overflow: 'hidden',
          backgroundColor: '#1e293b',
          border: '1px solid var(--border-color)',
          cursor: 'pointer',
          position: 'relative',
        }}
      >
        {segments && segments.length > 0 ? (
          segments.map((seg, idx) => {
            const isHovered = hoveredSegment === seg;
            const isSelected = selectedSegment === seg;
            return (
              <div
                key={idx}
                onMouseEnter={() => setHoveredSegment(seg)}
                onMouseLeave={() => setHoveredSegment(null)}
                onClick={() => setSelectedSegment(seg)}
                style={{
                  flex: 1,
                  backgroundColor: getColor(seg.activity_state),
                  opacity: (isHovered || isSelected) ? 1 : 0.82,
                  transition: 'opacity 0.1s',
                  position: 'relative',
                  borderRight: idx < segments.length - 1 ? '1px solid rgba(0,0,0,0.2)' : 'none',
                }}
                title={`${seg.start_time} - ${seg.end_time}: ${seg.activity_state} (${seg.event_count} events)`}
              />
            );
          })
        ) : (
          <div
            style={{
              width: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '0.8rem',
              color: 'var(--text-muted)',
            }}
          >
            No timeline data recorded for this date
          </div>
        )}
      </div>

      {/* Hour ticks */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          marginTop: '0.4rem',
          fontSize: '0.7rem',
          fontFamily: 'var(--font-mono)',
          color: 'var(--text-muted)',
        }}
      >
        <span>00:00</span>
        <span>04:00</span>
        <span>08:00</span>
        <span>12:00</span>
        <span>16:00</span>
        <span>20:00</span>
        <span>24:00</span>
      </div>

      {/* Legend */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '1.25rem',
          marginTop: '0.85rem',
          paddingTop: '0.75rem',
          borderTop: '1px solid var(--border-color)',
          fontSize: '0.75rem',
          color: 'var(--text-secondary)',
        }}
      >
        <span style={{ fontWeight: 600 }}>Legend:</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
          <span style={{ width: '10px', height: '10px', borderRadius: '2px', backgroundColor: '#ef4444' }} />
          <span>Active (5 FPS)</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
          <span style={{ width: '10px', height: '10px', borderRadius: '2px', backgroundColor: '#f59e0b' }} />
          <span>Idle (2 FPS)</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
          <span style={{ width: '10px', height: '10px', borderRadius: '2px', backgroundColor: '#10b981' }} />
          <span>Deep Idle (1 FPS)</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
          <span style={{ width: '10px', height: '10px', borderRadius: '2px', backgroundColor: '#334155' }} />
          <span>Offline</span>
        </div>
      </div>
    </div>
  );
};
