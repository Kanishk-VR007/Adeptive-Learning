import React, { useState } from 'react';
import { LandingNavbar } from '../components/landing/LandingNavbar';
import { HeroSection } from '../components/landing/HeroSection';
import { StorytellingSection } from '../components/landing/StorytellingSection';
import { ProblemComparison } from '../components/landing/ProblemComparison';
import { HowItWorks } from '../components/landing/HowItWorks';
import { TutorDemo } from '../components/landing/TutorDemo';
import { FeatureGrid } from '../components/landing/FeatureGrid';
import { FinalCTA } from '../components/landing/FinalCTA';
import { LandingFooter } from '../components/landing/LandingFooter';
import { AuthModal } from '../components/landing/AuthModal';

interface LandingPageProps {
  onEnterApp: () => void;
}

export const LandingPage: React.FC<LandingPageProps> = ({ onEnterApp }) => {
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login');

  const handleOpenLogin = () => {
    setAuthMode('login');
    setAuthModalOpen(true);
  };

  const handleOpenRegister = () => {
    setAuthMode('register');
    setAuthModalOpen(true);
  };

  const handleScrollToHowItWorks = () => {
    const el = document.getElementById('how-it-works');
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col selection:bg-cyan-500/30 selection:text-cyan-200">
      {/* SECTION 1: Navigation Bar */}
      <LandingNavbar
        onSignIn={handleOpenLogin}
        onGetStarted={handleOpenRegister}
        onEnterApp={onEnterApp}
      />

      {/* Main Sections Content */}
      <main className="flex-1">
        {/* SECTION 2 & 3: Cinematic Hero & 3D Knowledge Galaxy */}
        <HeroSection
          onStartLearning={handleOpenRegister}
          onExploreHowItWorks={handleScrollToHowItWorks}
        />

        {/* SECTION 4: Scroll-Triggered Storytelling */}
        <StorytellingSection />

        {/* SECTION 5: The Problem with Generic AI Tutors */}
        <ProblemComparison />

        {/* SECTION 6: How AdeptLearn Works (4-Step Pipeline) */}
        <HowItWorks />

        {/* SECTION 7: Meet Your AI Tutor (Interactive Socratic Dialogue) */}
        <TutorDemo />

        {/* SECTION 8: Core Features (6 Pillars) */}
        <FeatureGrid />

        {/* SECTION 9: Final Call to Action */}
        <FinalCTA onStartJourney={handleOpenRegister} />
      </main>

      {/* SECTION 10: Footer */}
      <LandingFooter
        onSignIn={handleOpenLogin}
        onRegister={handleOpenRegister}
        onEnterApp={onEnterApp}
      />

      {/* Auth Modal for Login and Registration */}
      <AuthModal
        isOpen={authModalOpen}
        initialMode={authMode}
        onClose={() => setAuthModalOpen(false)}
        onSuccess={() => {
          setAuthModalOpen(false);
          onEnterApp();
        }}
      />
    </div>
  );
};
