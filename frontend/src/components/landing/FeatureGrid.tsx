import React from 'react';
import {
  Stethoscope,
  Brain,
  HelpCircle,
  AlertTriangle,
  Repeat,
  BarChart3,
  Sparkles,
  ArrowRight,
  ShieldCheck,
  CheckCircle2,
} from 'lucide-react';
import { ScrollReveal } from './ScrollReveal';

export const FeatureGrid: React.FC = () => {
  const features = [
    {
      title: 'Diagnostic Assessment',
      category: 'KNOWLEDGE DISCOVERY',
      description:
        'Fast, high-discrimination initial diagnostic tests that map your knowledge frontier across calculus, linear algebra, and data structures before practice starts.',
      icon: Stethoscope,
      metric: 'Fast 5-Question Probe',
      color: '#00F0FF',
    },
    {
      title: 'Learner Knowledge Model',
      category: 'BAYESIAN PROBABILITY',
      description:
        'Deterministic Bayesian Knowledge Tracing (BKT) engine tracks continuous mastery P(L), slip probabilities P(S), and guess rates P(G) with mathematical precision.',
      icon: Brain,
      metric: 'Real-Time P(L) Deltas',
      color: '#3B82F6',
    },
    {
      title: 'Intelligent Question Generation',
      category: 'CALIBRATED DIFFICULTY',
      description:
        'Context-aware question sequencing tailored to your zone of proximal development, falling back to vetted database question banks with mathematical validity.',
      icon: HelpCircle,
      metric: '4 Cognitive Tiers',
      color: '#10B981',
    },
    {
      title: 'Misconception Detection',
      category: 'ROOT-CAUSE DIAGNOSIS',
      description:
        'Deep diagnostic evaluation distinguishes calculation typos from structural conceptual flaws, categorizing errors into an actionable pedagogical taxonomy.',
      icon: AlertTriangle,
      metric: 'Zero Hallucinations',
      color: '#F59E0B',
    },
    {
      title: 'Spaced Repetition (FSRS)',
      category: 'MEMORY RETENTION',
      description:
        'Free Spaced Repetition Scheduler predicts the Ebbinghaus forgetting curve, scheduling 3D flashcard reviews at optimal memory consolidation intervals.',
      icon: Repeat,
      metric: '5-Stage Leitner Deck',
      color: '#8B5CF6',
    },
    {
      title: 'Teacher & Cohort Analytics',
      category: 'INSTITUTIONAL INSIGHT',
      description:
        'Comprehensive syllabus heatmaps, student cohort distributions, and Directed Acyclic Graph (DAG) cycle validation for academic institutions and educators.',
      icon: BarChart3,
      metric: 'DAG Cycle Prevention',
      color: '#EC4899',
    },
  ];

  return (
    <section id="features" className="relative py-28 bg-slate-950/60 border-t border-slate-800/80 overflow-hidden">
      {/* Background Lighting */}
      <div className="absolute top-1/3 -left-40 w-96 h-96 bg-blue-900/10 rounded-full blur-[140px] pointer-events-none" />
      <div className="absolute bottom-1/3 -right-40 w-96 h-96 bg-cyan-900/10 rounded-full blur-[140px] pointer-events-none" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        {/* Section Header */}
        <div className="text-center space-y-4 mb-20">
          <ScrollReveal delayMs={50}>
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-cyan-500/10 border border-cyan-500/30 text-cyan-300 text-xs font-semibold">
              <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
              <span>Full-Stack Capabilities</span>
            </div>
          </ScrollReveal>

          <ScrollReveal delayMs={150}>
            <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-white tracking-tight">
              Six pillars of{' '}
              <span className="bg-gradient-to-r from-blue-400 via-cyan-400 to-indigo-300 bg-clip-text text-transparent">
                intelligent exam preparation.
              </span>
            </h2>
          </ScrollReveal>

          <ScrollReveal delayMs={250}>
            <p className="text-slate-400 text-base sm:text-lg max-w-2xl mx-auto">
              Every feature works together as a cohesive learning system designed to eliminate study
              inefficiency and build true conceptual mastery.
            </p>
          </ScrollReveal>
        </div>

        {/* 6-Card Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 sm:gap-8">
          {features.map((feat, index) => {
            const Icon = feat.icon;
            return (
              <ScrollReveal key={feat.title} delayMs={index * 80} direction="up">
                <div className="h-full p-7 rounded-3xl bg-slate-900/70 border border-slate-800 hover:border-cyan-500/40 backdrop-blur-md transition-all group flex flex-col justify-between hover:shadow-glow-cyan/20">
                  <div>
                    {/* Top Row: Icon and Category Tag */}
                    <div className="flex items-center justify-between mb-5">
                      <div
                        className="w-12 h-12 rounded-2xl flex items-center justify-center transition-transform group-hover:scale-110"
                        style={{
                          backgroundColor: `${feat.color}15`,
                          border: `1px solid ${feat.color}35`,
                        }}
                      >
                        <Icon className="w-6 h-6" style={{ color: feat.color }} />
                      </div>

                      <span className="text-[10px] font-bold tracking-widest uppercase px-2.5 py-1 rounded-full bg-slate-950 border border-slate-800 text-slate-400">
                        {feat.category}
                      </span>
                    </div>

                    <h3 className="text-lg font-bold text-white mb-2.5 group-hover:text-cyan-300 transition-colors">
                      {feat.title}
                    </h3>

                    <p className="text-xs sm:text-sm text-slate-400 leading-relaxed font-normal">
                      {feat.description}
                    </p>
                  </div>

                  <div className="pt-5 mt-5 border-t border-slate-800/80 flex items-center justify-between">
                    <span className="text-xs font-semibold text-cyan-400">
                      {feat.metric}
                    </span>
                    <ArrowRight className="w-4 h-4 text-slate-500 group-hover:text-cyan-400 group-hover:translate-x-1 transition-all" />
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
