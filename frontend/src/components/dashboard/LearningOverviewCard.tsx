import React from 'react';
import { Award, BookCheck, HelpCircle, Timer, TrendingUp } from 'lucide-react';
import { ProgressBar } from '../common/ProgressBar';

interface LearningOverviewCardProps {
  overallMastery: number; // 0 to 100
  conceptsCompleted: number;
  totalConcepts: number;
  questionsAnswered: number;
  studyMinutes: number;
}

export const LearningOverviewCard: React.FC<LearningOverviewCardProps> = ({
  overallMastery,
  conceptsCompleted,
  totalConcepts,
  questionsAnswered,
  studyMinutes,
}) => {
  return (
    <div
      className="p-5 rounded-2xl bg-background-card border border-slate-800/80 shadow-card-soft glass-card-hover"
      data-testid="learning-overview-card"
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-electric-600/20 border border-electric-500/30 flex items-center justify-center text-electric-400">
            <Award className="w-4 h-4" />
          </div>
          <div>
            <h3 className="font-semibold text-sm text-slate-100">Learning Overview</h3>
            <p className="text-[11px] text-slate-400">Bayesian Knowledge Tracing (BKT)</p>
          </div>
        </div>

        <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-300 border border-cyan-500/30 flex items-center gap-1">
          <TrendingUp className="w-3 h-3" />
          +12% this week
        </span>
      </div>

      {/* Main Mastery Progress */}
      <div className="mb-5 bg-slate-900/60 p-3.5 rounded-xl border border-slate-800/60">
        <div className="flex justify-between items-baseline mb-1.5">
          <span className="text-xs text-slate-300 font-medium">Aggregate Syllabus Mastery</span>
          <span className="text-xl font-extrabold gradient-text-blue-cyan">{overallMastery}%</span>
        </div>
        <ProgressBar value={overallMastery} height="h-2.5" />
      </div>

      {/* Key Metrics Grid */}
      <div className="grid grid-cols-3 gap-2.5">
        {/* Concepts */}
        <div className="p-2.5 rounded-xl bg-slate-900/40 border border-slate-800 flex flex-col justify-between">
          <div className="flex items-center gap-1.5 text-slate-400 text-[11px]">
            <BookCheck className="w-3.5 h-3.5 text-cyan-400" />
            <span>Concepts</span>
          </div>
          <div className="mt-2 text-base font-bold text-slate-100">
            {conceptsCompleted}
            <span className="text-xs font-normal text-slate-400">/{totalConcepts}</span>
          </div>
        </div>

        {/* Questions Answered */}
        <div className="p-2.5 rounded-xl bg-slate-900/40 border border-slate-800 flex flex-col justify-between">
          <div className="flex items-center gap-1.5 text-slate-400 text-[11px]">
            <HelpCircle className="w-3.5 h-3.5 text-electric-400" />
            <span>Questions</span>
          </div>
          <div className="mt-2 text-base font-bold text-slate-100">
            {questionsAnswered}
          </div>
        </div>

        {/* Study Time */}
        <div className="p-2.5 rounded-xl bg-slate-900/40 border border-slate-800 flex flex-col justify-between">
          <div className="flex items-center gap-1.5 text-slate-400 text-[11px]">
            <Timer className="w-3.5 h-3.5 text-amber-400" />
            <span>Practice</span>
          </div>
          <div className="mt-2 text-base font-bold text-slate-100">
            {Math.floor(studyMinutes / 60)}h {studyMinutes % 60}m
          </div>
        </div>
      </div>
    </div>
  );
};
