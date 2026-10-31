// Domain Models for Adaptive Exam-Prep Tutor
// Compatible with FastAPI Pydantic schemas

export type DifficultyLevel = 'beginner' | 'intermediate' | 'advanced';

export type QuestionType = 'mcq' | 'text' | 'multi_select';

export type MasteryTier = 'Weak Understanding' | 'Developing Understanding' | 'Good Understanding' | 'Mastered';

export interface StudentProfile {
  id: number;
  email: string;
  fullName: string;
  avatarUrl?: string;
  role: 'student' | 'instructor' | 'admin';
  studyStreakDays: number;
  lastActiveDate: string;
  targetExam: string;
  targetExamDate: string;
  weeklyGoalHours: number;
  currentWeeklyHours: number;
  preferences: {
    reducedMotion: boolean;
    soundEffects: boolean;
    dailyReminderTime: string;
  };
}

export interface Subject {
  id: number;
  code: string;
  name: string;
  description: string;
  totalChapters: number;
  totalConcepts: number;
  iconName: string;
  colorScheme: string;
}

export interface Chapter {
  id: number;
  subjectId: number;
  chapterNumber: number;
  title: string;
  description: string;
  conceptCount: number;
}

export interface Concept {
  id: number;
  conceptCode: string;
  subjectId: number;
  chapterId: number;
  name: string;
  description: string;
  difficultyLevel: DifficultyLevel;
  learningObjectives: string[];
  prerequisiteIds: number[];
  dependentIds: number[];
}

export interface ConceptMastery {
  id: number;
  studentId: number;
  conceptId: number;
  conceptCode: string;
  conceptName: string;
  chapterId: number;
  subjectId: number;
  initialMastery: number; // 0.0 to 1.0
  currentMastery: number; // 0.0 to 1.0
  masteryClassification: MasteryTier;
  totalAttempts: number;
  correctAttempts: number;
  incorrectAttempts: number;
  lastAttemptAt?: string;
  history: {
    timestamp: string;
    isCorrect: boolean;
    previousMastery: number;
    updatedMastery: number;
  }[];
}

export interface QuestionOption {
  id: string; // "A", "B", "C", "D"
  text: string;
  explanation?: string;
}

export interface Question {
  id: number;
  conceptId: number;
  conceptName: string;
  chapterTitle: string;
  subjectName: string;
  questionType: QuestionType;
  difficultyLevel: DifficultyLevel;
  questionText: string;
  codeSnippet?: string;
  options?: QuestionOption[];
  correctAnswer: string;
  hints: string[];
  evaluationRubric?: {
    keyConcepts: string[];
    partialCreditCriteria: string;
    explanation: string;
  };
}

export type EvaluationOutcome = 'correct' | 'partially_correct' | 'incorrect';

export interface StudentResponse {
  questionId: number;
  selectedOptionId?: string;
  responseText?: string;
  timeSpentSeconds: number;
  confidenceScore?: number; // 0.0 to 1.0
  hintsRequested: number;
}

export interface EvaluationResult {
  outcome: EvaluationOutcome;
  isCorrect: boolean;
  score: number; // 0.0 to 1.0
  correctAnswer: string;
  explanation: string;
  socraticHint?: string;
  conceptClarification: string;
  previousMastery: number;
  updatedMastery: number;
  masteryDelta: number;
  newClassification: MasteryTier;
  recommendedAction: {
    type: 'next_question' | 'retry' | 'review_prerequisite' | 'concept_mastered';
    message: string;
    targetConceptId?: number;
    targetConceptName?: string;
  };
}

export interface LearningRecommendation {
  id: string;
  conceptId: number;
  conceptName: string;
  subjectName: string;
  chapterTitle: string;
  reason: 'weak_concept' | 'prerequisite_gap' | 'spaced_repetition' | 'next_in_sequence';
  urgency: 'high' | 'medium' | 'low';
  estimatedMinutes: number;
  currentMastery: number;
}

export interface RevisionItem {
  id: string;
  conceptId: number;
  conceptName: string;
  subjectName: string;
  lastPracticed: string;
  dueStatus: 'due_today' | 'due_soon' | 'overdue' | 'scheduled';
  retentionEstimate: number; // 0% to 100%
  intervalDays: number;
  box?: number; // 1 to 5 Leitner stage
}

export interface GraphNode {
  id: number;
  conceptCode: string;
  name: string;
  difficultyLevel: DifficultyLevel;
  subjectId: number;
  chapterId: number;
  masteryProbability: number;
  status: 'locked' | 'ready' | 'mastered' | 'in_progress';
  tierLevel: number; // Graph layout depth (0 = foundation, 1 = intermediate, 2 = advanced)
}

export interface GraphEdge {
  fromConceptId: number;
  toConceptId: number;
  relationshipType: 'strict' | 'suggested';
}

export interface ConceptGraphData {
  subjectId: number;
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface ActivitySummary {
  date: string;
  day: string;
  questionsAnswered: number;
  studyMinutes: number;
  masteryGain: number;
}
