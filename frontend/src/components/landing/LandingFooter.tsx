import React from 'react';
import { Compass, Sparkles, Mail, Heart, Globe, GraduationCap } from 'lucide-react';

interface LandingFooterProps {
  onSignIn: () => void;
  onRegister: () => void;
  onEnterApp: () => void;
}

export const LandingFooter: React.FC<LandingFooterProps> = ({
  onSignIn,
  onRegister,
  onEnterApp,
}) => {
  return (
    <footer className="bg-slate-950 border-t border-slate-800/80 pt-16 pb-12 text-slate-400 text-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-10 pb-12 border-b border-slate-800/80">
          {/* Column 1: Brand & Tagline */}
          <div className="lg:col-span-2 space-y-4">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-blue-600 to-cyan-500 p-0.5 shadow-glow-cyan/30">
                <div className="w-full h-full bg-slate-950 rounded-[10px] flex items-center justify-center">
                  <Compass className="w-4 h-4 text-cyan-400" />
                </div>
              </div>
              <span className="text-base font-bold text-white tracking-tight">
                Adept<span className="gradient-text-blue-cyan">Learn</span>
              </span>
            </div>

            <p className="text-slate-400 max-w-sm leading-relaxed text-xs">
              "Understand what you learn. Master what you know."
              <br />
              An adaptive AI-powered exam-preparation platform that identifies knowledge gaps,
              understands reasoning and builds a personalized path to exam mastery.
            </p>

            <div className="flex items-center gap-3 pt-2">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-[11px] text-slate-400 font-mono">
                System Online • Port 8000 & 5173 Active
              </span>
            </div>
          </div>

          {/* Column 2: Architecture & Capabilities */}
          <div className="space-y-3">
            <div className="text-xs font-bold uppercase tracking-wider text-slate-200">
              Features
            </div>
            <ul className="space-y-2">
              <li>
                <a href="#how-it-works" className="hover:text-cyan-300 transition-colors">
                  4-Step Adaptive Pipeline
                </a>
              </li>
              <li>
                <a href="#comparison" className="hover:text-cyan-300 transition-colors">
                  BKT vs Generic AI
                </a>
              </li>
              <li>
                <a href="#demo" className="hover:text-cyan-300 transition-colors">
                  Interactive AI Tutor Demo
                </a>
              </li>
              <li>
                <a href="#features" className="hover:text-cyan-300 transition-colors">
                  3D Knowledge Galaxy
                </a>
              </li>
              <li>
                <a href="#features" className="hover:text-cyan-300 transition-colors">
                  FSRS Spaced Repetition
                </a>
              </li>
            </ul>
          </div>

          {/* Column 3: Platform & Portal */}
          <div className="space-y-3">
            <div className="text-xs font-bold uppercase tracking-wider text-slate-200">
              Portal
            </div>
            <ul className="space-y-2">
              <li>
                <button
                  onClick={onEnterApp}
                  className="hover:text-cyan-300 transition-colors text-left"
                >
                  Student Dashboard
                </button>
              </li>
              <li>
                <button
                  onClick={onSignIn}
                  className="hover:text-cyan-300 transition-colors text-left"
                >
                  Sign In
                </button>
              </li>
              <li>
                <button
                  onClick={onRegister}
                  className="hover:text-cyan-300 transition-colors text-left font-semibold text-cyan-400"
                >
                  Register Free
                </button>
              </li>
              <li>
                <span className="text-slate-500 cursor-not-allowed">Teacher Analytics (Pro)</span>
              </li>
            </ul>
          </div>

          {/* Column 4: Contact & Resources */}
          <div className="space-y-3">
            <div className="text-xs font-bold uppercase tracking-wider text-slate-200">
              Contact & Syllabi
            </div>
            <ul className="space-y-2">
              <li className="flex items-center gap-1.5">
                <Mail className="w-3.5 h-3.5 text-cyan-400" />
                <span>contact@adeptlearn.edu</span>
              </li>
              <li>
                <span className="text-slate-400">AP Calculus BC & STEM Curricula</span>
              </li>
              <li>
                <span className="text-slate-400">FastAPI & LangGraph Engine</span>
              </li>
            </ul>
          </div>
        </div>

        {/* Bottom Row */}
        <div className="pt-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-[11px] text-slate-400">
          <div>
            © {new Date().getFullYear()} AdeptLearn. All rights reserved. Adaptive Exam-Prep Tutor Platform.
          </div>
          <div className="flex items-center gap-1">
            <span>Built with precision for deeper cognitive mastery</span>
          </div>
        </div>
      </div>
    </footer>
  );
};
