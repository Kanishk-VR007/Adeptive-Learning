import React, { useState } from 'react';
import {
  MessageSquare,
  Sparkles,
  AlertTriangle,
  Lightbulb,
  HelpCircle,
  CheckCircle2,
  Brain,
  Info,
  ChevronRight,
} from 'lucide-react';
import { ScrollReveal } from './ScrollReveal';

export const TutorDemo: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'reasoning' | 'misconception' | 'hint' | 'question'>(
    'reasoning'
  );

  return (
    <section id="demo" className="relative py-28 overflow-hidden">
      {/* Background Lighting */}
      <div className="absolute top-1/2 left-1/4 -translate-y-1/2 w-96 h-96 bg-cyan-600/10 rounded-full blur-[140px] pointer-events-none" />
      <div className="absolute top-1/2 right-1/4 -translate-y-1/2 w-96 h-96 bg-purple-600/10 rounded-full blur-[140px] pointer-events-none" />

      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        {/* Section Header */}
        <div className="text-center space-y-4 mb-16">
          <ScrollReveal delayMs={50}>
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-cyan-500/10 border border-cyan-500/30 text-cyan-300 text-xs font-semibold">
              <Brain className="w-3.5 h-3.5 text-cyan-400" />
              <span>Interactive Socratic Dialogue</span>
            </div>
          </ScrollReveal>

          <ScrollReveal delayMs={150}>
            <h2 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-white tracking-tight">
              Meet your AI tutor in action.
            </h2>
          </ScrollReveal>

          <ScrollReveal delayMs={250}>
            <p className="text-slate-400 text-base sm:text-lg max-w-2xl mx-auto">
              Observe how AdeptLearn intercepts student intuition, diagnoses cognitive misconceptions,
              and scaffolds the reasoning path without giving away the answer.
            </p>
          </ScrollReveal>
        </div>

        {/* Demo Interactive Container */}
        <ScrollReveal delayMs={200}>
          <div className="rounded-3xl bg-slate-900/90 border border-slate-800 backdrop-blur-xl shadow-2xl overflow-hidden">
            {/* Top Bar with Window Controls & Disclaimer */}
            <div className="px-6 py-4 bg-slate-950/80 border-b border-slate-800 flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-rose-500/80" />
                <span className="w-3 h-3 rounded-full bg-amber-500/80" />
                <span className="w-3 h-3 rounded-full bg-emerald-500/80" />
                <span className="ml-2 text-xs font-mono text-slate-400">
                  Concept: Ohm's Law & Circuit Resistance (PHYS101)
                </span>
              </div>

              <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-blue-500/10 border border-blue-500/30 text-blue-300 text-[11px] font-medium">
                <Info className="w-3 h-3 text-cyan-400" />
                <span>Pedagogical Demonstration Simulator</span>
              </div>
            </div>

            <div className="p-6 sm:p-8 space-y-6">
              {/* Turn 1: Student Response Bubble */}
              <div className="flex items-start gap-4 max-w-2xl">
                <div className="w-9 h-9 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center shrink-0 font-bold text-xs text-slate-300">
                  You
                </div>
                <div className="p-4 rounded-2xl rounded-tl-sm bg-slate-800/80 border border-slate-700/80 text-sm text-slate-200 shadow-md">
                  <p className="font-medium">
                    "I think current increases when resistance increases."
                  </p>
                  <span className="text-[10px] text-slate-400 mt-1 block">
                    Student Submission • AP Physics 1
                  </span>
                </div>
              </div>

              {/* Turn 2: AdeptLearn Tutor Initial Response Bubble */}
              <div className="flex items-start gap-4 max-w-2xl ml-auto flex-row-reverse">
                <div className="w-9 h-9 rounded-full bg-gradient-to-br from-blue-600 to-cyan-500 flex items-center justify-center shrink-0 shadow-glow-cyan/40">
                  <Sparkles className="w-4 h-4 text-white" />
                </div>
                <div className="p-4 rounded-2xl rounded-tr-sm bg-blue-950/40 border border-cyan-500/40 text-sm text-slate-100 shadow-md">
                  <p className="font-medium text-cyan-300 mb-1">
                    "Let's revisit the relationship between voltage, resistance, and current."
                  </p>
                  <p className="text-slate-300 text-xs leading-relaxed">
                    Think of resistance like a constriction in a water pipe. If the water pressure (voltage)
                    stays constant and the pipe gets narrower, what happens to the volume of water flowing per second?
                  </p>
                </div>
              </div>

              {/* Cognitive Diagnostic Breakdown Tabs */}
              <div className="pt-6 border-t border-slate-800">
                <div className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3 flex items-center gap-1.5">
                  <Brain className="w-3.5 h-3.5 text-cyan-400" />
                  <span>Behind the Scenes: AI Cognitive Diagnostic Pipeline</span>
                </div>

                {/* Tab Switcher Pills */}
                <div className="flex flex-wrap gap-2 mb-4">
                  <button
                    onClick={() => setActiveTab('reasoning')}
                    className={`px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-all border ${
                      activeTab === 'reasoning'
                        ? 'bg-blue-600/20 border-cyan-500/50 text-cyan-300 shadow-glow-sm'
                        : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <Brain className="w-3.5 h-3.5" />
                    1. Reasoning Analysis
                  </button>

                  <button
                    onClick={() => setActiveTab('misconception')}
                    className={`px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-all border ${
                      activeTab === 'misconception'
                        ? 'bg-amber-500/20 border-amber-500/50 text-amber-300 shadow-glow-sm'
                        : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <AlertTriangle className="w-3.5 h-3.5" />
                    2. Misconception Detection
                  </button>

                  <button
                    onClick={() => setActiveTab('hint')}
                    className={`px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-all border ${
                      activeTab === 'hint'
                        ? 'bg-cyan-500/20 border-cyan-500/50 text-cyan-300 shadow-glow-sm'
                        : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <Lightbulb className="w-3.5 h-3.5" />
                    3. Socratic Scaffolding
                  </button>

                  <button
                    onClick={() => setActiveTab('question')}
                    className={`px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-all border ${
                      activeTab === 'question'
                        ? 'bg-emerald-500/20 border-emerald-500/50 text-emerald-300 shadow-glow-sm'
                        : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <HelpCircle className="w-3.5 h-3.5" />
                    4. Calibrated Follow-up
                  </button>
                </div>

                {/* Tab Content Display Card */}
                <div className="p-5 rounded-2xl bg-slate-950 border border-slate-800 text-xs sm:text-sm">
                  {activeTab === 'reasoning' && (
                    <div className="space-y-2 animate-in fade-in duration-150">
                      <div className="text-cyan-400 font-bold flex items-center gap-1.5">
                        <CheckCircle2 className="w-4 h-4 text-cyan-400" />
                        Mathematical Reasoning Diagnosis
                      </div>
                      <p className="text-slate-300 leading-relaxed font-normal">
                        Student correctly identified that resistance is connected to current, but inverted the
                        algebraic relationship. By Ohm's Law, I = V / R. Current is inversely proportional
                        to resistance, not directly proportional.
                      </p>
                      <div className="text-[11px] text-slate-400 font-mono pt-1">
                        Engine: DeepSeek-R1 • Evaluated in 1 pass • Confidence: 0.94
                      </div>
                    </div>
                  )}

                  {activeTab === 'misconception' && (
                    <div className="space-y-2 animate-in fade-in duration-150">
                      <div className="text-amber-400 font-bold flex items-center gap-1.5">
                        <AlertTriangle className="w-4 h-4 text-amber-400" />
                        Taxonomy: Direct vs Inverse Variation Confusion
                      </div>
                      <p className="text-slate-300 leading-relaxed font-normal">
                        Category: <span className="font-semibold text-white">Algebraic Inversion in Denominator Variables</span>.
                        The learner assumes greater physical quantity (resistance) produces greater movement (current).
                        Remediation requires physical flow analogy before symbolic formula retesting.
                      </p>
                      <div className="text-[11px] text-slate-400 font-mono pt-1">
                        BKT Update: P(L) slip penalty applied (-0.08) • Prior: 0.45 $\to$ Posterior: 0.37
                      </div>
                    </div>
                  )}

                  {activeTab === 'hint' && (
                    <div className="space-y-2 animate-in fade-in duration-150">
                      <div className="text-cyan-300 font-bold flex items-center gap-1.5">
                        <Lightbulb className="w-4 h-4 text-cyan-400" />
                        Empathetic Socratic Scaffolding
                      </div>
                      <p className="text-slate-300 leading-relaxed font-normal">
                        "Notice that resistance measures how much a material opposes current flow. More opposition
                        means charges struggle more to pass through. Does that increase or decrease the flow rate?"
                      </p>
                      <div className="text-[11px] text-slate-400 font-mono pt-1">
                        Generated via Llama 3.2 • Tone: Constructive & Non-punitive
                      </div>
                    </div>
                  )}

                  {activeTab === 'question' && (
                    <div className="space-y-2 animate-in fade-in duration-150">
                      <div className="text-emerald-400 font-bold flex items-center gap-1.5">
                        <HelpCircle className="w-4 h-4 text-emerald-400" />
                        Targeted Concept Probe
                      </div>
                      <p className="text-slate-300 leading-relaxed font-normal">
                        "If a battery maintains a constant 12 Volts across a circuit, and the resistor is doubled
                        from $4\Omega$ to $8\Omega$, does the current become 3 Amperes or 1.5 Amperes?"
                      </p>
                      <div className="text-[11px] text-slate-400 font-mono pt-1">
                        Bank Calibrated: Concept 104 • Difficulty: Level 2 (Reinforcement)
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </ScrollReveal>
      </div>
    </section>
  );
};
