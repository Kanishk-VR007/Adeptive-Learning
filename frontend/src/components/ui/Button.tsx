import React, { ButtonHTMLAttributes, forwardRef } from 'react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'tactile' | 'glow' | 'danger' | 'ghost' | 'glass';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant = 'primary',
      size = 'md',
      isLoading = false,
      disabled,
      children,
      ...props
    },
    ref
  ) => {
    // Base styles: high performance transitions, focus rings, accessibility
    const baseStyles =
      'inline-flex items-center justify-center font-medium rounded-xl transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-950 disabled:opacity-50 disabled:pointer-events-none select-none active:scale-[0.98]';

    const sizeStyles = {
      sm: 'text-xs px-3 py-1.5 gap-1.5',
      md: 'text-sm px-4 py-2 gap-2',
      lg: 'text-base px-6 py-3 gap-2.5',
    }[size];

    const variantStyles = {
      // Tactile 3D Button (Duolingo style: 4px border-bottom offset that depresses)
      tactile:
        'bg-blue-600 hover:bg-blue-500 text-white border border-blue-400/30 shadow-[0_4px_0_#1e40af,0_8px_16px_rgba(37,99,235,0.25)] hover:shadow-[0_5px_0_#1e40af,0_12px_20px_rgba(37,99,235,0.35)] active:shadow-[0_1px_0_#1e40af] active:translate-y-[3px]',
      
      // Electric Blue Primary with glow
      primary:
        'bg-blue-600 hover:bg-blue-500 text-white shadow-lg shadow-blue-600/25 border border-blue-500/50 hover:border-blue-400',
      
      // Neon Cyan Glow (Linear / Spline style)
      glow:
        'bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-semibold shadow-[0_0_20px_rgba(6,182,212,0.4)] border border-cyan-300',
      
      // Secondary Dark Surface
      secondary:
        'bg-slate-800/90 hover:bg-slate-700 text-slate-200 border border-slate-700/80 hover:border-slate-600 shadow-sm',
      
      // Hairline Glassmorphism
      glass:
        'bg-slate-900/60 hover:bg-slate-800/70 text-slate-200 border border-white/10 hover:border-cyan-400/40 backdrop-blur-md shadow-sm',
      
      // Danger Action
      danger:
        'bg-rose-600/90 hover:bg-rose-500 text-white border border-rose-500/50 shadow-lg shadow-rose-950/40',
      
      // Ghost Minimal
      ghost:
        'text-slate-400 hover:text-slate-100 hover:bg-slate-800/60',
    }[variant];

    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        className={twMerge(clsx(baseStyles, sizeStyles, variantStyles, className))}
        {...props}
      >
        {isLoading && (
          <svg
            className="animate-spin -ml-1 mr-2 h-4 w-4 text-current"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
        )}
        {children}
      </button>
    );
  }
);

Button.displayName = 'Button';
