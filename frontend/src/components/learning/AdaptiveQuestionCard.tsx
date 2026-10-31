import React, { useState, useEffect } from 'react';
import {
  Lightbulb,
  Send,
  HelpCircle,
  Code,
  CheckCircle2,
  Clock,
  Sparkles,
  ArrowRight,
  RefreshCw,
} from 'lucide-react';
import { Question, StudentResponse, EvaluationResult } from '../../types';
import { Badge } from '../common/Badge';
import { HintDrawer } from './HintDrawer';
import { FeedbackCard } from './FeedbackCard';
import { ExplainerDrawer } from '../tutor/ExplainerDrawer';
import { SegmentedProgressBar } from '../tutor/SegmentedProgressBar';
import { Button } from '../ui/Button';

interface AdaptiveQuestionCardProps {
  question: Question;
  questionIndex: number;
  totalQuestions: number;
  onSubmit: (response: StudentResponse) => Promise<EvaluationResult>;
  onNextQuestion: () => void;
  onReviewPrerequisite?: (conceptId: number) => void;
}

export const AdaptiveQuestionCard: React.FC<AdaptiveQuestionCardProps> = ({
  question,
  questionIndex,
  totalQuestions,
  onSubmit,
  onNextQuestion,
  onReviewPrerequisite,
}) => {
  const [selectedOption, setSelectedOption] = useState<string>('');
  const [textInput, setTextInput] = useState<string>('');
  const [hintsRequested, setHintsRequested] = useState<number>(0);
  const [isHintOpen, setIsHintOpen] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [evaluationResult, setEvaluationResult] = useState<EvaluationResult | null>(null);
  const [startTime, setStartTime] = useState<number>(Date.now());

  // Reset state when question changes
  useEffect(() => {
    setSelectedOption('');
    setTextInput('');
    setHintsRequested(0);
    setIsHintOpen(false);
    setIsSubmitting(false);
    setEvaluationResult(null);
    setStartTime(Date.now());
  }, [question.id]);

  // Global hotkeys 1-4 for MCQ selection & Enter to submit
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (['INPUT', 'TEXTAREA'].includes((e.target as HTMLElement)?.tagName)) return;

      if (!evaluationResult && question.questionType === 'mcq' && question.options) {
        const keyNum = parseInt(e.key, 10);
        if (keyNum >= 1 && keyNum <= question.options.length) {
          const opt = question.options[keyNum - 1];
          if (opt) setSelectedOption(opt.id);
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [evaluationResult, question]);

  const handleRequestHint = () => {
    setIsHintOpen(true);
    setHintsRequested((prev) => Math.min(prev + 1, (question.hints?.length || 1) - 1));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isSubmitting) return;

    if (question.questionType === 'mcq' && !selectedOption) return;
    if (question.questionType === 'text' && !textInput.trim()) return;

    setIsSubmitting(true);
    const timeSpent = Math.max(1, Math.round((Date.now() - startTime) / 1000));

    try {
      const result = await onSubmit({
        questionId: question.id,
        selectedOptionId: question.questionType === 'mcq' ? selectedOption : undefined,
        responseText: question.questionType === 'text' ? textInput : undefined,
        timeSpentSeconds: timeSpent,
        hintsRequested,
      });
      setEvaluationResult(result);
    } catch (err) {
      console.error('Error submitting response:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRetry = () => {
    setEvaluationResult(null);
    setSelectedOption('');
    setTextInput('');
    setStartTime(Date.now());
  };

  return (
    <div
      className="p-6 rounded-2xl bg-background-card border border-slate-800/80 shadow-card-soft glass-card-hover"
      data-testid="adaptive-question-card"
    >
      {/* Top Question Header: Index, Concept, Difficulty, Segmented Progress */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-5 border-b border-slate-800/80 pb-4">
        <div className="flex items-center gap-2.5">
          <span className="w-8 h-8 rounded-xl bg-blue-600/20 border border-blue-500/30 flex items-center justify-center font-bold text-xs text-cyan-300">
            {questionIndex + 1}
          </span>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-semibold text-xs text-slate-200">
                Drill {questionIndex + 1} of {totalQuestions}
              </span>
              <Badge
                label={question.difficultyLevel}
                variant="difficulty"
                level={question.difficultyLevel}
                size="sm"
              />
            </div>
            <p className="text-[11px] text-slate-400">{question.conceptName}</p>
          </div>
        </div>

        {/* Duolingo-style Segmented Progress Bar */}
        <div className="w-36 sm:w-48">
          <SegmentedProgressBar
            totalSegments={totalQuestions}
            currentSegment={questionIndex + 1}
          />
        </div>
      </div>

      {/* Question Prompt */}
      <div className="mb-6">
        <h2 className="text-base sm:text-lg font-medium text-slate-100 leading-relaxed">
          {question.questionText}
        </h2>

        {/* Optional code / math snippet display */}
        {question.codeSnippet && (
          <div className="mt-3 p-3.5 rounded-xl bg-slate-900 border border-slate-700/80 font-mono text-xs sm:text-sm text-cyan-300 flex items-center gap-2.5 overflow-x-auto shadow-inner">
            <Code className="w-4 h-4 text-slate-400 shrink-0" />
            <pre className="tracking-wide">{question.codeSnippet}</pre>
          </div>
        )}
      </div>

      {/* Answer Form or Feedback Card + Explainer Drawer */}
      {evaluationResult ? (
        <div className="space-y-4">
          <FeedbackCard
            result={evaluationResult}
            onNextQuestion={onNextQuestion}
            onRetry={handleRetry}
            onReviewPrerequisite={onReviewPrerequisite}
          />
          <ExplainerDrawer
            isCorrect={evaluationResult.isCorrect}
            explanation={evaluationResult.explanation}
            conceptName={question.conceptName}
            onNextQuestion={onNextQuestion}
          />
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Options: MCQ with tactile depth and keyboard hotkeys */}
          {question.questionType === 'mcq' && question.options && (
            <div className="space-y-2.5" role="radiogroup" aria-label="Question options">
              {question.options.map((opt, idx) => {
                const isSelected = selectedOption === opt.id;
                return (
                  <button
                    key={opt.id}
                    type="button"
                    onClick={() => setSelectedOption(opt.id)}
                    className={`w-full text-left p-3.5 rounded-xl border transition-all flex items-start justify-between gap-3 group active:translate-y-[1px] ${
                      isSelected
                        ? 'bg-blue-600/20 border-cyan-400 text-slate-100 shadow-[0_0_20px_rgba(6,182,212,0.25)] ring-1 ring-cyan-400'
                        : 'bg-slate-900/60 border-slate-800 text-slate-300 hover:bg-slate-800/80 hover:border-slate-700'
                    }`}
                    data-testid={`option-${opt.id}`}
                  >
                    <div className="flex items-start gap-3 min-w-0">
                      <span
                        className={`w-6 h-6 rounded-lg flex items-center justify-center font-bold text-xs shrink-0 transition-colors ${
                          isSelected
                            ? 'bg-cyan-500 text-slate-950 shadow-glow-cyan'
                            : 'bg-slate-800 text-slate-400 group-hover:text-slate-200'
                        }`}
                      >
                        {opt.id}
                      </span>
                      <span className="text-xs sm:text-sm pt-0.5 leading-relaxed">{opt.text}</span>
                    </div>

                    <kbd className="hidden sm:inline-block text-[10px] font-mono text-slate-500 bg-slate-950 px-1.5 py-0.5 rounded border border-slate-800 shrink-0">
                      {idx + 1}
                    </kbd>
                  </button>
                );
              })}
            </div>
          )}

          {/* Text input for open algebraic responses */}
          {question.questionType === 'text' && (
            <div className="space-y-2">
              <label htmlFor="answer-input" className="block text-xs font-medium text-slate-300">
                Enter your exact calculated answer or constant:
              </label>
              <div className="relative">
                <input
                  id="answer-input"
                  type="text"
                  value={textInput}
                  onChange={(e) => setTextInput(e.target.value)}
                  placeholder="e.g. 2 or 3x^2"
                  className="w-full px-4 py-3 rounded-xl bg-slate-900 border border-slate-700 focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400 text-slate-100 placeholder-slate-500 text-sm font-mono outline-none transition-all"
                  data-testid="text-answer-input"
                />
              </div>
            </div>
          )}

          {/* Socratic Hint Drawer */}
          {question.hints && question.hints.length > 0 && (
            <HintDrawer
              hints={question.hints}
              currentHintIndex={hintsRequested}
              isOpen={isHintOpen}
              onToggle={() => setIsHintOpen(!isHintOpen)}
              onRequestNextHint={handleRequestHint}
            />
          )}

          {/* Form Actions: Request Hint & Submit */}
          <div className="flex items-center justify-between pt-2">
            <button
              type="button"
              onClick={handleRequestHint}
              className="px-3.5 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-amber-300 border border-amber-500/30 hover:border-amber-500/50 text-xs font-semibold flex items-center gap-1.5 transition-colors"
              data-testid="request-hint-button"
            >
              <Lightbulb className="w-3.5 h-3.5 fill-amber-400/20" />
              <span>{isHintOpen ? 'Hint Active' : 'Request Socratic Hint'}</span>
            </button>

            <Button
              type="submit"
              variant="tactile"
              size="md"
              disabled={
                isSubmitting ||
                (question.questionType === 'mcq' && !selectedOption) ||
                (question.questionType === 'text' && !textInput.trim())
              }
              isLoading={isSubmitting}
              className="text-xs tracking-wide"
              data-testid="submit-answer-button"
            >
              <span>Submit Answer</span>
              <Send className="w-3.5 h-3.5" />
            </Button>
          </div>
        </form>
      )}
    </div>
  );
};
