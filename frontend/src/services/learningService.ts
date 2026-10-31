import {
  Subject,
  Chapter,
  Concept,
  Question,
  StudentResponse,
  EvaluationResult,
  MasteryTier,
} from '../types';
import {
  mockSubjects,
  mockChapters,
  mockConcepts,
  mockQuestions,
  mockMasteryRecords,
} from '../mock/mockData';
import { api, apiConfig, simulateDelay } from './apiClient';

function classifyMastery(prob: number): MasteryTier {
  if (prob >= 0.90) return 'Mastered';
  if (prob >= 0.70) return 'Good Understanding';
  if (prob >= 0.40) return 'Developing Understanding';
  return 'Weak Understanding';
}

export class LearningService {
  async getSubjects(): Promise<Subject[]> {
    if (!apiConfig.useMock) {
      try {
        const remoteSubjects = await api.get<any[]>('/subjects');
        if (Array.isArray(remoteSubjects) && remoteSubjects.length > 0) {
          return remoteSubjects.map((s) => ({
            id: s.id,
            code: s.code || `SUBJ${s.id}`,
            name: s.name,
            description: s.description || 'Core syllabus module',
            totalChapters: s.chapters_count || 3,
            totalConcepts: 7,
            iconName: s.id === 1 ? 'Compass' : s.id === 2 ? 'Layers' : 'Code',
            colorScheme: s.id === 1 ? 'electric' : s.id === 2 ? 'cyan' : 'purple',
          }));
        }
      } catch (err) {
        console.warn('LearningService.getSubjects remote failed, using mock fallback:', err);
      }
    }

    await simulateDelay();
    return [...mockSubjects];
  }

  async getChapters(subjectId: number): Promise<Chapter[]> {
    if (!apiConfig.useMock) {
      try {
        const remoteChapters = await api.get<any[]>(`/chapters?subject_id=${subjectId}`);
        if (Array.isArray(remoteChapters) && remoteChapters.length > 0) {
          return remoteChapters.map((c) => ({
            id: c.id,
            subjectId: c.subject_id,
            chapterNumber: c.chapter_number,
            title: c.title,
            description: c.description || '',
            conceptCount: c.concept_count || 3,
          }));
        }
      } catch (err) {
        console.warn('LearningService.getChapters remote failed, using mock fallback:', err);
      }
    }

    await simulateDelay();
    return mockChapters.filter((c) => c.subjectId === subjectId);
  }

  async getConcepts(subjectId: number, chapterId?: number): Promise<Concept[]> {
    if (!apiConfig.useMock) {
      try {
        const query = chapterId ? `?chapter_id=${chapterId}` : `?subject_id=${subjectId}`;
        const remoteConcepts = await api.get<any[]>(`/concepts${query}`);
        if (Array.isArray(remoteConcepts) && remoteConcepts.length > 0) {
          return remoteConcepts.map((c) => ({
            id: c.id,
            conceptCode: c.code || `CONCEPT_${c.id}`,
            subjectId: c.subject_id || subjectId,
            chapterId: c.chapter_id || (chapterId || 1),
            name: c.name,
            description: c.description || '',
            difficultyLevel: (c.difficulty_level || 'beginner').toLowerCase() as any,
            learningObjectives: c.learning_objectives || ['Understand foundational mechanics'],
            prerequisiteIds: c.prerequisites || [],
            dependentIds: c.dependents || [],
          }));
        }
      } catch (err) {
        console.warn('LearningService.getConcepts remote failed, using mock fallback:', err);
      }
    }

    await simulateDelay();
    return mockConcepts.filter((c) => {
      if (c.subjectId !== subjectId) return false;
      if (chapterId && c.chapterId !== chapterId) return false;
      return true;
    });
  }

  async getConceptById(conceptId: number): Promise<Concept | null> {
    if (!apiConfig.useMock) {
      try {
        const c = await api.get<any>(`/concepts/${conceptId}`);
        if (c && c.id) {
          return {
            id: c.id,
            conceptCode: c.code || `CONCEPT_${c.id}`,
            subjectId: c.subject_id || 1,
            chapterId: c.chapter_id || 1,
            name: c.name,
            description: c.description || '',
            difficultyLevel: (c.difficulty_level || 'beginner').toLowerCase() as any,
            learningObjectives: c.learning_objectives || ['Master key conceptual mechanics'],
            prerequisiteIds: c.prerequisites || [],
            dependentIds: c.dependents || [],
          };
        }
      } catch (err) {
        console.warn(`LearningService.getConceptById(${conceptId}) remote failed, using mock fallback:`, err);
      }
    }

    await simulateDelay();
    const concept = mockConcepts.find((c) => c.id === conceptId);
    return concept || null;
  }

  async getQuestionsForConcept(conceptId: number): Promise<Question[]> {
    await simulateDelay();
    const questions = mockQuestions.filter((q) => q.conceptId === conceptId);
    if (questions.length === 0) {
      return [...mockQuestions];
    }
    return questions;
  }

  async getNextRecommendedQuestion(conceptId?: number): Promise<Question> {
    if (!apiConfig.useMock) {
      try {
        const sessionPayload = {
          subject_id: 1,
          session_type: 'ADAPTIVE_PRACTICE',
          target_concept_id: conceptId || undefined,
          question_count: 5,
        };
        const sess = await api.post<any>('/assessments/sessions', sessionPayload);
        if (sess && Array.isArray(sess.questions) && sess.questions.length > 0) {
          const q = sess.questions[0];
          return {
            id: q.id,
            conceptId: q.concept_id,
            conceptName: 'Active Target Concept',
            chapterTitle: 'Target Chapter',
            subjectName: 'Calculus I & Real Analysis',
            questionType: (q.question_type || 'mcq').toLowerCase() as any,
            difficultyLevel: (q.difficulty_level || 'beginner').toLowerCase() as any,
            questionText: q.question_text,
            options: (q.question_options || []).map((opt: any) => ({
              id: opt.id,
              text: opt.text,
              explanation: opt.explanation,
            })),
            correctAnswer: 'B', // Practice view sanitizes correct_answer
            hints: [
              'Consider the denominator constraints: sqrt(x - 3) must be strictly positive.',
              'A fraction 1/u is defined when u > 0 and u != 0.',
            ],
            evaluationRubric: {
              keyConcepts: ['Domain Analysis', 'Radical Constraints'],
              partialCreditCriteria: 'Recognizing radicand non-negativity without strict denominator positivity',
              explanation: 'Because the radical is in the denominator, x - 3 must be strictly greater than 0, giving x > 3.',
            },
          };
        }
      } catch (err) {
        console.warn('LearningService.getNextRecommendedQuestion remote failed, using mock fallback:', err);
      }
    }

    await simulateDelay();
    if (conceptId) {
      const match = mockQuestions.find((q) => q.conceptId === conceptId);
      if (match) return match;
    }
    return mockQuestions[0];
  }

  async submitAnswer(response: StudentResponse): Promise<EvaluationResult> {
    // If Live API is enabled, attempt live backend evaluation
    if (!apiConfig.useMock) {
      try {
        const answerText = response.selectedOptionId || response.responseText || '';
        const submissionPayload = {
          question_id: response.questionId,
          response_text: answerText,
          confidence_score: response.confidenceScore || 0.85,
          time_spent_ms: (response.timeSpentSeconds || 10) * 1000,
        };

        const evalRes = await api.post<any>('/assessments/submit', submissionPayload);
        if (evalRes && typeof evalRes.is_correct === 'boolean') {
          const prevProb = evalRes.previous_mastery_probability ?? 0.30;
          const newProb = evalRes.new_mastery_probability ?? (evalRes.is_correct ? prevProb + 0.14 : prevProb - 0.08);
          const delta = Number((newProb - prevProb).toFixed(3));
          const newClass = classifyMastery(newProb);

          return {
            outcome: evalRes.is_correct ? 'correct' : 'incorrect',
            isCorrect: evalRes.is_correct,
            score: evalRes.is_correct ? 1.0 : 0.0,
            correctAnswer: evalRes.correct_answer || answerText,
            explanation: evalRes.ai_feedback || (evalRes.is_correct ? 'Excellent! Live BKT state updated.' : 'Answer evaluated by live backend engine.'),
            socraticHint: evalRes.is_correct ? undefined : 'Review the fundamental definition before your next attempt.',
            conceptClarification: evalRes.is_correct
              ? 'Your response was validated by the live BKT learner model.'
              : 'The posterior probability of mastery has been calibrated according to your response.',
            previousMastery: Number(prevProb.toFixed(2)),
            updatedMastery: Number(newProb.toFixed(2)),
            masteryDelta: delta,
            newClassification: newClass,
            recommendedAction: evalRes.is_correct
              ? {
                  type: newProb >= 0.90 ? 'concept_mastered' : 'next_question',
                  message: newProb >= 0.90
                    ? 'Concept Mastered on Live Engine! Ready to advance.'
                    : 'Great progress. Keep momentum going with the next item.',
                }
              : {
                  type: 'retry',
                  message: 'Review the underlying constraints and retry.',
                },
          };
        }
      } catch (err) {
        console.warn('LearningService.submitAnswer live call failed, falling back to deterministic mock engine:', err);
      }
    }

    // Deterministic Mock Engine (Headless tests & offline mode)
    await simulateDelay(250);
    const question = mockQuestions.find((q) => q.id === response.questionId);
    if (!question) {
      throw new Error(`Question ID ${response.questionId} not found.`);
    }
    const currentRecord = mockMasteryRecords.find((m) => m.conceptId === question.conceptId);
    const previousMastery = currentRecord ? currentRecord.currentMastery : 0.30;

    let isCorrect = false;
    let isPartial = false;
    let explanation = '';
    let socraticHint = '';
    let conceptClarification = '';

    if (question.questionType === 'mcq') {
      const selected = response.selectedOptionId;
      isCorrect = selected === question.correctAnswer;
      const matchedOption = question.options?.find((o) => o.id === selected);
      explanation = matchedOption?.explanation || (isCorrect ? 'Correct choice!' : 'Incorrect choice.');

      if (!isCorrect && question.id === 101 && selected === 'A') {
        isPartial = true;
      }
    } else {
      const cleanUserText = (response.responseText || '').trim().toLowerCase();
      const cleanCorrect = question.correctAnswer.trim().toLowerCase();

      if (cleanUserText === cleanCorrect) {
        isCorrect = true;
        explanation = 'Perfect algebraic solution!';
      } else if (cleanUserText.includes('8') || cleanUserText.includes('3c')) {
        isPartial = true;
        explanation = 'You correctly identified that the limit boundary must equal 8, but the final value of c needs revision.';
      } else {
        isCorrect = false;
        explanation = `The correct expected value is ${question.correctAnswer}.`;
      }
    }

    let outcome: 'correct' | 'partially_correct' | 'incorrect' = 'incorrect';
    let masteryDelta = 0;

    if (isCorrect) {
      outcome = 'correct';
      masteryDelta = +0.14;
      conceptClarification = `Great mastery of "${question.conceptName}". You correctly chained the inner derivative with the outer power law.`;
    } else if (isPartial) {
      outcome = 'partially_correct';
      masteryDelta = +0.04;
      socraticHint = 'Notice how the inner function u(x) has a non-zero derivative. What is d/dx [3x² - 5x + 4]?';
      conceptClarification = 'You correctly differentiated the outer exponent, but omitted the chain factor representing the rate of change of the inner function.';
    } else {
      outcome = 'incorrect';
      masteryDelta = -0.08;
      socraticHint = question.hints[0] || 'Try decomposing into outer and inner functions first.';
      conceptClarification = question.evaluationRubric?.explanation || 'Review the core prerequisite definitions before retrying.';
    }

    const updatedMastery = Math.max(0.05, Math.min(0.99, Number((previousMastery + masteryDelta).toFixed(2))));
    const newClassification = classifyMastery(updatedMastery);

    if (currentRecord) {
      currentRecord.currentMastery = updatedMastery;
      currentRecord.masteryClassification = newClassification;
      currentRecord.totalAttempts += 1;
      if (isCorrect) currentRecord.correctAttempts += 1;
      else currentRecord.incorrectAttempts += 1;
      currentRecord.lastAttemptAt = new Date().toISOString();
      currentRecord.history.push({
        timestamp: new Date().toISOString(),
        isCorrect,
        previousMastery,
        updatedMastery,
      });
    }

    return {
      outcome,
      isCorrect,
      score: isCorrect ? 1.0 : isPartial ? 0.5 : 0.0,
      correctAnswer: question.correctAnswer,
      explanation,
      socraticHint: isCorrect ? undefined : socraticHint,
      conceptClarification,
      previousMastery,
      updatedMastery,
      masteryDelta,
      newClassification,
      recommendedAction: isCorrect
        ? {
            type: updatedMastery >= 0.90 ? 'concept_mastered' : 'next_question',
            message: updatedMastery >= 0.90
              ? 'Concept Mastered! Ready to advance to the next syllabus module.'
              : 'Keep momentum going with the next adaptive practice item.',
          }
        : isPartial
        ? {
            type: 'retry',
            message: 'You have the right foundation. Review the inner derivative step and try another attempt.',
          }
        : {
            type: 'review_prerequisite',
            message: 'Recommended: Review foundational limits and differentiation rules before retesting.',
            targetConceptId: 4,
            targetConceptName: 'Definition of the Derivative',
          },
    };
  }

  async requestHint(questionId: number, currentHintIndex: number): Promise<{ hint: string; hasMore: boolean }> {
    await simulateDelay(100);
    const question = mockQuestions.find((q) => q.id === questionId);
    if (!question || !question.hints || question.hints.length === 0) {
      return { hint: 'Review the problem statement carefully and identify what is being asked.', hasMore: false };
    }
    const safeIndex = Math.min(currentHintIndex, question.hints.length - 1);
    const hint = question.hints[safeIndex];
    const hasMore = safeIndex < question.hints.length - 1;
    return { hint, hasMore };
  }
}

export const learningService = new LearningService();
