import React from 'react';
import { Lightbulb, ChevronDown, ChevronUp, Sparkles } from 'lucide-react';

interface HintDrawerProps {
  hints: string[];
  currentHintIndex: number;
  isOpen: boolean;
  onToggle: () => void;
  onRequestNextHint: () => void;
}

export const HintDrawer: React.FC<HintDrawerProps> = ({
  hints,
  currentHintIndex,
  isOpen,
  onToggle,
  onRequestNextHint,
}) => {
  if (!hints || hints.length === 0) return null;

  const totalHints = hints.length;
  const activeHints = hints.slice(0, currentHintIndex + 1);
  const hasMoreHints = currentHintIndex < totalHints - 1;

  return (
    <div
      className="rounded-xl border border-amber-500/30 bg-amber-950/20 overflow-hidden transition-all"
      data-testid="hint-drawer"
    >
      {/* Header bar */}
      <button
        onClick={onToggle}
        className="w-full px-4 py-2.5 flex items-center justify-between text-left hover:bg-amber-500/10 transition-colors"
        data-testid="hint-drawer-toggle"
      >
        <div className="flex items-center gap-2">
          <Lightbulb className="w-4 h-4 text-amber-400 fill-amber-400/20" />
          <span className="text-xs font-semibold text-amber-300">
            Socratic Hints ({activeHints.length}/{totalHints} Revealed)
          </span>
        </div>

        <div className="flex items-center gap-1 text-amber-400 text-xs">
          <span>{isOpen ? 'Hide' : 'Show'}</span>
          {isOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </div>
      </button>

      {/* Expanded Content */}
      {isOpen && (
        <div className="px-4 pb-4 pt-1 space-y-2.5 border-t border-amber-500/20">
          {activeHints.map((hint, idx) => (
            <div
              key={idx}
              className="p-3 rounded-lg bg-slate-900/80 border border-amber-500/20 text-xs text-slate-200"
              data-testid={`hint-step-${idx}`}
            >
              <div className="text-[10px] font-bold uppercase text-amber-400 mb-1 flex items-center gap-1">
                <Sparkles className="w-3 h-3 text-amber-400" />
                Hint Level {idx + 1}
              </div>
              <p className="leading-relaxed">{hint}</p>
            </div>
          ))}

          {hasMoreHints && (
            <button
              onClick={onRequestNextHint}
              className="w-full py-2 rounded-lg bg-amber-500/20 hover:bg-amber-500/30 text-amber-200 text-xs font-semibold border border-amber-500/30 flex items-center justify-center gap-1.5 transition-colors"
              data-testid="request-next-hint-button"
            >
              <Lightbulb className="w-3.5 h-3.5" />
              <span>Reveal Next Clue ({totalHints - activeHints.length} remaining)</span>
            </button>
          )}
        </div>
      )}
    </div>
  );
};
