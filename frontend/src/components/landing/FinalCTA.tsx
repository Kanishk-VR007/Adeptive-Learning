import React from 'react';
import {
  ArrowRight,
  Sparkles,
  ShieldCheck,
  CheckCircle2,
  Zap,
} from 'lucide-react';
import { Button } from '../ui/Button';
import { ScrollReveal } from './ScrollReveal';

interface FinalCTAProps {
  onStartJourney: () => void;
}

export const FinalCTA: React.FC<FinalCTAProps> = ({ onStartJourney }) => {
  return (
    <section className="relative py-28 overflow-hidden">
      {/* Background Lighting Ambience */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[350px] bg-gradient-to-r from-blue-600/20 via-cyan-500/20 to-purple-600/20 rounded-full blur-[140px] pointer-events-none" />

      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10 text-center">
        <ScrollReveal delayMs={50}>
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-cyan-500/10 border border-cyan-500/30 text-cyan-300 text-xs font-semibold mb-6 shadow-glow-sm">
            <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
            <span>Ready for Exam Day?</span>
          </div>
        </ScrollReveal>

        <ScrollReveal delayMs={150}>
          <h2 className="text-4xl sm:text-5xl lg:text-6xl font-black text-white tracking-tight leading-[1.15] mb-6">
            Stop studying everything.{' '}
            <span className="block mt-1 bg-gradient-to-r from-blue-400 via-cyan-400 to-indigo-300 bg-clip-text text-transparent">
              Start mastering what matters.
            </span>
          </h2>
        </ScrollReveal>

        <ScrollReveal delayMs={250}>
          <p className="text-base sm:text-xl text-slate-300 max-w-2xl mx-auto mb-10 font-normal leading-relaxed">
            Build your personalized learning journey with AdeptLearn. Experience intelligent exam
            preparation that adapts to your mind, targets your weak concepts, and guarantees deep cognitive retention.
          </p>
        </ScrollReveal>

        {/* Action Button Group */}
        <ScrollReveal delayMs={350}>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Button
              variant="tactile"
              size="lg"
              onClick={onStartJourney}
              className="px-10 py-4 font-extrabold text-base shadow-glow-cyan/50"
              data-testid="final-cta-start-button"
            >
              Start Your Learning Journey
              <ArrowRight className="w-5 h-5 ml-2.5" />
            </Button>
          </div>
        </ScrollReveal>

        {/* Trust Guarantees */}
        <ScrollReveal delayMs={450}>
          <div className="mt-10 flex flex-wrap items-center justify-center gap-6 text-xs text-slate-400 font-medium">
            <div className="flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-cyan-400" />
              <span>Full Curriculum Included</span>
            </div>
            <div className="flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <span>No Credit Card Required</span>
            </div>
            <div className="flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-purple-400" />
              <span>BKT & FSRS Dual-Memory Engine</span>
            </div>
          </div>
        </ScrollReveal>
      </div>
    </section>
  );
};
