import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { LandingPage } from '../pages/LandingPage';
import { LandingNavbar } from '../components/landing/LandingNavbar';
import { HeroSection } from '../components/landing/HeroSection';
import { StorytellingSection } from '../components/landing/StorytellingSection';
import { ProblemComparison } from '../components/landing/ProblemComparison';
import { HowItWorks } from '../components/landing/HowItWorks';
import { TutorDemo } from '../components/landing/TutorDemo';
import { FeatureGrid } from '../components/landing/FeatureGrid';
import { FinalCTA } from '../components/landing/FinalCTA';
import { LandingFooter } from '../components/landing/LandingFooter';

describe('Cinematic Introduction Landing Page Suite', () => {
  it('renders LandingNavbar with logo, navigation links, and action buttons', () => {
    const handleSignIn = vi.fn();
    const handleGetStarted = vi.fn();
    const handleEnterApp = vi.fn();

    render(
      <LandingNavbar
        onSignIn={handleSignIn}
        onGetStarted={handleGetStarted}
        onEnterApp={handleEnterApp}
      />
    );

    expect(screen.getAllByText(/Adept/i)[0]).toBeInTheDocument();
    expect(screen.getAllByText(/How It Works/i)[0]).toBeInTheDocument();
    expect(screen.getAllByText(/Features/i)[0]).toBeInTheDocument();
    expect(screen.getByTestId('navbar-signin-button')).toBeInTheDocument();
    expect(screen.getByTestId('navbar-getstarted-button')).toBeInTheDocument();

    fireEvent.click(screen.getByTestId('navbar-signin-button'));
    expect(handleSignIn).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByTestId('navbar-getstarted-button'));
    expect(handleGetStarted).toHaveBeenCalledTimes(1);
  });

  it('renders HeroSection with grand display headline and action buttons', () => {
    const handleStart = vi.fn();
    const handleExplore = vi.fn();

    render(
      <HeroSection
        onStartLearning={handleStart}
        onExploreHowItWorks={handleExplore}
      />
    );

    expect(
      screen.getByText(/Powered by intelligence that adapts to you/i)
    ).toBeInTheDocument();
    expect(screen.getByTestId('hero-start-button')).toBeInTheDocument();
    expect(screen.getByTestId('hero-explore-button')).toBeInTheDocument();
    expect(screen.getByTestId('landing-knowledge-galaxy')).toBeInTheDocument();

    fireEvent.click(screen.getByTestId('hero-start-button'));
    expect(handleStart).toHaveBeenCalledTimes(1);
  });

  it('renders StorytellingSection with all required pedagogical sequence beats', () => {
    render(<StorytellingSection />);

    expect(screen.getByText(/Every student learns differently/i)).toBeInTheDocument();
    expect(screen.getByText(/Every concept has a connection/i)).toBeInTheDocument();
    expect(screen.getByText(/Every mistake reveals an opportunity/i)).toBeInTheDocument();
    expect(
      screen.getByText(/Your tutor should understand more than your answers/i)
    ).toBeInTheDocument();
    expect(screen.getByText(/Meet AdeptLearn/i)).toBeInTheDocument();
  });

  it('renders ProblemComparison comparing Traditional AI vs AdeptLearn', () => {
    render(<ProblemComparison />);

    expect(screen.getByText(/The problem with/i)).toBeInTheDocument();
    expect(screen.getByText(/Traditional AI Chatbots/i)).toBeInTheDocument();
    expect(screen.getByText(/Bayesian Knowledge Tracing/i)).toBeInTheDocument();
    expect(screen.getByText(/Free Spaced Repetition/i)).toBeInTheDocument();
  });

  it('renders HowItWorks 4-step pipeline', () => {
    render(<HowItWorks />);

    expect(screen.getByText('01')).toBeInTheDocument();
    expect(screen.getByText('Diagnose')).toBeInTheDocument();
    expect(screen.getByText('02')).toBeInTheDocument();
    expect(screen.getByText('Map')).toBeInTheDocument();
    expect(screen.getByText('03')).toBeInTheDocument();
    expect(screen.getByText('Adapt')).toBeInTheDocument();
    expect(screen.getByText('04')).toBeInTheDocument();
    expect(screen.getByText('Master')).toBeInTheDocument();
  });

  it('renders TutorDemo with student dialogue and diagnostic breakdown', () => {
    render(<TutorDemo />);

    expect(screen.getByText(/current increases when resistance increases/i)).toBeInTheDocument();
    expect(
      screen.getByText(/relationship between voltage, resistance/i)
    ).toBeInTheDocument();
    expect(screen.getByText(/1. Reasoning Analysis/i)).toBeInTheDocument();
    expect(screen.getByText(/2. Misconception Detection/i)).toBeInTheDocument();
  });

  it('renders FeatureGrid with 6 core pillars', () => {
    render(<FeatureGrid />);

    expect(screen.getByText('Diagnostic Assessment')).toBeInTheDocument();
    expect(screen.getByText('Learner Knowledge Model')).toBeInTheDocument();
    expect(screen.getByText('Intelligent Question Generation')).toBeInTheDocument();
    expect(screen.getByText('Misconception Detection')).toBeInTheDocument();
    expect(screen.getByText('Spaced Repetition (FSRS)')).toBeInTheDocument();
    expect(screen.getByText('Teacher & Cohort Analytics')).toBeInTheDocument();
  });

  it('renders FinalCTA with headline and start button', () => {
    const handleStart = vi.fn();
    render(<FinalCTA onStartJourney={handleStart} />);

    expect(screen.getByText(/Stop studying everything/i)).toBeInTheDocument();
    expect(screen.getByTestId('final-cta-start-button')).toBeInTheDocument();

    fireEvent.click(screen.getByTestId('final-cta-start-button'));
    expect(handleStart).toHaveBeenCalledTimes(1);
  });

  it('renders LandingFooter with brand and copyright', () => {
    render(
      <LandingFooter
        onSignIn={vi.fn()}
        onRegister={vi.fn()}
        onEnterApp={vi.fn()}
      />
    );

    expect(screen.getAllByText(/Adept/i)[0]).toBeInTheDocument();
    expect(screen.getByText(/contact@adeptlearn.edu/i)).toBeInTheDocument();
    expect(screen.getByText(/All rights reserved/i)).toBeInTheDocument();
  });

  it('renders full LandingPage and opens AuthModal when Sign In is clicked', () => {
    const handleEnterApp = vi.fn();
    render(<LandingPage onEnterApp={handleEnterApp} />);

    // Check key landing landmarks
    expect(screen.getByTestId('landing-navbar')).toBeInTheDocument();
    expect(screen.getByTestId('landing-knowledge-galaxy')).toBeInTheDocument();

    // Click Sign In
    fireEvent.click(screen.getByTestId('navbar-signin-button'));
    expect(screen.getByTestId('auth-modal')).toBeInTheDocument();
    expect(screen.getByText(/Welcome Back/i)).toBeInTheDocument();
  });
});
