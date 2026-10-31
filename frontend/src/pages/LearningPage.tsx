import React, { useState, useEffect } from 'react';
import {
  Concept,
  Question,
  StudentResponse,
  EvaluationResult,
  Subject,
  Chapter,
} from '../types';
import { learningService } from '../services/learningService';
import { ConceptBreadcrumbs } from '../components/learning/ConceptBreadcrumbs';
import { AdaptiveQuestionCard } from '../components/learning/AdaptiveQuestionCard';
import { BookOpen } from 'lucide-react';

interface LearningPageProps {
  currentSubject: Subject;
  initialConceptId?: number;
  onNavigateHome: () => void;
  onMasteryUpdated?: () => void;
}

export const LearningPage: React.FC<LearningPageProps> = ({
  currentSubject,
  initialConceptId,
  onNavigateHome,
  onMasteryUpdated,
}) => {
  const [concepts, setConcepts] = useState<Concept[]>([]);
  const [activeConcept, setActiveConcept] = useState<Concept | null>(null);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState<number>(0);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Load concepts for current subject
  useEffect(() => {
    let isMounted = true;
    const fetchConcepts = async () => {
      setIsLoading(true);
      try {
        const list = await learningService.getConcepts(currentSubject.id);
        if (isMounted) {
          setConcepts(list);
          const target = initialConceptId
            ? list.find((c) => c.id === initialConceptId) || list[0]
            : list.find((c) => c.id === 6) || list[0]; // Default to Chain Rule if available
          setActiveConcept(target);
        }
      } catch (err) {
        console.error('Error fetching concepts:', err);
      } finally {
        if (isMounted) setIsLoading(false);
      }
    };

    fetchConcepts();
    return () => {
      isMounted = false;
    };
  }, [currentSubject.id, initialConceptId]);

  // Load questions when active concept changes
  useEffect(() => {
    if (!activeConcept) return;

    let isMounted = true;
    const fetchQuestions = async () => {
      try {
        const qList = await learningService.getQuestionsForConcept(activeConcept.id);
        if (isMounted) {
          setQuestions(qList);
          setCurrentQuestionIndex(0);
        }
      } catch (err) {
        console.error('Error fetching questions:', err);
      }
    };

    fetchQuestions();
    return () => {
      isMounted = false;
    };
  }, [activeConcept]);

  const handleSubmitResponse = async (response: StudentResponse): Promise<EvaluationResult> => {
    const result = await learningService.submitAnswer(response);
    if (onMasteryUpdated) {
      onMasteryUpdated();
    }
    return result;
  };

  const handleNextQuestion = () => {
    if (currentQuestionIndex < questions.length - 1) {
      setCurrentQuestionIndex((prev) => prev + 1);
    } else {
      // Loop or advance to next concept in sequence
      const currentIdx = concepts.findIndex((c) => c.id === activeConcept?.id);
      if (currentIdx !== -1 && currentIdx < concepts.length - 1) {
        setActiveConcept(concepts[currentIdx + 1]);
      } else {
        // Return to first question of current concept
        setCurrentQuestionIndex(0);
      }
    }
  };

  const handleReviewPrerequisite = (targetConceptId: number) => {
    const prereq = concepts.find((c) => c.id === targetConceptId);
    if (prereq) {
      setActiveConcept(prereq);
    }
  };

  if (isLoading || !activeConcept || questions.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] text-slate-400">
        <div className="w-8 h-8 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin mb-3" />
        <p className="text-sm">Initializing Adaptive Question Engine...</p>
      </div>
    );
  }

  const currentQuestion = questions[currentQuestionIndex] || questions[0];

  return (
    <div className="space-y-6 pb-12" data-testid="learning-page">
      {/* Breadcrumb Navigation */}
      <ConceptBreadcrumbs
        subjectName={currentSubject.name}
        chapterTitle={currentQuestion.chapterTitle}
        conceptName={activeConcept.name}
        onNavigateHome={onNavigateHome}
      />

      {/* Concept Selector Pills */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-none">
        <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider shrink-0 mr-1">
          Concepts:
        </span>
        {concepts.map((concept) => {
          const isSelected = concept.id === activeConcept.id;
          return (
            <button
              key={concept.id}
              onClick={() => setActiveConcept(concept)}
              className={`px-3 py-1.5 rounded-xl text-xs font-medium transition-all shrink-0 flex items-center gap-1.5 ${
                isSelected
                  ? 'bg-electric-600 text-white font-semibold shadow-glow-blue border border-cyan-400/40'
                  : 'bg-slate-900 text-slate-300 hover:bg-slate-800 border border-slate-800'
              }`}
              data-testid={`select-concept-${concept.id}`}
            >
              <span>{concept.name}</span>
            </button>
          );
        })}
      </div>

      {/* Main Adaptive Question Card */}
      <div className="max-w-4xl mx-auto">
        <AdaptiveQuestionCard
          question={currentQuestion}
          questionIndex={currentQuestionIndex}
          totalQuestions={questions.length}
          onSubmit={handleSubmitResponse}
          onNextQuestion={handleNextQuestion}
          onReviewPrerequisite={handleReviewPrerequisite}
        />
      </div>

      {/* Concept Learning Objectives Card */}
      <div className="max-w-4xl mx-auto p-4 rounded-xl bg-slate-900/50 border border-slate-800 text-xs text-slate-400">
        <div className="flex items-center gap-2 text-slate-300 font-semibold mb-2">
          <BookOpen className="w-4 h-4 text-cyan-400" />
          <span>Curriculum Objectives for {activeConcept.name}:</span>
        </div>
        <ul className="list-disc list-inside space-y-1 text-slate-300">
          {activeConcept.learningObjectives.map((obj, i) => (
            <li key={i}>{obj}</li>
          ))}
        </ul>
      </div>
    </div>
  );
};
