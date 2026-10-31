import React from 'react';
import { AlertCircle, Target, ArrowRight } from 'lucide-react';
import { ConceptMastery } from '../../types';
import { Badge } from '../common/Badge';

interface WeakConceptsCardProps {
  concepts: ConceptMastery[];
  onPracticeConcept: (conceptId: number) => void;
}

export const WeakConceptsCard: React.FC<WeakConceptsCardProps> = ({
  concepts,
  onPracticeConcept,
}) => {
  return (
    <div
      className="p-5 rounded-2xl bg-background-card border border-slate-800/80 shadow-card-soft glass-card-hover"
      data-testid="weak-concepts-card"
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-rose-500/15 border border-rose-500/30 flex items-center justify-center text-rose-400">
            <AlertCircle className="w-4 h-4" />
          </div>
          <div>
            <h3 className="font-semibold text-sm text-slate-100">Weak Concepts</h3>
            <p className="text-[11px] text-slate-400">Prioritized for maximum score gains</p>
          </div>
        </div>

        <span className="text-xs text-rose-400 font-semibold px-2 py-0.5 rounded-full bg-rose-500/10 border border-rose-500/20">
          {concepts.length} Need Focus
        </span>
      </div>

      <div className="space-y-3">
        {concepts.map((concept) => {
          const masteryPct = Math.round(concept.currentMastery * 100);
          return (
            <div
              key={concept.id}
              className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 hover:border-slate-700 transition-colors flex items-center justify-between gap-3 group"
              data-testid={`weak-concept-row-${concept.conceptId}`}
            >
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-semibold text-xs text-slate-200 truncate group-hover:text-cyan-300 transition-colors">
                    {concept.conceptName}
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  <div className="w-24 bg-slate-800 h-1.5 rounded-full overflow-hidden">
                    <div
                      className="bg-rose-500 h-full rounded-full"
                      style={{ width: `${masteryPct}%` }}
                    />
                  </div>
                  <span className="text-[11px] font-mono text-rose-400 font-semibold">
                    {masteryPct}%
                  </span>
                  <Badge label={concept.masteryClassification} variant="mastery" tier={concept.masteryClassification} size="sm" />
                </div>
              </div>

              {/* Targeted Practice CTA */}
              <button
                onClick={() => onPracticeConcept(concept.conceptId)}
                className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-electric-600 text-slate-200 hover:text-white text-xs font-medium border border-slate-700/80 hover:border-electric-500 flex items-center gap-1.5 transition-all shadow-sm shrink-0"
                data-testid={`practice-concept-${concept.conceptId}`}
              >
                <Target className="w-3.5 h-3.5 text-cyan-400" />
                <span>Practice</span>
                <ArrowRight className="w-3 h-3" />
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
};
