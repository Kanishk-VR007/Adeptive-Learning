import React from 'react';
import { Play, Sparkles, ArrowRight, BookOpen, Layers } from 'lucide-react';

interface ContinueLearningCardProps {
  subjectName: string;
  chapterTitle: string;
  conceptName: string;
  conceptDifficulty: string;
  onContinue: () => void;
}

export const ContinueLearningCard: React.FC<ContinueLearningCardProps> = ({
  subjectName,
  chapterTitle,
  conceptName,
  conceptDifficulty,
  onContinue,
}) => {
  return (
    <div
      className="p-5 rounded-2xl bg-gradient-to-br from-background-card via-slate-900 to-background-card border border-cyan-500/30 shadow-glow-blue/20 relative overflow-hidden glass-card-hover"
      data-testid="continue-learning-card"
    >
      {/* Decorative background aura */}
      <div className="absolute top-0 right-0 w-44 h-44 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />

      <div className="flex items-center justify-between mb-3">
        <span className="text-[11px] font-bold uppercase tracking-wider text-cyan-400 flex items-center gap-1.5">
          <Sparkles className="w-3.5 h-3.5 text-cyan-300" />
          Recommended Next Step
        </span>

        <span className="text-xs px-2.5 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700 capitalize">
          {conceptDifficulty}
        </span>
      </div>

      {/* Main Concept Highlight */}
      <h3 className="text-lg font-bold text-slate-100 mb-1 group-hover:text-cyan-300 transition-colors">
        {conceptName}
      </h3>

      {/* Context breadcrumb */}
      <div className="flex flex-wrap items-center gap-2 text-xs text-slate-400 mb-5">
        <span className="flex items-center gap-1 text-slate-300">
          <BookOpen className="w-3.5 h-3.5 text-electric-400" />
          {subjectName}
        </span>
        <span>•</span>
        <span className="flex items-center gap-1 text-slate-400 truncate max-w-[200px]">
          <Layers className="w-3.5 h-3.5 text-cyan-400" />
          {chapterTitle}
        </span>
      </div>

      {/* Continue Learning CTA Button */}
      <button
        onClick={onContinue}
        className="w-full py-2.5 px-4 rounded-xl bg-gradient-to-r from-electric-600 to-cyan-500 hover:from-electric-500 hover:to-cyan-400 text-white font-semibold text-xs tracking-wide flex items-center justify-center gap-2 shadow-glow-cyan transition-all transform active:scale-[0.99]"
        data-testid="continue-learning-button"
      >
        <Play className="w-4 h-4 fill-white" />
        <span>Continue Learning</span>
        <ArrowRight className="w-4 h-4" />
      </button>
    </div>
  );
};
