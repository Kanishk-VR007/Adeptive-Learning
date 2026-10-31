import React, { useState } from 'react';
import { CheckCircle2, XCircle, Lightbulb, ChevronDown, ChevronUp, ArrowRight, BookOpen, AlertCircle } from 'lucide-react';
import { Button } from '../ui/Button';

export interface ExplainerStep {
  stepNumber: number;
  title: string;
  detail: string;
  formula?: string;
}

export interface ExplainerDrawerProps {
  isCorrect: boolean;
  explanation: string;
  conceptName: string;
  steps?: ExplainerStep[];
  commonMisconception?: string;
  onNextQuestion: () => void;
  className?: string;
}

export const ExplainerDrawer: React.FC<ExplainerDrawerProps> = ({
  isCorrect,
  explanation,
  conceptName,
  steps,
  commonMisconception,
  onNextQuestion,
  className = '',
}) => {
  const [isExpanded, setIsExpanded] = useState<boolean>(true);

  const defaultSteps: ExplainerStep[] = steps || [
    {
      stepNumber: 1,
      title: 'Identify Core Pattern',
      detail: `Recall the definition and foundational rule governing ${conceptName}.`,
    },
    {
      stepNumber: 2,
      title: 'Apply Mathematical Transformation',
      detail: 'Substitute variables and evaluate intermediate boundary terms.',
      formula: 'd/dx [u(x) · v(x)] = u\'(x)v(x) + u(x)v\'(x)',
    },
    {
      stepNumber: 3,
      title: 'Synthesize Final Derivation',
      detail: 'Simplify algebraic fractions and cross-verify with problem constraints.',
    },
  ];

  return (
    <div
      className={`rounded-2xl border transition-all duration-300 overflow-hidden shadow-2xl ${
        isCorrect
          ? 'bg-emerald-950/25 border-emerald-500/40 shadow-emerald-950/30'
          : 'bg-slate-900/95 border-rose-500/40 shadow-rose-950/30'
      } ${className}`}
      data-testid="explainer-drawer"
    >
      {/* Header Banner */}
      <div
        className="px-5 py-4 flex items-center justify-between cursor-pointer select-none"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-3">
          {isCorrect ? (
            <div className="w-8 h-8 rounded-xl bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center text-emerald-400">
              <CheckCircle2 className="w-5 h-5" />
            </div>
          ) : (
            <div className="w-8 h-8 rounded-xl bg-rose-500/20 border border-rose-500/40 flex items-center justify-center text-rose-400">
              <XCircle className="w-5 h-5" />
            </div>
          )}

          <div>
            <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
              {isCorrect ? 'Correct! Concept Reinforced' : 'Incorrect — Remediation Activated'}
            </h3>
            <p className="text-xs text-slate-400">
              {conceptName} • Adaptive BKT Model Updated
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 transition-colors"
            aria-label={isExpanded ? 'Collapse explanation' : 'Expand explanation'}
          >
            {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Expanded Cognitive Breakdown (Brilliant style) */}
      {isExpanded && (
        <div className="px-5 pb-5 pt-1 space-y-4 border-t border-slate-800/60 animate-in fade-in duration-200">
          {/* Main takeaway */}
          <div className="p-3.5 rounded-xl bg-slate-950/50 border border-slate-800/80 text-sm text-slate-200 leading-relaxed">
            <span className="font-semibold text-cyan-400">Key Explanation: </span>
            {explanation}
          </div>

          {/* Step-by-step derivation steps */}
          <div className="space-y-2">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
              <Lightbulb className="w-3.5 h-3.5 text-amber-400" />
              Cognitive Step-by-Step Derivation
            </h4>
            <div className="space-y-2">
              {defaultSteps.map((step) => (
                <div
                  key={step.stepNumber}
                  className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 flex items-start gap-3"
                >
                  <span className="w-5 h-5 rounded-full bg-blue-500/20 border border-blue-500/40 text-blue-400 text-xs font-bold flex items-center justify-center shrink-0 mt-0.5">
                    {step.stepNumber}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-semibold text-slate-200">{step.title}</p>
                    <p className="text-xs text-slate-400 mt-0.5">{step.detail}</p>
                    {step.formula && (
                      <div className="mt-1.5 px-2.5 py-1 rounded bg-slate-950 border border-slate-800 font-mono text-[11px] text-cyan-300">
                        {step.formula}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Common misconception alert */}
          {commonMisconception && (
            <div className="p-3 rounded-xl bg-amber-950/20 border border-amber-500/30 flex items-start gap-2.5 text-xs text-amber-300">
              <AlertCircle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold text-amber-200">Common Misconception: </span>
                {commonMisconception}
              </div>
            </div>
          )}

          {/* Advance Action */}
          <div className="pt-2 flex justify-end">
            <Button
              variant="tactile"
              size="md"
              onClick={onNextQuestion}
              className="w-full sm:w-auto font-semibold"
              data-testid="explainer-next-button"
            >
              <span>Continue to Next Drill</span>
              <ArrowRight className="w-4 h-4" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
};
