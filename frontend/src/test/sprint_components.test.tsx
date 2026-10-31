import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Button } from '../components/ui/Button';
import { Card, CardHeader, CardContent } from '../components/ui/Card';
import { Omnibar } from '../components/ui/Omnibar';
import { SegmentedProgressBar } from '../components/tutor/SegmentedProgressBar';
import { ExplainerDrawer } from '../components/tutor/ExplainerDrawer';
import { LeitnerBoxTracker } from '../components/revision/LeitnerBoxTracker';
import { SpacedFlashcardDeck } from '../components/revision/SpacedFlashcardDeck';
import { KnowledgeGalaxy } from '../components/galaxy/KnowledgeGalaxy';
import { mockMasteryRecords, mockSubjects, mockRevisionItems } from '../mock/mockData';

describe('AdeptLearn Sprint-Ready Components (REA Reverse-Engineered)', () => {
  describe('Tactile Button Component', () => {
    it('renders tactile 3D button with proper variant class and handles clicks', async () => {
      const user = userEvent.setup();
      const handleClick = vi.fn();

      render(
        <Button variant="tactile" size="md" onClick={handleClick}>
          Submit Answer
        </Button>
      );

      const btn = screen.getByRole('button', { name: /Submit Answer/i });
      expect(btn).toBeInTheDocument();
      expect(btn.className).toContain('shadow-[0_4px_0_#1e40af');

      await user.click(btn);
      expect(handleClick).toHaveBeenCalledTimes(1);
    });

    it('disables button and shows spinner when isLoading is true', () => {
      render(
        <Button variant="primary" isLoading>
          Processing
        </Button>
      );

      const btn = screen.getByRole('button');
      expect(btn).toBeDisabled();
      expect(btn.querySelector('svg.animate-spin')).toBeInTheDocument();
    });
  });

  describe('Card Component', () => {
    it('renders glassmorphic card with header and content', () => {
      render(
        <Card variant="glass" hasGlowBorder>
          <CardHeader>Header Content</CardHeader>
          <CardContent>Body Content</CardContent>
        </Card>
      );

      expect(screen.getByText('Header Content')).toBeInTheDocument();
      expect(screen.getByText('Body Content')).toBeInTheDocument();
    });
  });

  describe('SegmentedProgressBar Component', () => {
    it('renders discrete segment segments and highlights active segment', () => {
      render(
        <SegmentedProgressBar
          totalSegments={5}
          currentSegment={3}
          label="Syllabus Milestone"
        />
      );

      expect(screen.getByText('Syllabus Milestone')).toBeInTheDocument();
      expect(screen.getByText('3 of 5')).toBeInTheDocument();
      const container = screen.getByTestId('segmented-progress-bar');
      expect(container).toBeInTheDocument();
      // 5 segment divs
      const segments = container.querySelectorAll('.h-2');
      expect(segments.length).toBe(5);
    });
  });

  describe('ExplainerDrawer Component', () => {
    it('renders step-by-step cognitive explainer and allows collapse/expansion', async () => {
      const user = userEvent.setup();
      const handleNext = vi.fn();

      render(
        <ExplainerDrawer
          isCorrect={true}
          explanation="Integration by parts reverses the differential product rule."
          conceptName="Integration by Parts"
          onNextQuestion={handleNext}
        />
      );

      expect(screen.getByText(/Correct! Concept Reinforced/i)).toBeInTheDocument();
      expect(screen.getByText(/Integration by parts reverses the differential product rule/i)).toBeInTheDocument();
      expect(screen.getByText(/Cognitive Step-by-Step Derivation/i)).toBeInTheDocument();

      const nextBtn = screen.getByRole('button', { name: /Continue to Next Drill/i });
      await user.click(nextBtn);
      expect(handleNext).toHaveBeenCalledTimes(1);
    });
  });

  describe('LeitnerBoxTracker Component', () => {
    it('renders 5 Leitner boxes with correct intervals and card counts', () => {
      render(<LeitnerBoxTracker boxCounts={[3, 5, 8, 12, 20]} activeBox={2} />);

      expect(screen.getByTestId('leitner-box-tracker')).toBeInTheDocument();
      expect(screen.getByText('Box 1')).toBeInTheDocument();
      expect(screen.getByText('Box 5')).toBeInTheDocument();
      expect(screen.getByText('3')).toBeInTheDocument();
      expect(screen.getByText('20')).toBeInTheDocument();
      expect(screen.getByText('Total Deck: 48 Concepts')).toBeInTheDocument();
    });
  });

  describe('SpacedFlashcardDeck Component', () => {
    it('allows 3D card flipping and confidence rating submission', async () => {
      const user = userEvent.setup();
      const handleReview = vi.fn();
      const handlePractice = vi.fn();

      render(
        <SpacedFlashcardDeck
          items={mockRevisionItems}
          onReview={handleReview}
          onPracticeConcept={handlePractice}
        />
      );

      expect(screen.getByTestId('spaced-flashcard-deck')).toBeInTheDocument();
      expect(screen.getByText(/Card 1 of/i)).toBeInTheDocument();

      // Click flip button
      const flipBtn = screen.getByRole('button', { name: /Flip Card/i });
      await user.click(flipBtn);

      // Rating buttons: Easy
      const easyBtn = screen.getByTestId('rate-easy-button');
      await user.click(easyBtn);

      expect(handleReview).toHaveBeenCalledWith(mockRevisionItems[0].id, 'easy');
    });

    it('renders empty deck message when items array is empty', () => {
      render(
        <SpacedFlashcardDeck
          items={[]}
          onReview={vi.fn()}
          onPracticeConcept={vi.fn()}
        />
      );

      expect(screen.getByTestId('empty-revision-deck')).toBeInTheDocument();
      expect(screen.getByText(/All Spaced Revisions Completed/i)).toBeInTheDocument();
    });
  });

  describe('Omnibar AI Search Component', () => {
    it('opens search modal on trigger button click, filters concepts, and invokes onStartLearning', async () => {
      const user = userEvent.setup();
      const handleStart = vi.fn();

      render(
        <Omnibar
          concepts={mockMasteryRecords}
          subjects={mockSubjects}
          onStartLearning={handleStart}
        />
      );

      const triggerBtn = screen.getByTestId('omnibar-trigger-button');
      await user.click(triggerBtn);

      // Search input appears
      const input = screen.getByTestId('omnibar-search-input');
      expect(input).toBeInTheDocument();

      // Type search term
      await user.type(input, 'Chain');

      // Matching concept result appears
      const resultItem = await screen.findByText(/The Chain Rule for Composite Functions/i);
      expect(resultItem).toBeInTheDocument();

      // Click to launch drill
      await user.click(resultItem);
      expect(handleStart).toHaveBeenCalledWith(6);
    });
  });

  describe('KnowledgeGalaxy 3D Visualization Component', () => {
    it('renders 3D canvas viewport and spatial controls', () => {
      render(
        <KnowledgeGalaxy
          masteries={mockMasteryRecords}
          subjectTitle="Calculus Module"
          onSelectConcept={vi.fn()}
        />
      );

      expect(screen.getByTestId('knowledge-galaxy-container')).toBeInTheDocument();
      expect(screen.getByText('3D Knowledge Galaxy')).toBeInTheDocument();
      expect(screen.getByText('Calculus Module')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Pause orbit/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Zoom in/i })).toBeInTheDocument();
    });
  });
});
