import React, { HTMLAttributes, forwardRef } from 'react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'elevated' | 'glass' | 'interactive' | 'glow';
  hasGlowBorder?: boolean;
}

export const Card = forwardRef<HTMLDivElement, CardProps>(
  ({ className, variant = 'default', hasGlowBorder = false, children, ...props }, ref) => {
    const baseStyles = 'rounded-2xl transition-all duration-200 relative overflow-hidden';

    const variantStyles = {
      default:
        'bg-slate-900/80 border border-slate-800/80 shadow-md',
      elevated:
        'bg-slate-900/95 border border-slate-700/70 shadow-xl shadow-slate-950/50',
      glass:
        'bg-slate-900/60 backdrop-blur-xl border border-white/[0.08] shadow-lg',
      interactive:
        'bg-slate-900/70 backdrop-blur-md border border-slate-800/80 hover:border-cyan-500/40 hover:-translate-y-1 hover:shadow-xl hover:shadow-cyan-500/10 cursor-pointer',
      glow:
        'bg-slate-900/90 border border-cyan-500/30 shadow-[0_0_25px_rgba(6,182,212,0.15)]',
    }[variant];

    return (
      <div
        ref={ref}
        className={twMerge(
          clsx(
            baseStyles,
            variantStyles,
            hasGlowBorder && 'gradient-border-glow',
            className
          )
        )}
        {...props}
      >
        {children}
      </div>
    );
  }
);

Card.displayName = 'Card';

export const CardHeader: React.FC<HTMLAttributes<HTMLDivElement>> = ({
  className,
  children,
  ...props
}) => (
  <div
    className={twMerge('px-5 py-4 border-b border-slate-800/80 flex items-center justify-between', className)}
    {...props}
  >
    {children}
  </div>
);

export const CardContent: React.FC<HTMLAttributes<HTMLDivElement>> = ({
  className,
  children,
  ...props
}) => (
  <div className={twMerge('p-5', className)} {...props}>
    {children}
  </div>
);

export const CardFooter: React.FC<HTMLAttributes<HTMLDivElement>> = ({
  className,
  children,
  ...props
}) => (
  <div
    className={twMerge(
      'px-5 py-3.5 bg-slate-950/40 border-t border-slate-800/60 flex items-center justify-between',
      className
    )}
    {...props}
  >
    {children}
  </div>
);
