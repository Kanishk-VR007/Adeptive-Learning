import React, { useState } from 'react';
import { RevisionItem } from '../types';
import { RevisionQueueCard } from '../components/revision/RevisionQueueCard';
import { SpacedFlashcardDeck } from '../components/revision/SpacedFlashcardDeck';
import { LeitnerBoxTracker } from '../components/revision/LeitnerBoxTracker';
import { Sparkles, Brain, Clock, Flame, Layers, Eye } from 'lucide-react';

interface RevisionPageProps {
  revisions: RevisionItem[];
  onReviewItem: (id: string, rating: 'hard' | 'good' | 'easy') => void;
  onPracticeConcept: (conceptId: number) => void;
}

export const RevisionPage: React.FC<RevisionPageProps> = ({
  revisions,
  onReviewItem,
  onPracticeConcept,
}) => {
  const [activeView, setActiveView] = useState<'flashcards' | 'queue'>('flashcards');

  const dueCount = revisions.filter((r) => r.dueStatus === 'due_today').length;

  // Calculate Leitner box distribution
  const boxCounts: [number, number, number, number, number] = [0, 0, 0, 0, 0];
  revisions.forEach((r) => {
    const boxIdx = Math.max(0, Math.min(4, (r.box || 1) - 1));
    boxCounts[boxIdx] += 1;
  });

  return (
    <div className="space-y-6 pb-12" data-testid="revision-page">
      {/* Top Header Banner */}
      <div className="p-6 rounded-3xl bg-gradient-to-br from-slate-900 via-slate-900/90 to-background border border-slate-800 shadow-card-soft">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-400 animate-pulse" />
              <span className="text-[11px] font-bold uppercase tracking-wider text-amber-400">
                Active Spaced Repetition Engine
              </span>
            </div>
            <h2 className="text-xl sm:text-2xl font-bold text-slate-100">
              Optimal Memory <span className="gradient-text-blue-cyan">Retention Schedule</span>
            </h2>
            <p className="text-xs sm:text-sm text-slate-400 max-w-xl mt-1">
              Based on the Ebbinghaus forgetting curve, reviewing concepts at calibrated Leitner intervals
              transforms working memory into permanent exam mastery.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <div className="p-3 rounded-2xl bg-slate-900/90 border border-slate-800 text-center min-w-[70px]">
              <div className="text-xl font-bold text-amber-400 font-mono">{dueCount}</div>
              <div className="text-[10px] text-slate-400 uppercase font-semibold">Due Today</div>
            </div>
            <div className="p-3 rounded-2xl bg-slate-900/90 border border-slate-800 text-center min-w-[70px]">
              <div className="text-xl font-bold text-cyan-400 font-mono">{revisions.length}</div>
              <div className="text-[10px] text-slate-400 uppercase font-semibold">In Cycle</div>
            </div>
          </div>
        </div>
      </div>

      {/* 5-Stage Leitner Box Progression Visualizer */}
      <LeitnerBoxTracker boxCounts={boxCounts} activeBox={1} />

      {/* View Switcher Tabs: 3D Flashcards vs Queue List */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setActiveView('flashcards')}
            className={`px-4 py-2 rounded-xl text-xs font-semibold flex items-center gap-2 transition-all ${
              activeView === 'flashcards'
                ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/25 border border-blue-500/50'
                : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
            }`}
            data-testid="tab-flashcards-view"
          >
            <Brain className="w-3.5 h-3.5" />
            <span>3D Flashcard Deck</span>
          </button>

          <button
            onClick={() => setActiveView('queue')}
            className={`px-4 py-2 rounded-xl text-xs font-semibold flex items-center gap-2 transition-all ${
              activeView === 'queue'
                ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/25 border border-blue-500/50'
                : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
            }`}
            data-testid="tab-queue-view"
          >
            <Layers className="w-3.5 h-3.5" />
            <span>Full Queue Table ({revisions.length})</span>
          </button>
        </div>

        <span className="text-xs text-slate-400 hidden sm:inline">
          {activeView === 'flashcards' ? 'Use Space to flip • 1-3 to rate' : 'Prioritized by review deadline'}
        </span>
      </div>

      {/* Active View: 3D Flashcard Deck or Standard Queue Card */}
      {activeView === 'flashcards' ? (
        <SpacedFlashcardDeck
          items={revisions}
          onReview={onReviewItem}
          onPracticeConcept={onPracticeConcept}
        />
      ) : (
        <RevisionQueueCard
          revisions={revisions}
          onReviewItem={onReviewItem}
          onPracticeConcept={onPracticeConcept}
        />
      )}
    </div>
  );
};
