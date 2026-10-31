import React from 'react';
import { ScrollReveal } from './ScrollReveal';
import { Compass, Sparkles, Brain, Network, HeartHandshake } from 'lucide-react';

export const StorytellingSection: React.FC = () => {
  const storyBeats = [
    {
      number: '01',
      title: 'Every student learns differently.',
      description:
        'Linear curricula force uniform pacing. Real cognition is non-linear, with unique cognitive strengths, learning speeds, and foundational instincts.',
      icon: Brain,
      color: 'from-blue-500 to-cyan-400',
    },
    {
      number: '02',
      title: 'Every concept has a connection.',
      description:
        'Advanced ideas rest on foundational bedrock. Understanding derivatives requires intuitive limits; mastering integration requires composite function fluency.',
      icon: Network,
      color: 'from-cyan-400 to-emerald-400',
    },
    {
      number: '03',
      title: 'Every mistake reveals an opportunity.',
      description:
        'An incorrect answer is rarely a random guess. It is almost always a systematic misconception that pinpointed pedagogical intervention can transform into mastery.',
      icon: Sparkles,
      color: 'from-emerald-400 to-amber-400',
    },
    {
      number: '04',
      title: 'Your tutor should understand more than your answers.',
      description:
        'A truly adaptive tutor tracks the latent probability of your knowledge, analyzes your step-by-step reasoning, and scaffolds your cognitive path forward.',
      icon: HeartHandshake,
      color: 'from-amber-400 to-purple-400',
    },
  ];

  return (
    <section className="relative py-28 overflow-hidden bg-slate-950/60 border-y border-slate-800/80">
      {/* Background Lighting */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[500px] bg-blue-950/20 rounded-full blur-[140px] pointer-events-none" />

      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        {/* Section Header */}
        <div className="text-center space-y-4 mb-20">
          <ScrollReveal delayMs={50}>
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-blue-500/10 border border-blue-500/30 text-blue-300 text-xs font-semibold">
              <Compass className="w-3.5 h-3.5 text-blue-400" />
              <span>Pedagogical Core Principle</span>
            </div>
          </ScrollReveal>

          <ScrollReveal delayMs={150}>
            <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-white tracking-tight">
              A philosophy built around{' '}
              <span className="bg-gradient-to-r from-cyan-400 via-blue-400 to-indigo-400 bg-clip-text text-transparent">
                how minds actually master knowledge.
              </span>
            </h2>
          </ScrollReveal>
        </div>

        {/* Vertical Story Track with Illuminated Line */}
        <div className="relative">
          {/* Central Vertical Timeline Guideline */}
          <div className="hidden md:block absolute left-1/2 top-4 bottom-4 w-px bg-gradient-to-b from-blue-500/40 via-cyan-500/40 to-purple-500/40 -translate-x-1/2" />

          <div className="space-y-14 sm:space-y-20">
            {storyBeats.map((beat, index) => {
              const isEven = index % 2 === 0;
              const Icon = beat.icon;

              return (
                <div
                  key={beat.number}
                  className={`flex flex-col md:flex-row items-center gap-8 md:gap-16 ${
                    isEven ? '' : 'md:flex-row-reverse'
                  }`}
                >
                  {/* Left / Right Card Content */}
                  <div className="w-full md:w-1/2">
                    <ScrollReveal
                      delayMs={index * 120}
                      direction={isEven ? 'right' : 'left'}
                    >
                      <div className="p-6 sm:p-8 rounded-3xl bg-slate-900/80 border border-slate-800 hover:border-slate-700/80 backdrop-blur-md shadow-xl transition-all group">
                        <div className="flex items-center gap-3 mb-3">
                          <span className="text-xs font-extrabold tracking-widest text-cyan-400 uppercase">
                            Phase {beat.number}
                          </span>
                          <span className="h-px flex-1 bg-slate-800" />
                        </div>

                        <h3 className="text-xl sm:text-2xl font-bold text-white mb-3 group-hover:text-cyan-300 transition-colors">
                          {beat.title}
                        </h3>

                        <p className="text-sm sm:text-base text-slate-300 leading-relaxed font-normal">
                          {beat.description}
                        </p>
                      </div>
                    </ScrollReveal>
                  </div>

                  {/* Center Node Icon */}
                  <div className="relative shrink-0 z-10">
                    <ScrollReveal delayMs={index * 120 + 80} direction="none">
                      <div className="w-14 h-14 rounded-2xl bg-slate-900 border-2 border-cyan-500/40 flex items-center justify-center shadow-glow-cyan/40 group-hover:scale-110 transition-transform">
                        <Icon className="w-6 h-6 text-cyan-400" />
                      </div>
                    </ScrollReveal>
                  </div>

                  {/* Empty Spacer Column for balance on desktop */}
                  <div className="hidden md:block w-1/2" />
                </div>
              );
            })}
          </div>
        </div>

        {/* Climax Reveal: "Meet AdeptLearn." */}
        <div className="mt-24 text-center">
          <ScrollReveal delayMs={200}>
            <div className="inline-block p-1 rounded-3xl bg-gradient-to-r from-blue-600 via-cyan-500 to-indigo-600 shadow-glow-cyan/50">
              <div className="px-8 sm:px-14 py-8 rounded-[22px] bg-slate-950 text-center space-y-3">
                <p className="text-xs font-bold tracking-widest uppercase text-cyan-400">
                  The Next Evolution
                </p>
                <h3 className="text-3xl sm:text-5xl font-black text-white tracking-tight">
                  Meet AdeptLearn.
                </h3>
                <p className="text-sm sm:text-base text-slate-300 max-w-lg mx-auto">
                  Understand what you learn. Master what you know. Powered by empirical cognitive science.
                </p>
              </div>
            </div>
          </ScrollReveal>
        </div>
      </div>
    </section>
  );
};
