'use client';

import { useEffect, useRef } from 'react';

const COLORS = {
  low:    { stroke: '#f87171', text: '#f87171' },
  mid:    { stroke: '#fbbf24', text: '#fbbf24' },
  high:   { stroke: '#4ade80', text: '#4ade80' },
};

function getColor(value) {
  if (value >= 0.70) return COLORS.high;
  if (value >= 0.45) return COLORS.mid;
  return COLORS.low;
}

export default function ConfidenceGauge({ value = 0 }) {
  const fillRef = useRef(null);
  const pct = Math.round(value * 100);
  const color = getColor(value);

  // SVG arc: r=40, circumference = 2π×40 = 251.2
  // We only show top 75% of circle (270°), so arc = 251.2 * 0.75 = 188.4
  const C = 251.2;
  const ARC = C * 0.75;
  const offset = ARC - (ARC * value);

  useEffect(() => {
    if (fillRef.current) {
      // Trigger CSS transition after mount
      setTimeout(() => {
        if (fillRef.current) {
          fillRef.current.style.strokeDashoffset = offset;
        }
      }, 100);
    }
  }, [offset]);

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative w-32 h-32">
        <svg
          viewBox="0 0 100 100"
          className="w-full h-full -rotate-[135deg]"
        >
          {/* Background arc */}
          <circle
            cx="50" cy="50" r="40"
            fill="none"
            stroke="rgba(99,102,241,0.12)"
            strokeWidth="8"
            strokeLinecap="round"
            strokeDasharray={`${ARC} ${C}`}
          />
          {/* Fill arc */}
          <circle
            ref={fillRef}
            cx="50" cy="50" r="40"
            fill="none"
            stroke={color.stroke}
            strokeWidth="8"
            strokeLinecap="round"
            strokeDasharray={`${ARC} ${C}`}
            strokeDashoffset={ARC}
            style={{ transition: 'stroke-dashoffset 1.4s cubic-bezier(0.4,0,0.2,1)' }}
          />
        </svg>

        {/* Center text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-2xl font-bold currency" style={{ color: color.text }}>
            {pct}%
          </span>
          <span className="text-[10px] mt-0.5" style={{ color: 'var(--text-muted)' }}>
            confidence
          </span>
        </div>
      </div>

      {/* Label */}
      <span className="text-xs font-medium" style={{ color: color.text }}>
        {value >= 0.70 ? '✓ High Confidence' : value >= 0.45 ? '⚠ Moderate' : '✗ Low Confidence'}
      </span>
    </div>
  );
}
