import React from 'react';
import { BookOpen, CheckCircle2, Clock, AlertCircle } from 'lucide-react';
import { SubjectProgressSummary } from '../../services/progressService';
import { ProgressBar } from '../common/ProgressBar';

interface SubjectProgressCardProps {
  summary: SubjectProgressSummary;
  onSelectSubject?: (id: number) => void;
}

export const SubjectProgressCard: React.FC<SubjectProgressCardProps> = ({
  summary,
  onSelectSubject,
}) => {
  return (
    <div
      onClick={() => onSelectSubject && onSelectSubject(summary.subjectId)}
      className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 hover:border-cyan-500/30 transition-all cursor-pointer group"
      data-testid={`subject-progress-${summary.subjectId}`}
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <BookOpen className="w-4 h-4 text-cyan-400 group-hover:text-cyan-300 transition-colors" />
          <h4 className="text-xs font-semibold text-slate-200 group-hover:text-cyan-200 transition-colors">
            {summary.subjectName}
          </h4>
        </div>
        <span className="text-xs font-bold font-mono text-cyan-300">{summary.averageMastery}%</span>
      </div>

      <ProgressBar value={summary.averageMastery} height="h-1.5" className="mb-3" />

      {/* Breakdown counters */}
      <div className="grid grid-cols-3 gap-1.5 text-center text-[10px]">
        <div className="p-1.5 rounded-lg bg-emerald-950/30 border border-emerald-800/30 text-emerald-300">
          <div className="font-bold">{summary.masteredCount}</div>
          <div className="text-[9px] text-slate-400">Mastered</div>
        </div>

        <div className="p-1.5 rounded-lg bg-cyan-950/30 border border-cyan-800/30 text-cyan-300">
          <div className="font-bold">{summary.inProgressCount}</div>
          <div className="text-[9px] text-slate-400">Developing</div>
        </div>

        <div className="p-1.5 rounded-lg bg-rose-950/30 border border-rose-800/30 text-rose-300">
          <div className="font-bold">{summary.weakCount}</div>
          <div className="text-[9px] text-slate-400">Weak</div>
        </div>
      </div>
    </div>
  );
};
