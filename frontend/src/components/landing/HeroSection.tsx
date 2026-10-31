import React from 'react';
import {
  ArrowRight,
  Play,
  Sparkles,
  ShieldCheck,
  Brain,
  Zap,
} from 'lucide-react';
import { Button } from '../ui/Button';
import { LandingGalaxy } from './LandingGalaxy';
import { ScrollReveal } from './ScrollReveal';

interface HeroSectionProps {
  onStartLearning: () => void;
  onExploreHowItWorks: () => void;
}

export const HeroSection: React.FC<HeroSectionProps> = ({
  onStartLearning,
  onExploreHowItWorks,
}) => {
  return (
    <section className="relative min-h-[92vh] flex items-center justify-center pt-24 pb-16 overflow-hidden">
      {/* Background Ambience & Lighting */}
      <div className="absolute top-1/4 -left-32 w-96 h-96 bg-blue-600/15 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute top-1/3 -right-32 w-96 h-96 bg-cyan-500/15 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute -top-16 left-1/2 -translate-x-1/2 w-[700px] h-[350px] bg-gradient-to-b from-indigo-900/20 to-transparent rounded-full blur-[140px] pointer-events-none" />

      {/* Grid Background Pattern */}
      <div
        className="absolute inset-0 opacity-[0.03] pointer-events-none"
        style={{
          backgroundImage:
            'radial-gradient(circle at 1px 1px, rgba(255,255,255,0.7) 1px, transparent 0)',
          backgroundSize: '36px 36px',
        }}
      />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 w-full relative z-10">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-8 items-center">
          {/* Left Column: Headline, Copy, Action Buttons */}
          <div className="lg:col-span-6 space-y-6 text-center lg:text-left">
            <ScrollReveal delayMs={50}>
              <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-cyan-500/10 border border-cyan-500/30 text-cyan-300 text-xs font-semibold shadow-glow-sm">
                <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
                <span>Next-Gen Adaptive Learning Architecture</span>
              </div>
            </ScrollReveal>

            <ScrollReveal delayMs={150}>
              <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-white leading-[1.12]">
                Your learning journey.{' '}
                <span className="block mt-1 bg-gradient-to-r from-blue-400 via-cyan-400 to-indigo-300 bg-clip-text text-transparent">
                  Powered by intelligence that adapts to you.
                </span>
              </h1>
            </ScrollReveal>

            <ScrollReveal delayMs={250}>
              <p className="text-base sm:text-lg text-slate-300 max-w-xl mx-auto lg:mx-0 font-normal leading-relaxed">
                Move beyond traditional AI tutoring. Discover a learning experience that tracks your
                understanding, identifies misconceptions and helps you master every concept.
              </p>
            </ScrollReveal>

            {/* CTA Buttons */}
            <ScrollReveal delayMs={350}>
              <div className="flex flex-col sm:flex-row items-center justify-center lg:justify-start gap-4 pt-2">
                <Button
                  variant="tactile"
                  size="lg"
                  onClick={onStartLearning}
                  className="w-full sm:w-auto px-8 py-3.5 font-bold text-sm shadow-glow-cyan/40"
                  data-testid="hero-start-button"
                >
                  Start Learning
                  <ArrowRight className="w-4 h-4 ml-2" />
                </Button>

                <Button
                  variant="glass"
                  size="lg"
                  onClick={onExploreHowItWorks}
                  className="w-full sm:w-auto px-6 py-3.5 font-semibold text-sm border-slate-700/80 text-slate-200 hover:text-cyan-300 hover:border-cyan-500/40"
                  data-testid="hero-explore-button"
                >
                  <Play className="w-4 h-4 mr-2 fill-slate-300" />
                  Explore How It Works
                </Button>
              </div>
            </ScrollReveal>

            {/* Proof Metric Highlights */}
            <ScrollReveal delayMs={450}>
              <div className="pt-6 border-t border-slate-800/80 grid grid-cols-3 gap-4 max-w-md mx-auto lg:mx-0">
                <div>
                  <div className="text-2xl font-bold text-white tracking-tight">BKT + FSRS</div>
                  <div className="text-[11px] text-slate-400 mt-0.5">Dual-Memory Engine</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-cyan-400 tracking-tight">60 FPS</div>
                  <div className="text-[11px] text-slate-400 mt-0.5">3D Knowledge Galaxy</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-emerald-400 tracking-tight">100%</div>
                  <div className="text-[11px] text-slate-400 mt-0.5">Deterministic Tracing</div>
                </div>
              </div>
            </ScrollReveal>
          </div>

          {/* Right Column: 3D Knowledge Galaxy Visualization */}
          <div className="lg:col-span-6 flex justify-center">
            <ScrollReveal delayMs={200} direction="none" className="w-full">
              <LandingGalaxy />
            </ScrollReveal>
          </div>
        </div>
      </div>
    </section>
  );
};
