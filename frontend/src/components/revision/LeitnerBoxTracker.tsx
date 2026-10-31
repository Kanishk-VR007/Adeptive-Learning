import React from 'react';
import { Layers, CheckCircle2, Clock } from 'lucide-react';

export interface LeitnerBoxTrackerProps {
  boxCounts?: [number, number, number, number, number]; // Counts in Box 1 to 5
  activeBox?: number; // 1 to 5
  className?: string;
}

export const LeitnerBoxTracker: React.FC<LeitnerBoxTrackerProps> = ({
  boxCounts = [4, 7, 12, 18, 25],
  activeBox = 1,
  className = '',
}) => {
  const boxLabels = [
    { box: 1, interval: 'Daily (<1d)', color: 'border-rose-500/50 text-rose-400 bg-rose-500/10' },
    { box: 2, interval: '2 Days', color: 'border-amber-500/50 text-amber-400 bg-amber-500/10' },
    { box: 3, interval: '4 Days', color: 'border-blue-500/50 text-blue-400 bg-blue-500/10' },
    { box: 4, interval: '7 Days', color: 'border-indigo-500/50 text-indigo-400 bg-indigo-500/10' },
    { box: 5, interval: '14+ Days', color: 'border-emerald-500/50 text-emerald-400 bg-emerald-500/10' },
  ];

  return (
    <div
      className={`p-4 rounded-2xl bg-slate-900/80 border border-slate-800 backdrop-blur-md ${className}`}
      data-testid="leitner-box-tracker"
    >
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
          <Layers className="w-3.5 h-3.5 text-cyan-400" />
          5-Stage Leitner Spaced Repetition Progression
        </h4>
        <span className="text-[11px] text-slate-400 font-medium">
          Total Deck: {boxCounts.reduce((a, b) => a + b, 0)} Concepts
        </span>
      </div>

      <div className="grid grid-cols-5 gap-2">
        {boxLabels.map((b, idx) => {
          const count = boxCounts[idx] || 0;
          const isCurrentActive = activeBox === b.box;

          return (
            <div
              key={b.box}
              className={`p-2.5 rounded-xl border text-center transition-all ${
                isCurrentActive
                  ? `${b.color} ring-2 ring-cyan-400 shadow-md`
                  : 'border-slate-800 bg-slate-950/40 text-slate-400 hover:border-slate-700'
              }`}
            >
              <div className="text-[10px] font-semibold text-slate-500 uppercase">
                Box {b.box}
              </div>
              <div className="text-base font-bold text-slate-100 my-0.5 font-mono">
                {count}
              </div>
              <div className="text-[9px] text-slate-400 truncate">
                {b.interval}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
