import React, { useState, useEffect } from 'react';
import { RotateCw, Check, Sparkles, BookOpen, Clock, Lightbulb, ArrowRight, Eye } from 'lucide-react';
import { RevisionItem } from '../../types';
import { Button } from '../ui/Button';

export interface SpacedFlashcardDeckProps {
  items: RevisionItem[];
  onReview: (id: string, rating: 'hard' | 'good' | 'easy') => void;
  onPracticeConcept: (conceptId: number) => void;
  className?: string;
}

export const SpacedFlashcardDeck: React.FC<SpacedFlashcardDeckProps> = ({
  items,
  onReview,
  onPracticeConcept,
  className = '',
}) => {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isFlipped, setIsFlipped] = useState(false);

  const currentCard = items[currentIndex];

  // Global spacebar & 1-4 hotkey listener
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't intercept when user is typing in an input
      if (['INPUT', 'TEXTAREA'].includes((e.target as HTMLElement)?.tagName)) return;

      if (e.code === 'Space') {
        e.preventDefault();
        setIsFlipped((f) => !f);
      } else if (isFlipped && currentCard) {
        if (e.key === '1' || e.key === '2') {
          handleRate('hard');
        } else if (e.key === '3') {
          handleRate('good');
        } else if (e.key === '4') {
          handleRate('easy');
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isFlipped, currentCard]);

  const handleRate = (rating: 'hard' | 'good' | 'easy') => {
    if (!currentCard) return;
    onReview(currentCard.id, rating);
    setIsFlipped(false);
    if (currentIndex < items.length - 1) {
      setCurrentIndex((idx) => idx + 1);
    } else {
      setCurrentIndex(0);
    }
  };

  if (!items || items.length === 0) {
    return (
      <div
        className={`p-10 rounded-2xl bg-slate-900/60 border border-slate-800 text-center ${className}`}
        data-testid="empty-revision-deck"
      >
        <Sparkles className="w-10 h-10 text-cyan-400 mx-auto mb-3" />
        <h3 className="text-base font-bold text-slate-100">All Spaced Revisions Completed!</h3>
        <p className="text-sm text-slate-400 mt-1 max-w-md mx-auto">
          Your adaptive Leitner intervals are up to date. Excellent retention work!
        </p>
      </div>
    );
  }

  return (
    <div className={`space-y-6 ${className}`} data-testid="spaced-flashcard-deck">
      {/* Deck Header & Card Count */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold uppercase tracking-wider text-cyan-400 font-mono">
            Card {currentIndex + 1} of {items.length}
          </span>
          <span className="text-slate-500">•</span>
          <span className="text-xs text-slate-400 font-medium">
            {currentCard.conceptName}
          </span>
        </div>

        <button
          onClick={() => setIsFlipped(!isFlipped)}
          className="text-xs text-slate-400 hover:text-cyan-400 font-medium flex items-center gap-1.5 transition-colors"
        >
          <RotateCw className="w-3.5 h-3.5" />
          <span>Flip Card (Space)</span>
        </button>
      </div>

      {/* 3D Perspective Card Container */}
      <div
        className="w-full h-80 sm:h-96 cursor-pointer select-none [perspective:1200px]"
        onClick={() => setIsFlipped(!isFlipped)}
        data-testid="flashcard-3d-wrapper"
      >
        <div
          className={`w-full h-full relative transition-transform duration-500 [transform-style:preserve-3d] ${
            isFlipped ? '[transform:rotateY(180deg)]' : ''
          }`}
        >
          {/* FRONT FACE */}
          <div className="absolute inset-0 w-full h-full rounded-3xl p-6 sm:p-8 bg-slate-900 border border-slate-800 [backface-visibility:hidden] flex flex-col justify-between shadow-2xl hover:border-cyan-500/40 transition-colors">
            <div>
              <div className="flex items-center justify-between mb-4">
                <span className="text-xs px-2.5 py-1 rounded-full bg-blue-500/10 border border-blue-500/30 text-blue-400 font-medium">
                  {currentCard.subjectName}
                </span>
                <span className="text-xs text-amber-400 flex items-center gap-1 font-mono font-medium">
                  <Clock className="w-3 h-3" /> Due Interval: {currentCard.intervalDays}d
                </span>
              </div>

              <h3 className="text-lg sm:text-xl font-bold text-slate-100 leading-snug">
                {currentCard.conceptName}
              </h3>
              <p className="text-sm text-slate-400 mt-2">
                What is the formal definition and fundamental application rule for this concept?
              </p>
            </div>

            <div className="p-4 rounded-2xl bg-slate-950/70 border border-slate-800/80 font-mono text-xs text-cyan-300">
              ∫ u · v' dx = u · v - ∫ u' · v dx
            </div>

            <div className="flex items-center justify-between text-xs text-slate-500 pt-2 border-t border-slate-800/60">
              <span className="flex items-center gap-1">
                <Eye className="w-3.5 h-3.5" /> Click anywhere or press <kbd className="px-1.5 py-0.5 bg-slate-800 border border-slate-700 rounded text-slate-300">Space</kbd> to reveal
              </span>
              <span className="text-cyan-400 font-medium">Box {currentCard.box} / 5</span>
            </div>
          </div>

          {/* BACK FACE */}
          <div className="absolute inset-0 w-full h-full rounded-3xl p-6 sm:p-8 bg-slate-900 border border-cyan-500/40 [transform:rotateY(180deg)] [backface-visibility:hidden] flex flex-col justify-between shadow-[0_0_40px_rgba(6,182,212,0.15)]">
            <div>
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs px-2.5 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 font-semibold flex items-center gap-1">
                  <Sparkles className="w-3 h-3" /> Derivation & Key Insight
                </span>
                <span className="text-xs text-slate-400 font-mono font-medium">
                  Retention Target: &ge; 85%
                </span>
              </div>

              <h4 className="text-base font-bold text-slate-100">Core Mathematical Solution</h4>
              <p className="text-xs sm:text-sm text-slate-300 mt-2 leading-relaxed">
                Integration by parts reverses the differential product rule. Choose $u$ via the <strong>LIATE</strong> priority rule (Logarithmic, Inverse trig, Algebraic, Trigonometric, Exponential) to ensure $du$ simplifies.
              </p>
            </div>

            <div className="p-3.5 rounded-2xl bg-emerald-950/20 border border-emerald-500/30 text-xs text-emerald-300">
              <span className="font-semibold text-emerald-200">Mnemonic / Pro Tip: </span>
              Always verify that $\int v \, du$ is strictly easier to integrate than the original integrand.
            </div>

            <div className="flex items-center justify-between pt-2 border-t border-slate-800">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onPracticeConcept(currentCard.conceptId);
                }}
                className="text-xs text-cyan-400 hover:text-cyan-300 font-medium flex items-center gap-1"
              >
                <span>Launch Diagnostic Drill</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
              <span className="text-[11px] text-slate-400">Rate confidence below:</span>
            </div>
          </div>
        </div>
      </div>

      {/* Confidence Rating Buttons (Linear & Anki inspired) */}
      <div className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-3">
        <span className="text-xs text-slate-400 font-medium">
          How well did you recall this concept?
        </span>

        <div className="grid grid-cols-3 gap-2 w-full sm:w-auto">
          <Button
            variant="danger"
            size="sm"
            onClick={() => handleRate('hard')}
            className="text-xs font-semibold justify-center"
            data-testid="rate-hard-button"
          >
            <span>Hard</span>
            <kbd className="hidden sm:inline-block px-1 py-0.2 text-[9px] bg-rose-900/50 rounded text-rose-200">1</kbd>
          </Button>

          <Button
            variant="secondary"
            size="sm"
            onClick={() => handleRate('good')}
            className="text-xs font-semibold justify-center border-blue-500/40 text-blue-300 hover:border-blue-400"
            data-testid="rate-good-button"
          >
            <span>Good</span>
            <kbd className="hidden sm:inline-block px-1 py-0.2 text-[9px] bg-slate-800 rounded text-slate-300">2</kbd>
          </Button>

          <Button
            variant="tactile"
            size="sm"
            onClick={() => handleRate('easy')}
            className="text-xs font-semibold justify-center bg-emerald-600 hover:bg-emerald-500 border-emerald-400/40 shadow-[0_4px_0_#065f46]"
            data-testid="rate-easy-button"
          >
            <span>Easy</span>
            <kbd className="hidden sm:inline-block px-1 py-0.2 text-[9px] bg-emerald-900/50 rounded text-emerald-200">3</kbd>
          </Button>
        </div>
      </div>
    </div>
  );
};
