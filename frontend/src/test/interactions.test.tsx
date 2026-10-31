import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AdaptiveQuestionCard } from '../components/learning/AdaptiveQuestionCard';
import { Sidebar } from '../components/common/Sidebar';
import { mockQuestions } from '../mock/mockData';
import { EvaluationResult } from '../types';

describe('User Interaction Flow Tests', () => {
  it('allows user to select MCQ option and submit for evaluation', async () => {
    const user = userEvent.setup();
    const handleSubmit = vi.fn().mockResolvedValue({
      outcome: 'correct',
      isCorrect: true,
      score: 1.0,
      correctAnswer: 'B',
      explanation: 'Correct application of chain rule.',
      conceptClarification: 'Inner derivative was retained and chained.',
      previousMastery: 0.29,
      updatedMastery: 0.43,
      masteryDelta: 0.14,
      newClassification: 'Developing Understanding',
      recommendedAction: { type: 'next_question', message: 'Continue momentum' },
    } as EvaluationResult);

    render(
      <AdaptiveQuestionCard
        question={mockQuestions[0]}
        questionIndex={0}
        totalQuestions={4}
        onSubmit={handleSubmit}
        onNextQuestion={vi.fn()}
      />
    );

    // Initial state: submit button should be disabled until option selected
    const submitBtn = screen.getByTestId('submit-answer-button');
    expect(submitBtn).toBeDisabled();

    // Select option B
    const optionB = screen.getByTestId('option-B');
    await user.click(optionB);

    // Submit button should now be enabled
    expect(submitBtn).not.toBeDisabled();

    // Click submit
    await user.click(submitBtn);

    // Verify submission was called with selected option
    await waitFor(() => {
      expect(handleSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          questionId: 101,
          selectedOptionId: 'B',
        })
      );
    });

    // Feedback view appears with next question button
    await waitFor(() => {
      expect(screen.getByTestId('next-question-button')).toBeInTheDocument();
      expect(screen.getByText(/Outstanding! Correct Answer/i)).toBeInTheDocument();
    });
  });

  it('reveals progressive Socratic hints when hint button is clicked', async () => {
    const user = userEvent.setup();

    render(
      <AdaptiveQuestionCard
        question={mockQuestions[0]}
        questionIndex={0}
        totalQuestions={4}
        onSubmit={vi.fn()}
        onNextQuestion={vi.fn()}
      />
    );

    const hintBtn = screen.getByTestId('request-hint-button');
    await user.click(hintBtn);

    // Hint drawer should be visible with Hint Level 1
    await waitFor(() => {
      expect(screen.getByTestId('hint-drawer')).toBeInTheDocument();
      expect(screen.getByTestId('hint-step-0')).toBeInTheDocument();
    });

    // Request next clue
    const nextHintBtn = screen.getByTestId('request-next-hint-button');
    await user.click(nextHintBtn);

    await waitFor(() => {
      expect(screen.getByTestId('hint-step-1')).toBeInTheDocument();
    });
  });

  it('triggers tab switching when sidebar items are clicked', async () => {
    const user = userEvent.setup();
    const handleSelectTab = vi.fn();

    render(
      <Sidebar
        activeTab="dashboard"
        onSelectTab={handleSelectTab}
        isOpenMobile={false}
        onCloseMobile={vi.fn()}
      />
    );

    const learnTab = screen.getByTestId('nav-item-learn');
    await user.click(learnTab);
    expect(handleSelectTab).toHaveBeenCalledWith('learn');

    const progressTab = screen.getByTestId('nav-item-progress');
    await user.click(progressTab);
    expect(handleSelectTab).toHaveBeenCalledWith('progress');
  });
});
