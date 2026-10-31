import React from 'react';
import {
  Stethoscope,
  Network,
  Cpu,
  Trophy,
  ArrowRight,
  Sparkles,
} from 'lucide-react';
import { ScrollReveal } from './ScrollReveal';

export const HowItWorks: React.FC = () => {
  const steps = [
    {
      step: '01',
      title: 'Diagnose',
      subtitle: 'Understand Existing Knowledge',
      description:
        'AdeptLearn begins with targeted diagnostic questions that probe your foundational frontiers. Our mathematical model isolates genuine intuition from superficial guesswork.',
      icon: Stethoscope,
      accent: 'from-blue-500 to-cyan-500',
      badgeColor: 'text-blue-400 bg-blue-500/10 border-blue-500/30',
    },
    {
      step: '02',
      title: 'Map',
      subtitle: 'Build Interconnected Concept Graphs',
      description:
        'Every syllabus is rendered as a Directed Acyclic Graph (DAG) with validated prerequisite edges. You see exactly how foundational concepts unlock advanced exam topics.',
      icon: Network,
      accent: 'from-cyan-500 to-emerald-500',
      badgeColor: 'text-cyan-400 bg-cyan-500/10 border-cyan-500/30',
    },
    {
      step: '03',
      title: 'Adapt',
      subtitle: 'Generate Targeted Practice & Feedback',
      description:
        'As you answer, our DeepSeek-R1 diagnostic engine evaluates your conceptual reasoning, while Llama 3.2 delivers empathetic, scaffolded Socratic hints tailored to your mistakes.',
      icon: Cpu,
      accent: 'from-emerald-500 to-amber-500',
      badgeColor: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30',
    },
    {
      step: '04',
      title: 'Master',
      subtitle: 'Track Retention & Schedule Revision',
      description:
        'Bayesian Knowledge Tracing (BKT) updates your mastery probability P(L) in real-time. Free Spaced Repetition (FSRS) schedules flashcard reviews right before memory decay occurs.',
      icon: Trophy,
      accent: 'from-amber-500 to-purple-500',
      badgeColor: 'text-purple-400 bg-purple-500/10 border-purple-500/30',
    },
  ];

  return (
    <section id="how-it-works" className="relative py-28 bg-slate-950/80 border-t border-slate-800/80 overflow-hidden">
      {/* Background Lighting Glows */}
      <div className="absolute top-1/4 left-1/3 w-[600px] h-[300px] bg-blue-900/10 rounded-full blur-[140px] pointer-events-none" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        {/* Section Header */}
        <div className="text-center space-y-4 mb-20">
          <ScrollReveal delayMs={50}>
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-cyan-500/10 border border-cyan-500/30 text-cyan-300 text-xs font-semibold">
              <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
              <span>The 4-Step Adaptive Pipeline</span>
            </div>
          </ScrollReveal>

          <ScrollReveal delayMs={150}>
            <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-white tracking-tight">
              How AdeptLearn{' '}
              <span className="bg-gradient-to-r from-blue-400 via-cyan-400 to-indigo-300 bg-clip-text text-transparent">
                builds exam mastery.
              </span>
            </h2>
          </ScrollReveal>

          <ScrollReveal delayMs={250}>
            <p className="text-slate-400 text-base sm:text-lg max-w-2xl mx-auto">
              From your initial diagnostic probe to confident exam readiness, every turn is guided
              by rigorous pedagogical algorithms.
            </p>
          </ScrollReveal>
        </div>

        {/* 4-Column Step Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {steps.map((item, index) => {
            const Icon = item.icon;
            return (
              <ScrollReveal key={item.step} delayMs={index * 120} direction="up">
                <div className="h-full p-6 sm:p-7 rounded-3xl bg-slate-900/70 border border-slate-800 hover:border-cyan-500/40 backdrop-blur-md transition-all group flex flex-col justify-between hover:shadow-glow-cyan/20">
                  <div>
                    {/* Top Row: Step Number & Icon */}
                    <div className="flex items-center justify-between mb-6">
                      <span className="text-3xl sm:text-4xl font-black text-slate-700 group-hover:text-cyan-400/80 transition-colors">
                        {item.step}
                      </span>
                      <div className="w-12 h-12 rounded-2xl bg-slate-950 border border-slate-800 flex items-center justify-center group-hover:scale-110 transition-transform">
                        <Icon className="w-6 h-6 text-cyan-400" />
                      </div>
                    </div>

                    <div className="mb-2">
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded-full border uppercase tracking-wider ${item.badgeColor}`}
                      >
                        {item.title}
                      </span>
                    </div>

                    <h3 className="text-lg font-bold text-white mb-3 group-hover:text-cyan-300 transition-colors">
                      {item.subtitle}
                    </h3>

                    <p className="text-xs sm:text-sm text-slate-400 leading-relaxed font-normal">
                      {item.description}
                    </p>
                  </div>

                  <div className="pt-6 mt-6 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-500 group-hover:text-cyan-400 transition-colors">
                    <span className="font-semibold">Step {item.step} in pipeline</span>
                    <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
                  </div>
                </div>
              </ScrollReveal>
            );
          })}
        </div>
      </div>
    </section>
  );
};
