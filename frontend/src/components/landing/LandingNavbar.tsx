import React, { useState, useEffect } from 'react';
import {
  Compass,
  Menu,
  X,
  ArrowRight,
  LogIn,
  Sparkles,
  Layers,
  GraduationCap,
  ShieldCheck,
} from 'lucide-react';
import { Button } from '../ui/Button';

interface LandingNavbarProps {
  onSignIn: () => void;
  onGetStarted: () => void;
  onEnterApp: () => void;
}

export const LandingNavbar: React.FC<LandingNavbarProps> = ({
  onSignIn,
  onGetStarted,
  onEnterApp,
}) => {
  const [isScrolled, setIsScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 20);
    };
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const navLinks = [
    { label: 'How It Works', href: '#how-it-works' },
    { label: 'Why AdeptLearn', href: '#comparison' },
    { label: 'Features', href: '#features' },
    { label: 'Live Demo', href: '#demo' },
  ];

  const handleScrollTo = (e: React.MouseEvent<HTMLAnchorElement>, href: string) => {
    e.preventDefault();
    setMobileMenuOpen(false);
    const target = document.querySelector(href);
    if (target) {
      target.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <header
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        isScrolled
          ? 'bg-slate-950/85 backdrop-blur-md border-b border-slate-800/80 shadow-2xl py-3'
          : 'bg-transparent border-b border-transparent py-5'
      }`}
      data-testid="landing-navbar"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between">
        {/* Brand Logo */}
        <a
          href="#"
          className="flex items-center gap-2.5 group cursor-pointer focus:outline-none"
          onClick={(e) => {
            e.preventDefault();
            window.scrollTo({ top: 0, behavior: 'smooth' });
          }}
        >
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-600 via-indigo-600 to-cyan-500 p-0.5 shadow-glow-cyan/40 transition-transform group-hover:scale-105">
            <div className="w-full h-full bg-slate-950 rounded-[10px] flex items-center justify-center">
              <Compass className="w-5 h-5 text-cyan-400 group-hover:rotate-45 transition-transform duration-300" />
            </div>
          </div>
          <div>
            <div className="text-lg font-bold tracking-tight text-white flex items-center gap-1.5">
              Adept<span className="gradient-text-blue-cyan">Learn</span>
              <span className="text-[10px] px-1.5 py-0.2 font-semibold bg-cyan-500/10 border border-cyan-500/30 text-cyan-300 rounded-full">
                AI
              </span>
            </div>
          </div>
        </a>

        {/* Desktop Navigation Links */}
        <nav className="hidden md:flex items-center gap-1 bg-slate-900/60 border border-slate-800/80 rounded-full px-4 py-1.5 backdrop-blur-sm">
          {navLinks.map((link) => (
            <a
              key={link.label}
              href={link.href}
              onClick={(e) => handleScrollTo(e, link.href)}
              className="text-xs font-medium text-slate-300 hover:text-cyan-300 px-3 py-1.5 rounded-full transition-colors hover:bg-slate-800/50"
            >
              {link.label}
            </a>
          ))}
        </nav>

        {/* Desktop Action CTAs */}
        <div className="hidden md:flex items-center gap-3">
          <button
            onClick={onSignIn}
            className="text-xs font-medium text-slate-300 hover:text-white px-3 py-1.5 rounded-xl transition-colors flex items-center gap-1.5 hover:bg-slate-900"
            data-testid="navbar-signin-button"
          >
            <LogIn className="w-3.5 h-3.5 text-cyan-400" />
            Sign In
          </button>

          <Button
            variant="tactile"
            size="sm"
            onClick={onGetStarted}
            className="flex items-center gap-1.5 font-semibold text-xs shadow-glow-sm"
            data-testid="navbar-getstarted-button"
          >
            Get Started
            <ArrowRight className="w-3.5 h-3.5" />
          </Button>

          <button
            onClick={onEnterApp}
            className="text-[11px] font-semibold text-cyan-400 border border-cyan-500/30 hover:border-cyan-400 px-3 py-1.5 rounded-full hover:bg-cyan-500/10 transition-all flex items-center gap-1.5 shadow-glow-sm"
            title="Jump directly to Student Dashboard"
            data-testid="navbar-portal-button"
          >
            <GraduationCap className="w-3.5 h-3.5" />
            Launch App
          </button>
        </div>

        {/* Mobile Hamburger Button */}
        <div className="md:hidden flex items-center gap-2">
          <button
            onClick={onEnterApp}
            className="text-[11px] font-semibold text-cyan-400 border border-cyan-500/30 px-2.5 py-1 rounded-full bg-cyan-500/10"
          >
            App
          </button>
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800"
            aria-label="Toggle Navigation Menu"
          >
            {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer Menu */}
      {mobileMenuOpen && (
        <div className="md:hidden bg-slate-950/95 border-b border-slate-800 px-4 pt-4 pb-6 space-y-4 backdrop-blur-xl animate-in slide-in-from-top-4 duration-200">
          <div className="flex flex-col space-y-2">
            {navLinks.map((link) => (
              <a
                key={link.label}
                href={link.href}
                onClick={(e) => handleScrollTo(e, link.href)}
                className="text-sm font-medium text-slate-300 hover:text-cyan-300 px-3 py-2 rounded-lg hover:bg-slate-900 transition-colors"
              >
                {link.label}
              </a>
            ))}
          </div>

          <div className="pt-4 border-t border-slate-800/80 flex flex-col gap-2.5">
            <Button
              variant="tactile"
              size="md"
              onClick={() => {
                setMobileMenuOpen(false);
                onGetStarted();
              }}
              className="w-full justify-center"
            >
              Get Started Free
              <ArrowRight className="w-4 h-4 ml-1.5" />
            </Button>

            <button
              onClick={() => {
                setMobileMenuOpen(false);
                onSignIn();
              }}
              className="w-full text-center text-sm font-medium text-slate-300 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-200 transition-colors"
            >
              Sign In to Your Account
            </button>
          </div>
        </div>
      )}
    </header>
  );
};
