import React from 'react';

export interface SegmentedProgressBarProps {
  totalSegments?: number;
  currentSegment: number; // 1-indexed
  className?: string;
  label?: string;
}

export const SegmentedProgressBar: React.FC<SegmentedProgressBarProps> = ({
  totalSegments = 5,
  currentSegment,
  className = '',
  label,
}) => {
  return (
    <div className={`space-y-1.5 w-full ${className}`} data-testid="segmented-progress-bar">
      {label && (
        <div className="flex items-center justify-between text-xs text-slate-400 font-medium">
          <span>{label}</span>
          <span className="font-mono text-cyan-400 font-semibold">
            {Math.min(currentSegment, totalSegments)} of {totalSegments}
          </span>
        </div>
      )}
      <div className="flex items-center gap-1.5 w-full">
        {Array.from({ length: totalSegments }, (_, i) => {
          const segmentIndex = i + 1;
          const isCompleted = segmentIndex < currentSegment;
          const isCurrent = segmentIndex === currentSegment;

          return (
            <div
              key={i}
              className={`h-2 flex-1 rounded-full transition-all duration-300 relative overflow-hidden ${
                isCompleted
                  ? 'bg-blue-500 shadow-[0_0_8px_rgba(59,130,246,0.5)]'
                  : isCurrent
                  ? 'bg-cyan-400 shadow-[0_0_12px_rgba(6,182,212,0.6)] animate-pulse'
                  : 'bg-slate-800'
              }`}
            >
              {isCompleted && (
                <div className="absolute inset-0 bg-white/20" />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
