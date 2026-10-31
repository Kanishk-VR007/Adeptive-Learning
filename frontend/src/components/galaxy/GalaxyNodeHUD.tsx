import React from 'react';
import { Sparkles, ArrowRight, X, ShieldAlert, CheckCircle2 } from 'lucide-react';
import { Button } from '../ui/Button';

export interface GalaxyNodeData {
  id: number;
  name: string;
  subjectName: string;
  masteryProbability: number;
  prerequisites: string[];
  slipRate?: number;
  guessRate?: number;
  x: number;
  y: number;
}

export interface GalaxyNodeHUDProps {
  node: GalaxyNodeData | null;
  onClose: () => void;
  onPractice: (conceptId: number) => void;
}

export const GalaxyNodeHUD: React.FC<GalaxyNodeHUDProps> = ({ node, onClose, onPractice }) => {
  if (!node) return null;

  const pct = Math.round(node.masteryProbability * 100);
  const isMastered = pct >= 75;
  const isWeak = pct < 40;

  return (
    <div
      className="absolute z-20 w-72 bg-slate-900/95 backdrop-blur-xl border border-cyan-500/40 rounded-2xl p-4 shadow-[0_0_30px_rgba(6,182,212,0.25)] pointer-events-auto transform -translate-x-1/2 -translate-y-full mb-3 animate-in fade-in zoom-in-95 duration-150"
      style={{
        left: `${node.x}px`,
        top: `${node.y}px`,
      }}
      data-testid="galaxy-node-hud"
    >
      {/* Header with Title & Close */}
      <div className="flex items-start justify-between gap-2 border-b border-slate-800 pb-2.5">
        <div>
          <span className="text-[10px] uppercase font-mono tracking-wider text-cyan-400 font-semibold">
            {node.subjectName}
          </span>
          <h4 className="text-sm font-bold text-slate-100 flex items-center gap-1.5 mt-0.5">
            {node.name}
          </h4>
        </div>
        <button
          onClick={onClose}
          className="p-1 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition-colors"
          aria-label="Close concept inspector"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Mastery & BKT Stats */}
      <div className="py-3 space-y-2.5">
        <div>
          <div className="flex items-center justify-between text-xs mb-1">
            <span className="text-slate-400 font-medium">BKT Mastery $P(L)$</span>
            <span
              className={`font-bold font-mono ${
                isMastered ? 'text-emerald-400' : isWeak ? 'text-rose-400' : 'text-cyan-400'
              }`}
            >
              {pct}%
            </span>
          </div>
          <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                isMastered ? 'bg-emerald-500 shadow-glow-emerald' : isWeak ? 'bg-rose-500' : 'bg-cyan-500'
              }`}
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>

        {/* Cognitive status */}
        <div className="flex items-center gap-2 text-xs">
          {isMastered ? (
            <span className="flex items-center gap-1 text-emerald-400 font-medium">
              <CheckCircle2 className="w-3.5 h-3.5" /> Concept Verified
            </span>
          ) : isWeak ? (
            <span className="flex items-center gap-1 text-amber-400 font-medium">
              <ShieldAlert className="w-3.5 h-3.5" /> High Slip Risk
            </span>
          ) : (
            <span className="flex items-center gap-1 text-blue-400 font-medium">
              <Sparkles className="w-3.5 h-3.5" /> In Active Practice
            </span>
          )}
        </div>

        {/* Prerequisites */}
        {node.prerequisites && node.prerequisites.length > 0 && (
          <div className="text-[11px] text-slate-400">
            <span className="text-slate-500 font-medium">Prerequisites:</span>{' '}
            <span className="text-slate-300">{node.prerequisites.join(', ')}</span>
          </div>
        )}
      </div>

      {/* Action CTA */}
      <Button
        variant="tactile"
        size="sm"
        className="w-full text-xs font-semibold justify-center"
        onClick={() => onPractice(node.id)}
      >
        <span>Practice Drill</span>
        <ArrowRight className="w-3.5 h-3.5" />
      </Button>
    </div>
  );
};
