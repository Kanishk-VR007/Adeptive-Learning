import React from 'react';
import { DifficultyLevel, MasteryTier } from '../../types';

interface BadgeProps {
  label: string;
  variant?: 'difficulty' | 'mastery' | 'neutral' | 'accent';
  level?: DifficultyLevel;
  tier?: MasteryTier;
  size?: 'sm' | 'md';
}

export const Badge: React.FC<BadgeProps> = ({
  label,
  variant = 'neutral',
  level,
  tier,
  size = 'md',
}) => {
  let styleClasses = 'bg-slate-800 text-slate-300 border-slate-700';

  if (variant === 'difficulty' && level) {
    if (level === 'beginner') {
      styleClasses = 'bg-emerald-950/60 text-emerald-300 border-emerald-700/50';
    } else if (level === 'intermediate') {
      styleClasses = 'bg-cyan-950/60 text-cyan-300 border-cyan-700/50';
    } else if (level === 'advanced') {
      styleClasses = 'bg-purple-950/60 text-purple-300 border-purple-700/50';
    }
  } else if (variant === 'mastery' && tier) {
    if (tier === 'Mastered') {
      styleClasses = 'bg-emerald-900/40 text-emerald-300 border-emerald-500/40';
    } else if (tier === 'Good Understanding') {
      styleClasses = 'bg-blue-900/40 text-blue-300 border-blue-500/40';
    } else if (tier === 'Developing Understanding') {
      styleClasses = 'bg-amber-900/40 text-amber-300 border-amber-500/40';
    } else {
      styleClasses = 'bg-rose-900/40 text-rose-300 border-rose-500/40';
    }
  } else if (variant === 'accent') {
    styleClasses = 'bg-cyan-500/15 text-cyan-300 border-cyan-500/30';
  }

  const sizeClasses = size === 'sm' ? 'px-2 py-0.5 text-[11px]' : 'px-2.5 py-1 text-xs';

  return (
    <span
      className={`inline-flex items-center font-medium rounded-full border ${styleClasses} ${sizeClasses}`}
      data-testid="status-badge"
    >
      {label}
    </span>
  );
};
