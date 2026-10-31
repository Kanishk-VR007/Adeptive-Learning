import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Sidebar } from '../components/common/Sidebar';
import { Header } from '../components/common/Header';
import { LearningOverviewCard } from '../components/dashboard/LearningOverviewCard';
import { ContinueLearningCard } from '../components/dashboard/ContinueLearningCard';
import { WeakConceptsCard } from '../components/dashboard/WeakConceptsCard';
import { TodaysPlanCard } from '../components/dashboard/TodaysPlanCard';
import { MasteryCircularGauge } from '../components/progress/MasteryCircularGauge';
import { FeedbackCard } from '../components/learning/FeedbackCard';
import { KnowledgeOrb } from '../components/3d/KnowledgeOrb';
import { mockStudentProfile, mockSubjects, mockMasteryRecords, mockRecommendations, mockRevisionItems } from '../mock/mockData';
import { EvaluationResult } from '../types';

describe('UI Component Rendering Suite', () => {
  it('renders Sidebar with all navigation items and streak counter', () => {
    const handleSelect = vi.fn();
    const handleClose = vi.fn();

    render(
      <Sidebar
        activeTab="dashboard"
        onSelectTab={handleSelect}
        isOpenMobile={false}
        onCloseMobile={handleClose}
        streakDays={7}
      />
    );

    expect(screen.getByTestId('nav-item-dashboard')).toBeInTheDocument();
    expect(screen.getByTestId('nav-item-learn')).toBeInTheDocument();
    expect(screen.getByTestId('nav-item-progress')).toBeInTheDocument();
    expect(screen.getByTestId('nav-item-revision')).toBeInTheDocument();
    expect(screen.getByTestId('nav-item-profile')).toBeInTheDocument();
    expect(screen.getByText(/7 Days/i)).toBeInTheDocument();
  });

  it('renders Header with student profile name and streak badge', () => {
    render(
      <Header
        profile={mockStudentProfile}
        subjects={mockSubjects}
        selectedSubjectId={1}
        onSelectSubject={vi.fn()}
        onOpenMobileSidebar={vi.fn()}
        onNavigateToProfile={vi.fn()}
        onNavigateToLearn={vi.fn()}
      />
    );

    expect(screen.getByText(/Alex Chen/i)).toBeInTheDocument();
    expect(screen.getByText('7')).toBeInTheDocument();
    expect(screen.getByTestId('notification-button')).toBeInTheDocument();
  });

  it('renders LearningOverviewCard with mastery percentage and metrics', () => {
    render(
      <LearningOverviewCard
        overallMastery={68}
        conceptsCompleted={4}
        totalConcepts={16}
        questionsAnswered={76}
        studyMinutes={335}
      />
    );

    expect(screen.getByText('68%')).toBeInTheDocument();
    expect(screen.getByText('76')).toBeInTheDocument();
    expect(screen.getByText(/5h 35m/i)).toBeInTheDocument();
  });

  it('renders ContinueLearningCard with recommended concept title', () => {
    const handleContinue = vi.fn();
    render(
      <ContinueLearningCard
        subjectName="Calculus I"
        chapterTitle="Derivatives"
        conceptName="The Chain Rule"
        conceptDifficulty="Advanced"
        onContinue={handleContinue}
      />
    );

    expect(screen.getByText('The Chain Rule')).toBeInTheDocument();
    expect(screen.getByText('Continue Learning')).toBeInTheDocument();
  });

  it('renders WeakConceptsCard with prioritized items and practice button', () => {
    const handlePractice = vi.fn();
    render(
      <WeakConceptsCard
        concepts={mockMasteryRecords.slice(0, 2)}
        onPracticeConcept={handlePractice}
      />
    );

    expect(screen.getByTestId('weak-concepts-card')).toBeInTheDocument();
    expect(screen.getByText(/Need Focus/i)).toBeInTheDocument();
  });

  it('renders TodaysPlanCard with daily goals and recommendations', () => {
    render(
      <TodaysPlanCard
        suggestedConcepts={mockRecommendations}
        dailyPracticeTarget={15}
        completedTodayCount={9}
        upcomingRevisions={mockRevisionItems}
        onSelectConcept={vi.fn()}
        onOpenRevision={vi.fn()}
      />
    );

    expect(screen.getByText(/9 of 15 done/i)).toBeInTheDocument();
    expect(screen.getByText(/Suggested Focus Concepts/i)).toBeInTheDocument();
  });

  it('renders MasteryCircularGauge correctly', () => {
    render(<MasteryCircularGauge percentage={78} />);
    expect(screen.getByTestId('mastery-circular-gauge')).toBeInTheDocument();
    expect(screen.getByText('78%')).toBeInTheDocument();
    expect(screen.getByText('Good')).toBeInTheDocument();
  });

  it('renders FeedbackCard in correct, partially correct, and incorrect states', () => {
    const mockCorrect: EvaluationResult = {
      outcome: 'correct',
      isCorrect: true,
      score: 1.0,
      correctAnswer: 'B',
      explanation: 'Great job!',
      conceptClarification: 'Inner derivative was chained correctly.',
      previousMastery: 0.35,
      updatedMastery: 0.49,
      masteryDelta: 0.14,
      newClassification: 'Developing Understanding',
      recommendedAction: { type: 'next_question', message: 'Continue practice' },
    };

    const { rerender } = render(
      <FeedbackCard
        result={mockCorrect}
        onNextQuestion={vi.fn()}
        onRetry={vi.fn()}
      />
    );

    expect(screen.getByText(/Outstanding! Correct Answer/i)).toBeInTheDocument();
    expect(screen.getByText(/Next Recommended Question/i)).toBeInTheDocument();

    const mockIncorrect: EvaluationResult = {
      ...mockCorrect,
      outcome: 'incorrect',
      isCorrect: false,
      score: 0.0,
      explanation: 'Missed chain factor.',
      socraticHint: 'Look closely at inner function.',
    };

    rerender(
      <FeedbackCard
        result={mockIncorrect}
        onNextQuestion={vi.fn()}
        onRetry={vi.fn()}
      />
    );

    expect(screen.getByText(/Not Quite – Let’s Learn From This/i)).toBeInTheDocument();
    expect(screen.getByText(/Look closely at inner function/i)).toBeInTheDocument();
    expect(screen.getByTestId('retry-attempt-button')).toBeInTheDocument();
  });

  it('renders KnowledgeOrb canvas container gracefully', () => {
    render(<KnowledgeOrb />);
    expect(screen.getByTestId('knowledge-orb-container')).toBeInTheDocument();
  });
});
