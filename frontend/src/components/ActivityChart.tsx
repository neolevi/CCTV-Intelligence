import React, { useState } from 'react';
import { HourlyActivity } from '../types';
import { BarChart2 } from 'lucide-react';

interface ActivityChartProps {
  hourlyData: HourlyActivity[];
  title?: string;
}

export const ActivityChart: React.FC<ActivityChartProps> = ({
  hourlyData,
  title = 'Hourly Motion Events Distribution',
}) => {
  const [hoveredHour, setHoveredHour] = useState<HourlyActivity | null>(null);

  const maxEvents = Math.max(...hourlyData.map((d) => d.event_count), 5);

  const chartHeight = 140;
  const chartWidth = 520;
  const barWidth = 14;
  const gap = 7;

  return (
    <div className="card" style={{ padding: '1.25rem' }}>
      <div className="card-header">
        <div className="card-title">
          <BarChart2 size={18} style={{ color: 'var(--accent-blue)' }} />
          <span>{title}</span>
        </div>
        {hoveredHour && (
          <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
            <strong>{hoveredHour.label}</strong>: {hoveredHour.event_count} events (
            {hoveredHour.active_minutes.toFixed(1)}m active)
          </div>
        )}
      </div>

      <div style={{ width: '100%', overflowX: 'auto' }}>
        <svg
          viewBox={`0 0 ${chartWidth} ${chartHeight + 30}`}
          style={{ width: '100%', height: '170px', display: 'block' }}
        >
          {/* Grid lines */}
          <line x1="0" y1={chartHeight} x2={chartWidth} y2={chartHeight} stroke="var(--border-color)" strokeWidth="1" />
          <line x1="0" y1={chartHeight / 2} x2={chartWidth} y2={chartHeight / 2} stroke="var(--border-color)" strokeDasharray="3 3" opacity="0.4" />

          {/* Bars */}
          {hourlyData.map((d, i) => {
            const h = (d.event_count / maxEvents) * (chartHeight - 20);
            const x = i * (barWidth + gap) + 10;
            const y = chartHeight - h;
            const isHovered = hoveredHour?.hour === d.hour;

            return (
              <g
                key={d.hour}
                onMouseEnter={() => setHoveredHour(d)}
                onMouseLeave={() => setHoveredHour(null)}
                style={{ cursor: 'pointer' }}
              >
                <rect
                  x={x}
                  y={y}
                  width={barWidth}
                  height={Math.max(2, h)}
                  rx="3"
                  fill={isHovered ? '#60a5fa' : d.event_count > 0 ? '#3b82f6' : '#1e293b'}
                  opacity={isHovered ? 1 : 0.85}
                  style={{ transition: 'all 0.15s ease' }}
                />
                {/* Hour label on X axis every 4 hours */}
                {d.hour % 4 === 0 && (
                  <text
                    x={x + barWidth / 2}
                    y={chartHeight + 18}
                    textAnchor="middle"
                    fill="var(--text-muted)"
                    fontSize="9"
                    fontFamily="var(--font-mono)"
                  >
                    {d.label}
                  </text>
                )}
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
};
