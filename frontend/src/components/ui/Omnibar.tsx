import React, { useState, useEffect, useRef } from 'react';
import { Search, Sparkles, BookOpen, AlertTriangle, ArrowRight, X, Clock, Flame } from 'lucide-react';
import { ConceptMastery, Subject } from '../../types';

export interface OmnibarProps {
  concepts: ConceptMastery[];
  subjects: Subject[];
  onStartLearning: (conceptId: number) => void;
  onNavigateToRevision?: () => void;
  isOpen?: boolean;
  onClose?: () => void;
}

export const Omnibar: React.FC<OmnibarProps> = ({
  concepts,
  subjects,
  onStartLearning,
  onNavigateToRevision,
  isOpen: controlledIsOpen,
  onClose: controlledOnClose,
}) => {
  const [internalIsOpen, setInternalIsOpen] = useState(false);
  const isModalOpen = controlledIsOpen !== undefined ? controlledIsOpen : internalIsOpen;
  const closeModal = () => {
    if (controlledOnClose) controlledOnClose();
    else setInternalIsOpen(false);
  };

  const [query, setQuery] = useState('');
  const [selectedFilter, setSelectedFilter] = useState<'all' | 'weak' | 'calculus' | 'algebra'>('all');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  // Listen for global Cmd+K / Ctrl+K
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        if (controlledIsOpen !== undefined) {
          if (controlledIsOpen && controlledOnClose) controlledOnClose();
        } else {
          setInternalIsOpen((prev) => !prev);
        }
      }
      if (e.key === 'Escape' && isModalOpen) {
        closeModal();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isModalOpen, controlledIsOpen, controlledOnClose]);

  // Focus input when opened
  useEffect(() => {
    if (isModalOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
      setSelectedIndex(0);
    } else {
      setQuery('');
    }
  }, [isModalOpen]);

  const getSubjectName = (subjectId: number) => {
    return subjects.find((s) => s.id === subjectId)?.name || 'Mathematics';
  };

  // Filtered concepts based on query and filter pill
  const filteredConcepts = concepts.filter((c) => {
    const subName = getSubjectName(c.subjectId);
    const matchesQuery =
      c.conceptName.toLowerCase().includes(query.toLowerCase()) ||
      subName.toLowerCase().includes(query.toLowerCase());

    if (!matchesQuery) return false;

    if (selectedFilter === 'weak') return c.currentMastery < 0.45;
    if (selectedFilter === 'calculus') return subName.toLowerCase().includes('calculus');
    if (selectedFilter === 'algebra') return subName.toLowerCase().includes('algebra');
    return true;
  });

  // Handle keyboard navigation inside the list
  const handleInputKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev < filteredConcepts.length - 1 ? prev + 1 : 0));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev > 0 ? prev - 1 : filteredConcepts.length - 1));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      const target = filteredConcepts[selectedIndex];
      if (target) {
        onStartLearning(target.conceptId);
        closeModal();
      }
    }
  };

  return (
    <>
      {/* Header Embedded Search Button Trigger */}
      <button
        onClick={() => setInternalIsOpen(true)}
        className="hidden md:flex items-center justify-between w-64 lg:w-80 px-3.5 py-1.5 rounded-full bg-slate-900/90 border border-slate-700/80 hover:border-cyan-500/50 text-xs text-slate-400 hover:text-slate-200 transition-all shadow-inner group"
        aria-label="Open concept search omnibar"
        data-testid="omnibar-trigger-button"
      >
        <div className="flex items-center gap-2 truncate">
          <Search className="w-3.5 h-3.5 text-cyan-400 group-hover:scale-110 transition-transform" />
          <span className="truncate">Search concepts or ask AI...</span>
        </div>
        <kbd className="hidden sm:inline-block px-1.5 py-0.5 text-[10px] font-mono font-medium text-slate-400 bg-slate-800 border border-slate-700 rounded shadow-sm">
          ⌘K
        </kbd>
      </button>

      {/* Modal Backdrop & Command Bar Overlay */}
      {isModalOpen && (
        <div
          className="fixed inset-0 z-50 flex items-start justify-center pt-16 sm:pt-24 px-4 bg-slate-950/80 backdrop-blur-md animate-in fade-in duration-150"
          onClick={closeModal}
        >
          <div
            className="w-full max-w-2xl bg-slate-900 border border-slate-700/80 rounded-2xl shadow-2xl overflow-hidden animate-in zoom-in-95 duration-150 flex flex-col max-h-[80vh]"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-label="AdeptLearn Concept Search Omnibar"
          >
            {/* Input Header */}
            <div className="flex items-center gap-3 px-4 py-3.5 border-b border-slate-800 bg-slate-950/50">
              <Sparkles className="w-5 h-5 text-cyan-400 shrink-0 animate-pulse" />
              <input
                ref={inputRef}
                type="text"
                value={query}
                onChange={(e) => {
                  setQuery(e.target.value);
                  setSelectedIndex(0);
                }}
                onKeyDown={handleInputKeyDown}
                placeholder="Type a concept, formula, or topic (e.g., 'Matrix Inversion', 'Chain Rule')..."
                className="w-full bg-transparent text-slate-100 placeholder-slate-500 text-sm focus:outline-none"
                data-testid="omnibar-search-input"
              />
              <button
                onClick={closeModal}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
                aria-label="Close search"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Quick Action Filter Pills (StudyFetch style) */}
            <div className="flex items-center gap-2 px-4 py-2 border-b border-slate-800/80 bg-slate-900/60 overflow-x-auto text-xs">
              <span className="text-[11px] font-medium text-slate-500 uppercase tracking-wider shrink-0 mr-1">
                Filter:
              </span>
              <button
                onClick={() => setSelectedFilter('all')}
                className={`px-2.5 py-1 rounded-full font-medium transition-colors shrink-0 ${
                  selectedFilter === 'all'
                    ? 'bg-blue-600 text-white shadow-sm'
                    : 'bg-slate-800 text-slate-400 hover:text-slate-200'
                }`}
              >
                All Topics ({concepts.length})
              </button>
              <button
                onClick={() => setSelectedFilter('weak')}
                className={`px-2.5 py-1 rounded-full font-medium transition-colors shrink-0 flex items-center gap-1.5 ${
                  selectedFilter === 'weak'
                    ? 'bg-amber-600 text-white shadow-sm'
                    : 'bg-slate-800 text-slate-400 hover:text-slate-200'
                }`}
              >
                <AlertTriangle className="w-3 h-3 text-amber-300" />
                Weak Concepts
              </button>
              <button
                onClick={() => setSelectedFilter('calculus')}
                className={`px-2.5 py-1 rounded-full font-medium transition-colors shrink-0 ${
                  selectedFilter === 'calculus'
                    ? 'bg-cyan-600 text-white shadow-sm'
                    : 'bg-slate-800 text-slate-400 hover:text-slate-200'
                }`}
              >
                Calculus
              </button>
              <button
                onClick={() => setSelectedFilter('algebra')}
                className={`px-2.5 py-1 rounded-full font-medium transition-colors shrink-0 ${
                  selectedFilter === 'algebra'
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'bg-slate-800 text-slate-400 hover:text-slate-200'
                }`}
              >
                Linear Algebra
              </button>
            </div>

            {/* Concept Results List */}
            <div className="flex-1 overflow-y-auto p-2 space-y-1 divide-y divide-slate-800/30">
              {filteredConcepts.length === 0 ? (
                <div className="p-8 text-center text-slate-400">
                  <BookOpen className="w-8 h-8 text-slate-600 mx-auto mb-2" />
                  <p className="text-sm font-medium">No matching concepts found</p>
                  <p className="text-xs text-slate-500 mt-1">
                    Try searching for specific terms like "Derivative", "Eigenvalues", or clear filters.
                  </p>
                </div>
              ) : (
                filteredConcepts.map((item, idx) => {
                  const isSelected = idx === selectedIndex;
                  const pct = Math.round(item.currentMastery * 100);
                  const subName = getSubjectName(item.subjectId);

                  return (
                    <div
                      key={item.conceptId}
                      onClick={() => {
                        onStartLearning(item.conceptId);
                        closeModal();
                      }}
                      onMouseEnter={() => setSelectedIndex(idx)}
                      className={`flex items-center justify-between p-3 rounded-xl cursor-pointer transition-all ${
                        isSelected
                          ? 'bg-blue-600/15 border border-cyan-500/40 shadow-sm'
                          : 'hover:bg-slate-800/60 border border-transparent'
                      }`}
                      data-testid={`omnibar-result-${item.conceptId}`}
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <div
                          className={`w-8 h-8 rounded-lg flex items-center justify-center font-bold text-xs shrink-0 ${
                            pct >= 75
                              ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                              : pct >= 40
                              ? 'bg-blue-500/15 text-blue-400 border border-blue-500/30'
                              : 'bg-amber-500/15 text-amber-400 border border-amber-500/30'
                          }`}
                        >
                          {pct}%
                        </div>
                        <div className="min-w-0">
                          <h4 className="text-sm font-medium text-slate-200 truncate flex items-center gap-2">
                            {item.conceptName}
                            {pct < 40 && (
                              <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
                                Priority Gap
                              </span>
                            )}
                          </h4>
                          <p className="text-xs text-slate-400 truncate">
                            {subName} • {item.totalAttempts} drills completed
                          </p>
                        </div>
                      </div>

                      <div className="flex items-center gap-2 shrink-0">
                        <span className="text-xs font-semibold text-cyan-400 flex items-center gap-1 group-hover:translate-x-1 transition-transform">
                          Practice <ArrowRight className="w-3.5 h-3.5" />
                        </span>
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            {/* Footer with Keyboard Hints (Linear style) */}
            <div className="px-4 py-2.5 bg-slate-950/60 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-500">
              <div className="flex items-center gap-4">
                <span>
                  <kbd className="px-1.5 py-0.5 bg-slate-800 border border-slate-700 rounded text-slate-400 mr-1">
                    ↑↓
                  </kbd>{' '}
                  Navigate
                </span>
                <span>
                  <kbd className="px-1.5 py-0.5 bg-slate-800 border border-slate-700 rounded text-slate-400 mr-1">
                    ↵
                  </kbd>{' '}
                  Select Drill
                </span>
                <span>
                  <kbd className="px-1.5 py-0.5 bg-slate-800 border border-slate-700 rounded text-slate-400 mr-1">
                    ESC
                  </kbd>{' '}
                  Close
                </span>
              </div>
              {onNavigateToRevision && (
                <button
                  onClick={() => {
                    onNavigateToRevision();
                    closeModal();
                  }}
                  className="text-cyan-400 hover:text-cyan-300 font-medium flex items-center gap-1"
                >
                  <Clock className="w-3 h-3" /> Jump to Revision Deck
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
};
