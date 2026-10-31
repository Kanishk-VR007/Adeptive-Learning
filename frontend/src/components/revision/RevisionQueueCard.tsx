import React from 'react';
import { RotateCcw, Clock, CheckCircle2, Flame, Brain, ArrowRight } from 'lucide-react';
import { RevisionItem } from '../../types';

interface RevisionQueueCardProps {
  revisions: RevisionItem[];
  onReviewItem: (id: string, rating: 'hard' | 'good' | 'easy') => void;
  onPracticeConcept: (conceptId: number) => void;
}

export const RevisionQueueCard: React.FC<RevisionQueueCardProps> = ({
  revisions,
  onReviewItem,
  onPracticeConcept,
}) => {
  return (
    <div
      className="p-5 rounded-2xl bg-background-card border border-slate-800/80 shadow-card-soft"
      data-testid="revision-queue-card"
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-amber-500/15 border border-amber-500/30 flex items-center justify-center text-amber-400">
            <Brain className="w-4 h-4" />
          </div>
          <div>
            <h3 className="font-semibold text-sm text-slate-100">Spaced Repetition Review Queue</h3>
            <p className="text-[11px] text-slate-400">Ebbinghaus forgetting curve optimization</p>
          </div>
        </div>

        <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-amber-500/10 text-amber-300 border border-amber-500/30">
          {revisions.filter((r) => r.dueStatus === 'due_today').length} Due Today
        </span>
      </div>

      <div className="space-y-3">
        {revisions.map((item) => {
          const isDue = item.dueStatus === 'due_today';

          return (
            <div
              key={item.id}
              className={`p-4 rounded-xl border transition-all ${
                isDue
                  ? 'bg-slate-900 border-amber-500/30 hover:border-amber-500/50'
                  : 'bg-slate-900/50 border-slate-800'
              }`}
              data-testid={`revision-item-${item.id}`}
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-3">
                <div>
                  <div className="flex items-center gap-2">
                    <h4 className="text-sm font-semibold text-slate-200">{item.conceptName}</h4>
                    <span
                      className={`text-[10px] px-2 py-0.5 rounded-full font-semibold uppercase ${
                        isDue
                          ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                          : 'bg-slate-800 text-slate-400'
                      }`}
                    >
                      {item.dueStatus.replace('_', ' ')}
                    </span>
                  </div>
                  <div className="text-xs text-slate-400 mt-0.5 flex items-center gap-2">
                    <span>{item.subjectName}</span>
                    <span>•</span>
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      Last reviewed: {item.lastPracticed}
                    </span>
                  </div>
                </div>

                {/* Retention Gauge */}
                <div className="flex items-center gap-2 shrink-0">
                  <div className="text-right">
                    <div className="text-xs font-bold text-slate-200">{item.retentionEstimate}%</div>
                    <div className="text-[9px] text-slate-400">Retention</div>
                  </div>
                  <div className="w-16 bg-slate-800 h-2 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${
                        item.retentionEstimate >= 70
                          ? 'bg-emerald-500'
                          : item.retentionEstimate >= 40
                          ? 'bg-amber-500'
                          : 'bg-rose-500'
                      }`}
                      style={{ width: `${item.retentionEstimate}%` }}
                    />
                  </div>
                </div>
              </div>

              {/* Action Buttons: Spaced Repetition Feedback */}
              <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-800 text-xs">
                <span className="text-[11px] text-slate-400 font-medium">Quick Retention Feedback:</span>

                <div className="flex items-center gap-1.5">
                  <button
                    onClick={() => onReviewItem(item.id, 'hard')}
                    className="px-2.5 py-1 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 border border-rose-500/30 transition-colors"
                  >
                    Hard (1d)
                  </button>
                  <button
                    onClick={() => onReviewItem(item.id, 'good')}
                    className="px-2.5 py-1 rounded-lg bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 transition-colors"
                  >
                    Good ({item.intervalDays * 2}d)
                  </button>
                  <button
                    onClick={() => onReviewItem(item.id, 'easy')}
                    className="px-2.5 py-1 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 transition-colors"
                  >
                    Easy ({item.intervalDays * 3}d)
                  </button>
                  <button
                    onClick={() => onPracticeConcept(item.conceptId)}
                    className="ml-2 px-3 py-1 rounded-lg bg-electric-600 hover:bg-electric-500 text-white font-medium flex items-center gap-1 transition-colors"
                  >
                    <span>Quiz</span>
                    <ArrowRight className="w-3 h-3" />
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
