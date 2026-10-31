import React from 'react';
import { ChevronRight, Home, BookOpen, Layers } from 'lucide-react';

interface ConceptBreadcrumbsProps {
  subjectName: string;
  chapterTitle: string;
  conceptName: string;
  onNavigateHome: () => void;
  onNavigateSubject?: () => void;
}

export const ConceptBreadcrumbs: React.FC<ConceptBreadcrumbsProps> = ({
  subjectName,
  chapterTitle,
  conceptName,
  onNavigateHome,
  onNavigateSubject,
}) => {
  return (
    <nav
      className="flex items-center gap-1.5 text-xs text-slate-400 mb-4 overflow-x-auto py-1 scrollbar-none"
      aria-label="Breadcrumb"
      data-testid="concept-breadcrumbs"
    >
      <button
        onClick={onNavigateHome}
        className="flex items-center gap-1 hover:text-slate-200 transition-colors shrink-0"
      >
        <Home className="w-3.5 h-3.5" />
        <span>Dashboard</span>
      </button>

      <ChevronRight className="w-3.5 h-3.5 text-slate-600 shrink-0" />

      <button
        onClick={onNavigateSubject}
        className="flex items-center gap-1 hover:text-slate-200 transition-colors shrink-0 truncate max-w-[140px] sm:max-w-none"
      >
        <BookOpen className="w-3.5 h-3.5 text-electric-400" />
        <span>{subjectName}</span>
      </button>

      <ChevronRight className="w-3.5 h-3.5 text-slate-600 shrink-0" />

      <span className="flex items-center gap-1 text-slate-300 shrink-0 truncate max-w-[140px] sm:max-w-none">
        <Layers className="w-3.5 h-3.5 text-cyan-400" />
        <span>{chapterTitle}</span>
      </span>

      <ChevronRight className="w-3.5 h-3.5 text-slate-600 shrink-0" />

      <span className="font-semibold text-cyan-300 shrink-0 truncate max-w-[160px] sm:max-w-none">
        {conceptName}
      </span>
    </nav>
  );
};
