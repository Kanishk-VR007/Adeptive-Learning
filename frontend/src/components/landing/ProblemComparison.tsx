import React from 'react';
import {
  XCircle,
  CheckCircle2,
  AlertTriangle,
  Sparkles,
  ArrowRight,
  Brain,
  Layers,
  Repeat,
  Compass,
} from 'lucide-react';
import { ScrollReveal } from './ScrollReveal';

export const ProblemComparison: React.FC = () => {
  const comparisonItems = [
    {
      label: 'Core Capability',
      traditional: 'Superficial Q&A response generation',
      adeptlearn: 'Deep reasoning & conceptual cognitive diagnosis',
    },
    {
      label: 'Feedback Style',
      traditional: 'Generic, verbose text explanations',
      adeptlearn: 'Pinpointed Socratic hints with misconception identification',
    },
    {
      label: 'Learner Modeling',
      traditional: 'Stateless session memory with zero mastery tracking',
      adeptlearn: 'Persistent Bayesian Knowledge Tracing (BKT) calculating continuous P(L)',
    },
    {
      label: 'Practice Sequencing',
      traditional: 'Random or repetitive static question dumps',
      adeptlearn: 'Dynamically calibrated questions targeting zone of proximal development',
    },
    {
      label: 'Memory Retention',
      traditional: 'Forgotten immediately upon session close',
      adeptlearn: 'Free Spaced Repetition (FSRS) scheduling optimal review intervals',
    },
  ];

  return (
    <section id="comparison" className="relative py-24 overflow-hidden">
      {/* Background Lighting Accents */}
      <div className="absolute top-1/3 -left-32 w-80 h-80 bg-rose-900/10 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute top-1/2 -right-32 w-80 h-80 bg-cyan-900/15 rounded-full blur-[120px] pointer-events-none" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        {/* Section Heading */}
        <div className="text-center space-y-4 mb-16">
          <ScrollReveal delayMs={50}>
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-cyan-500/10 border border-cyan-500/30 text-cyan-300 text-xs font-semibold">
              <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
              <span>Architectural Comparison</span>
            </div>
          </ScrollReveal>

          <ScrollReveal delayMs={150}>
            <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-white tracking-tight">
              The problem with{' '}
              <span className="text-slate-400">generic AI chatbots.</span>
            </h2>
          </ScrollReveal>

          <ScrollReveal delayMs={250}>
            <p className="text-slate-400 text-base sm:text-lg max-w-2xl mx-auto">
              Conventional LLM tutors just give away answers. AdeptLearn models your brain's actual
              knowledge frontier so you retain mastery on exam day.
            </p>
          </ScrollReveal>
        </div>

        {/* Side-by-Side Comparison Cards */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-stretch">
          {/* Traditional AI Tutor Card */}
          <ScrollReveal delayMs={100} direction="right">
            <div className="h-full p-8 rounded-3xl bg-slate-950/70 border border-rose-900/30 backdrop-blur-md relative overflow-hidden flex flex-col justify-between shadow-xl">
              <div className="absolute top-0 right-0 w-32 h-32 bg-rose-500/5 rounded-bl-full pointer-events-none" />

              <div>
                <div className="flex items-center gap-3 mb-6">
                  <div className="w-10 h-10 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-center justify-center">
                    <XCircle className="w-5 h-5 text-rose-400" />
                  </div>
                  <div>
                    <h3 className="text-xl font-bold text-white">Traditional AI Chatbots</h3>
                    <p className="text-xs text-rose-300/80">Surface-Level Prompt Interfaces</p>
                  </div>
                </div>

                <div className="space-y-4">
                  {comparisonItems.map((item, idx) => (
                    <div
                      key={idx}
                      className="p-3.5 rounded-2xl bg-slate-900/50 border border-slate-800/80 flex items-start gap-3"
                    >
                      <XCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                      <div>
                        <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                          {item.label}
                        </div>
                        <div className="text-xs text-slate-300 mt-0.5">{item.traditional}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="mt-6 pt-4 border-t border-slate-800/80 text-xs text-rose-300/70 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0" />
                <span>Result: Illusion of competence without long-term retention.</span>
              </div>
            </div>
          </ScrollReveal>

          {/* AdeptLearn Adaptive Tutor Card (Elevated & Glowing) */}
          <ScrollReveal delayMs={200} direction="left">
            <div className="h-full p-8 rounded-3xl bg-slate-900/90 border border-cyan-500/40 backdrop-blur-md relative overflow-hidden flex flex-col justify-between shadow-glow-cyan/20">
              <div className="absolute top-0 right-0 w-44 h-44 bg-gradient-to-bl from-cyan-500/15 via-blue-500/10 to-transparent rounded-bl-full pointer-events-none" />

              <div>
                <div className="flex items-center justify-between mb-6">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center">
                      <CheckCircle2 className="w-5 h-5 text-cyan-400" />
                    </div>
                    <div>
                      <h3 className="text-xl font-bold text-white flex items-center gap-2">
                        AdeptLearn
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-cyan-500/20 text-cyan-300 border border-cyan-500/40">
                          RECOMMENDED
                        </span>
                      </h3>
                      <p className="text-xs text-cyan-300/80">Cognitive Science & Algorithmic Tracing</p>
                    </div>
                  </div>
                </div>

                <div className="space-y-4">
                  {comparisonItems.map((item, idx) => (
                    <div
                      key={idx}
                      className="p-3.5 rounded-2xl bg-slate-950/70 border border-cyan-500/20 hover:border-cyan-500/40 transition-colors flex items-start gap-3 shadow-sm"
                    >
                      <CheckCircle2 className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
                      <div>
                        <div className="text-[11px] font-bold uppercase tracking-wider text-cyan-400">
                          {item.label}
                        </div>
                        <div className="text-xs font-medium text-white mt-0.5">
                          {item.adeptlearn}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="mt-6 pt-4 border-t border-slate-800 text-xs text-cyan-300 flex items-center gap-2 font-medium">
                <Sparkles className="w-4 h-4 shrink-0 text-cyan-400" />
                <span>Result: Deterministic concept mastery with measurable probability updates.</span>
              </div>
            </div>
          </ScrollReveal>
        </div>
      </div>
    </section>
  );
};
