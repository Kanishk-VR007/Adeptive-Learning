import React from 'react';

interface ProgressBarProps {
  value: number; // 0 to 100
  height?: string;
  showLabel?: boolean;
  color?: 'gradient' | 'cyan' | 'blue' | 'emerald' | 'amber';
  className?: string;
}

export const ProgressBar: React.FC<ProgressBarProps> = ({
  value,
  height = 'h-2',
  showLabel = false,
  color = 'gradient',
  className = '',
}) => {
  const clamped = Math.max(0, Math.min(100, Math.round(value)));

  let barBg = 'bg-gradient-to-r from-electric-600 via-cyan-500 to-cyanAccent-glow shadow-glow-cyan';
  if (color === 'cyan') barBg = 'bg-cyan-500';
  if (color === 'blue') barBg = 'bg-electric-600';
  if (color === 'emerald') barBg = 'bg-emerald-500';
  if (color === 'amber') barBg = 'bg-amber-500';

  return (
    <div className={`w-full ${className}`}>
      {showLabel && (
        <div className="flex justify-between text-xs text-slate-400 mb-1">
          <span>Mastery Progress</span>
          <span className="font-semibold text-cyan-300">{clamped}%</span>
        </div>
      )}
      <div className={`w-full bg-slate-800/80 rounded-full overflow-hidden border border-slate-700/40 ${height}`}>
        <div
          className={`${barBg} ${height} rounded-full transition-all duration-500 ease-out`}
          style={{ width: `${clamped}%` }}
          role="progressbar"
          aria-valuenow={clamped}
          aria-valuemin={0}
          aria-valuemax={100}
        />
      </div>
    </div>
  );
};
