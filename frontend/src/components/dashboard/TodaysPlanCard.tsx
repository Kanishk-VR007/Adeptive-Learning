import React from 'react';
import { Calendar, CheckCircle2, RotateCcw, Target, Sparkles, Clock } from 'lucide-react';
import { LearningRecommendation, RevisionItem } from '../../types';

interface TodaysPlanCardProps {
  suggestedConcepts: LearningRecommendation[];
  dailyPracticeTarget: number;
  completedTodayCount: number;
  upcomingRevisions: RevisionItem[];
  onSelectConcept: (conceptId: number) => void;
  onOpenRevision: () => void;
}

export const TodaysPlanCard: React.FC<TodaysPlanCardProps> = ({
  suggestedConcepts,
  dailyPracticeTarget,
  completedTodayCount,
  upcomingRevisions,
  onSelectConcept,
  onOpenRevision,
}) => {
  const practicePct = Math.min(100, Math.round((completedTodayCount / dailyPracticeTarget) * 100));

  return (
    <div
      className="p-5 rounded-2xl bg-background-card border border-slate-800/80 shadow-card-soft glass-card-hover"
      data-testid="todays-plan-card"
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-cyan-500/15 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
            <Calendar className="w-4 h-4" />
          </div>
          <div>
            <h3 className="font-semibold text-sm text-slate-100">Today's Learning Plan</h3>
            <p className="text-[11px] text-slate-400">Personalized study schedule</p>
          </div>
        </div>

        <span className="text-xs font-semibold text-cyan-300">
          {completedTodayCount} of {dailyPracticeTarget} done
        </span>
      </div>

      {/* Target Progress Bar */}
      <div className="mb-4">
        <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
          <div
            className="bg-gradient-to-r from-electric-600 to-cyan-400 h-full rounded-full transition-all duration-300"
            style={{ width: `${practicePct}%` }}
          />
        </div>
      </div>

      {/* Section 1: Suggested Concepts */}
      <div className="mb-4">
        <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 block mb-2">
          Suggested Focus Concepts
        </span>
        <div className="space-y-2">
          {suggestedConcepts.map((rec) => (
            <div
              key={rec.id}
              onClick={() => onSelectConcept(rec.conceptId)}
              className="p-2.5 rounded-xl bg-slate-900/60 border border-slate-800 hover:border-cyan-500/40 cursor-pointer flex items-center justify-between transition-colors group"
            >
              <div className="flex items-center gap-2.5 min-w-0">
                <Target className="w-4 h-4 text-cyan-400 shrink-0" />
                <div className="min-w-0">
                  <div className="text-xs font-semibold text-slate-200 truncate group-hover:text-cyan-300 transition-colors">
                    {rec.conceptName}
                  </div>
                  <div className="text-[10px] text-slate-400 flex items-center gap-1.5">
                    <span>{rec.chapterTitle}</span>
                    <span>•</span>
                    <span className="flex items-center gap-0.5">
                      <Clock className="w-2.5 h-2.5" />
                      ~{rec.estimatedMinutes}m
                    </span>
                  </div>
                </div>
              </div>

              <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700 shrink-0">
                Start
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Section 2: Spaced Revisions */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
            Upcoming Revisions
          </span>
          <button
            onClick={onOpenRevision}
            className="text-[11px] text-cyan-400 font-semibold hover:underline flex items-center gap-1"
          >
            <RotateCcw className="w-3 h-3" />
            Review Queue
          </button>
        </div>

        <div className="p-2.5 rounded-xl bg-slate-900/60 border border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400">
              <RotateCcw className="w-3.5 h-3.5" />
            </div>
            <div>
              <div className="text-xs font-semibold text-slate-200">
                {upcomingRevisions.length} Concepts scheduled for review
              </div>
              <div className="text-[10px] text-slate-400">Optimal forgetting curve retention</div>
            </div>
          </div>

          <button
            onClick={onOpenRevision}
            className="px-2.5 py-1 rounded-lg bg-amber-500/15 hover:bg-amber-500/25 text-amber-300 text-xs font-semibold border border-amber-500/30 transition-colors"
          >
            Review
          </button>
        </div>
      </div>
    </div>
  );
};
