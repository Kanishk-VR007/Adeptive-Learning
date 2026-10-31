import React, { useEffect } from 'react';
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ArrowRight,
  RotateCcw,
  Sparkles,
  BookOpen,
  TrendingUp,
  TrendingDown,
} from 'lucide-react';
import confetti from 'canvas-confetti';
import { EvaluationResult } from '../../types';
import { Badge } from '../common/Badge';

interface FeedbackCardProps {
  result: EvaluationResult;
  onNextQuestion: () => void;
  onRetry: () => void;
  onReviewPrerequisite?: (conceptId: number) => void;
}

export const FeedbackCard: React.FC<FeedbackCardProps> = ({
  result,
  onNextQuestion,
  onRetry,
  onReviewPrerequisite,
}) => {
  // Fire confetti on correct answer
  useEffect(() => {
    if (result.outcome === 'correct') {
      try {
        confetti({
          particleCount: 45,
          spread: 60,
          origin: { y: 0.75 },
          colors: ['#00F0FF', '#3B82F6', '#10B981'],
        });
      } catch (e) {
        // Safe fallback in test environments
      }
    }
  }, [result.outcome]);

  const prevPct = Math.round(result.previousMastery * 100);
  const newPct = Math.round(result.updatedMastery * 100);
  const deltaPct = newPct - prevPct;

  return (
    <div
      className={`p-6 rounded-2xl border transition-all ${
        result.outcome === 'correct'
          ? 'bg-emerald-950/30 border-emerald-500/40 shadow-lg shadow-emerald-950/20'
          : result.outcome === 'partially_correct'
          ? 'bg-amber-950/30 border-amber-500/40 shadow-lg shadow-amber-950/20'
          : 'bg-rose-950/30 border-rose-500/40 shadow-lg shadow-rose-950/20'
      }`}
      data-testid="feedback-card"
    >
      {/* Top Feedback Banner */}
      <div className="flex items-start justify-between gap-3 mb-4">
        <div className="flex items-center gap-3">
          {result.outcome === 'correct' && (
            <div className="w-10 h-10 rounded-xl bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center text-emerald-400">
              <CheckCircle2 className="w-6 h-6" />
            </div>
          )}
          {result.outcome === 'partially_correct' && (
            <div className="w-10 h-10 rounded-xl bg-amber-500/20 border border-amber-500/40 flex items-center justify-center text-amber-400">
              <AlertTriangle className="w-6 h-6" />
            </div>
          )}
          {result.outcome === 'incorrect' && (
            <div className="w-10 h-10 rounded-xl bg-rose-500/20 border border-rose-500/40 flex items-center justify-center text-rose-400">
              <XCircle className="w-6 h-6" />
            </div>
          )}

          <div>
            <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
              {result.outcome === 'correct' && 'Outstanding! Correct Answer.'}
              {result.outcome === 'partially_correct' && 'Partially Correct – Almost There!'}
              {result.outcome === 'incorrect' && 'Not Quite – Let’s Learn From This.'}
            </h3>
            <p className="text-xs text-slate-300 mt-0.5">{result.explanation}</p>
          </div>
        </div>

        {/* BKT Mastery Delta Pill */}
        <div className="flex flex-col items-end">
          <div className="flex items-center gap-1.5 px-3 py-1 rounded-xl bg-slate-900 border border-slate-700">
            {deltaPct >= 0 ? (
              <TrendingUp className="w-3.5 h-3.5 text-emerald-400" />
            ) : (
              <TrendingDown className="w-3.5 h-3.5 text-rose-400" />
            )}
            <span className="text-xs font-mono font-bold text-slate-200">
              {prevPct}% → <span className={deltaPct >= 0 ? 'text-emerald-400' : 'text-rose-400'}>{newPct}%</span>
            </span>
          </div>
          <span className="text-[10px] text-slate-400 mt-1">BKT Posterior Mastery</span>
        </div>
      </div>

      {/* Socratic Hint / Concept Clarification Body */}
      <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-3 mb-5">
        <div>
          <span className="text-[11px] font-bold uppercase tracking-wider text-cyan-400 block mb-1 flex items-center gap-1">
            <Sparkles className="w-3 h-3" />
            Concept Clarification
          </span>
          <p className="text-xs text-slate-200 leading-relaxed">{result.conceptClarification}</p>
        </div>

        {result.socraticHint && (
          <div className="pt-2.5 border-t border-slate-800">
            <span className="text-[11px] font-bold uppercase tracking-wider text-amber-400 block mb-1">
              Socratic Guide
            </span>
            <p className="text-xs text-amber-200/90 leading-relaxed">{result.socraticHint}</p>
          </div>
        )}

        <div className="flex items-center justify-between pt-2 border-t border-slate-800 text-[11px] text-slate-400">
          <span>Target Classification Tier</span>
          <Badge label={result.newClassification} variant="mastery" tier={result.newClassification} size="sm" />
        </div>
      </div>

      {/* Bottom Action Buttons */}
      <div className="flex flex-wrap items-center justify-end gap-3">
        {result.outcome === 'correct' ? (
          <button
            onClick={onNextQuestion}
            className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-electric-600 to-cyan-500 hover:from-electric-500 hover:to-cyan-400 text-white font-semibold text-xs tracking-wide flex items-center gap-2 shadow-glow-cyan transition-all transform active:scale-95"
            data-testid="next-question-button"
          >
            <span>Next Recommended Question</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        ) : result.outcome === 'partially_correct' ? (
          <div className="flex items-center gap-2.5 w-full sm:w-auto">
            <button
              onClick={onRetry}
              className="flex-1 sm:flex-none px-4 py-2.5 rounded-xl bg-amber-500/20 hover:bg-amber-500/30 text-amber-200 font-semibold text-xs border border-amber-500/40 flex items-center justify-center gap-2 transition-colors"
              data-testid="retry-attempt-button"
            >
              <RotateCcw className="w-4 h-4" />
              <span>Retry Question</span>
            </button>
            <button
              onClick={onNextQuestion}
              className="flex-1 sm:flex-none px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold text-xs flex items-center justify-center gap-2 transition-colors"
              data-testid="next-question-button"
            >
              <span>Skip to Next</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-2.5 w-full sm:w-auto">
            {result.recommendedAction.targetConceptId && onReviewPrerequisite && (
              <button
                onClick={() => onReviewPrerequisite(result.recommendedAction.targetConceptId!)}
                className="flex-1 sm:flex-none px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-cyan-300 font-semibold text-xs border border-cyan-500/30 flex items-center justify-center gap-2 transition-colors"
                data-testid="review-prerequisite-button"
              >
                <BookOpen className="w-4 h-4" />
                <span>Review Prerequisite</span>
              </button>
            )}
            <button
              onClick={onRetry}
              className="flex-1 sm:flex-none px-4 py-2.5 rounded-xl bg-rose-500/20 hover:bg-rose-500/30 text-rose-200 font-semibold text-xs border border-rose-500/40 flex items-center justify-center gap-2 transition-colors"
              data-testid="retry-attempt-button"
            >
              <RotateCcw className="w-4 h-4" />
              <span>Retry</span>
            </button>
            <button
              onClick={onNextQuestion}
              className="flex-1 sm:flex-none px-4 py-2.5 rounded-xl bg-electric-600 hover:bg-electric-500 text-white font-semibold text-xs flex items-center justify-center gap-2 transition-colors"
              data-testid="next-question-button"
            >
              <span>Next Question</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
