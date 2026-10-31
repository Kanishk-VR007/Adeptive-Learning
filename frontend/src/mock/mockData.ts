import {
  StudentProfile,
  Subject,
  Chapter,
  Concept,
  ConceptMastery,
  Question,
  LearningRecommendation,
  RevisionItem,
  ConceptGraphData,
  ActivitySummary
} from '../types';

export const mockStudentProfile: StudentProfile = {
  id: 1,
  email: 'alex.chen@university.edu',
  fullName: 'Alex Chen',
  avatarUrl: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80',
  role: 'student',
  studyStreakDays: 7,
  lastActiveDate: '2026-10-31',
  targetExam: 'AP Calculus BC & STEM Entrance',
  targetExamDate: '2027-05-12',
  weeklyGoalHours: 12,
  currentWeeklyHours: 8.5,
  preferences: {
    reducedMotion: false,
    soundEffects: true,
    dailyReminderTime: '19:00',
  },
};

export const mockSubjects: Subject[] = [
  {
    id: 1,
    code: 'MATH101',
    name: 'Calculus I & Real Analysis',
    description: 'Fundamental limits, differential calculus, continuity, and real-world optimization.',
    totalChapters: 4,
    totalConcepts: 16,
    iconName: 'Sigma',
    colorScheme: 'electric',
  },
  {
    id: 2,
    code: 'MATH201',
    name: 'Linear Algebra & Vectors',
    description: 'Vector spaces, matrix transformations, eigenvalues, and basis orthogonalization.',
    totalChapters: 3,
    totalConcepts: 12,
    iconName: 'Grid',
    colorScheme: 'cyan',
  },
  {
    id: 3,
    code: 'CS102',
    name: 'Data Structures & Algorithms',
    description: 'Trees, graph traversals, dynamic programming, and complexity bounds.',
    totalChapters: 5,
    totalConcepts: 20,
    iconName: 'Binary',
    colorScheme: 'purple',
  },
];

export const mockChapters: Chapter[] = [
  {
    id: 1,
    subjectId: 1,
    chapterNumber: 1,
    title: 'Limits & Continuity',
    description: 'Intuitive limit foundations, delta-epsilon concepts, and asymptotic behavior.',
    conceptCount: 4,
  },
  {
    id: 2,
    subjectId: 1,
    chapterNumber: 2,
    title: 'Derivatives & Tangents',
    description: 'Rates of change, differentiation rules, and geometric meaning.',
    conceptCount: 5,
  },
  {
    id: 3,
    subjectId: 1,
    chapterNumber: 3,
    title: 'Applications of Derivatives',
    description: 'Optimization, curve sketching, related rates, and Mean Value Theorem.',
    conceptCount: 4,
  },
];

export const mockConcepts: Concept[] = [
  {
    id: 1,
    conceptCode: 'CALC_LIMIT_01',
    subjectId: 1,
    chapterId: 1,
    name: 'Intuitive Definition of Limits',
    description: 'Understanding how functions behave near a point without necessarily being defined there.',
    difficultyLevel: 'beginner',
    learningObjectives: [
      'Understand the difference between f(a) and the limit as x approaches a',
      'Read and interpret two-sided limits from graphs',
      'Evaluate direct algebraic substitutions'
    ],
    prerequisiteIds: [],
    dependentIds: [2],
  },
  {
    id: 2,
    conceptCode: 'CALC_LIMIT_02',
    subjectId: 1,
    chapterId: 1,
    name: 'One-Sided Limits & Continuity',
    description: 'Analyzing left-hand and right-hand limits and the 3 conditions for formal continuity.',
    difficultyLevel: 'intermediate',
    learningObjectives: [
      'Evaluate left-hand lim x->a- and right-hand lim x->a+',
      'Verify the three conditions for continuity at a point',
      'Identify jump, removable, and infinite discontinuities'
    ],
    prerequisiteIds: [1],
    dependentIds: [3, 4],
  },
  {
    id: 3,
    conceptCode: 'CALC_LIMIT_03',
    subjectId: 1,
    chapterId: 1,
    name: 'The Squeeze Theorem & Special Limits',
    description: 'Bounding oscillating functions and computing critical trigonometric limits.',
    difficultyLevel: 'intermediate',
    learningObjectives: [
      'Apply the Squeeze (Sandwich) Theorem between bounding curves',
      'Evaluate lim(x->0) sin(x)/x = 1',
      'Handle zero-over-zero indeterminates algebraically'
    ],
    prerequisiteIds: [2],
    dependentIds: [4],
  },
  {
    id: 4,
    conceptCode: 'CALC_DERIV_01',
    subjectId: 1,
    chapterId: 2,
    name: 'Definition of the Derivative',
    description: 'Instantaneous rate of change formulated as the limit of difference quotients.',
    difficultyLevel: 'intermediate',
    learningObjectives: [
      'Formulate f\'(x) = lim h->0 (f(x+h) - f(x))/h',
      'Relate the secant line slope to tangent line slope',
      'Identify points of non-differentiability (cusps, corners, vertical tangents)'
    ],
    prerequisiteIds: [2, 3],
    dependentIds: [5, 6],
  },
  {
    id: 5,
    conceptCode: 'CALC_DERIV_02',
    subjectId: 1,
    chapterId: 2,
    name: 'Product & Quotient Rules',
    description: 'Systematic differentiation algorithms for compound polynomial and rational terms.',
    difficultyLevel: 'intermediate',
    learningObjectives: [
      'Apply (uv)\' = u\'v + uv\' correctly',
      'Apply the quotient rule (u/v)\' = (u\'v - uv\') / v^2 without sign errors',
      'Differentiate rational functions with multiple terms'
    ],
    prerequisiteIds: [4],
    dependentIds: [6],
  },
  {
    id: 6,
    conceptCode: 'CALC_DERIV_03',
    subjectId: 1,
    chapterId: 2,
    name: 'The Chain Rule for Composite Functions',
    description: 'Differentiating nested functions: d/dx [f(g(x))] = f\'(g(x)) * g\'(x).',
    difficultyLevel: 'advanced',
    learningObjectives: [
      'Decompose composite functions into outer and inner components',
      'Apply the chain rule repeatedly to multiple nested layers',
      'Combine the chain rule with product and quotient rules'
    ],
    prerequisiteIds: [4, 5],
    dependentIds: [],
  },
];

export const mockMasteryRecords: ConceptMastery[] = [
  {
    id: 1,
    studentId: 1,
    conceptId: 1,
    conceptCode: 'CALC_LIMIT_01',
    conceptName: 'Intuitive Definition of Limits',
    chapterId: 1,
    subjectId: 1,
    initialMastery: 0.25,
    currentMastery: 0.94,
    masteryClassification: 'Mastered',
    totalAttempts: 18,
    correctAttempts: 17,
    incorrectAttempts: 1,
    lastAttemptAt: '2026-10-30T14:20:00Z',
    history: [
      { timestamp: '2026-10-25', isCorrect: true, previousMastery: 0.25, updatedMastery: 0.52 },
      { timestamp: '2026-10-28', isCorrect: true, previousMastery: 0.52, updatedMastery: 0.81 },
      { timestamp: '2026-10-30', isCorrect: true, previousMastery: 0.81, updatedMastery: 0.94 },
    ],
  },
  {
    id: 2,
    studentId: 1,
    conceptId: 2,
    conceptCode: 'CALC_LIMIT_02',
    conceptName: 'One-Sided Limits & Continuity',
    chapterId: 1,
    subjectId: 1,
    initialMastery: 0.20,
    currentMastery: 0.78,
    masteryClassification: 'Good Understanding',
    totalAttempts: 14,
    correctAttempts: 11,
    incorrectAttempts: 3,
    lastAttemptAt: '2026-10-31T09:15:00Z',
    history: [
      { timestamp: '2026-10-29', isCorrect: false, previousMastery: 0.40, updatedMastery: 0.35 },
      { timestamp: '2026-10-31', isCorrect: true, previousMastery: 0.35, updatedMastery: 0.78 },
    ],
  },
  {
    id: 3,
    studentId: 1,
    conceptId: 3,
    conceptCode: 'CALC_LIMIT_03',
    conceptName: 'The Squeeze Theorem & Special Limits',
    chapterId: 1,
    subjectId: 1,
    initialMastery: 0.20,
    currentMastery: 0.34,
    masteryClassification: 'Weak Understanding',
    totalAttempts: 9,
    correctAttempts: 3,
    incorrectAttempts: 6,
    lastAttemptAt: '2026-10-31T11:45:00Z',
    history: [
      { timestamp: '2026-10-31', isCorrect: false, previousMastery: 0.42, updatedMastery: 0.34 },
    ],
  },
  {
    id: 4,
    studentId: 1,
    conceptId: 4,
    conceptCode: 'CALC_DERIV_01',
    conceptName: 'Definition of the Derivative',
    chapterId: 2,
    subjectId: 1,
    initialMastery: 0.20,
    currentMastery: 0.72,
    masteryClassification: 'Good Understanding',
    totalAttempts: 12,
    correctAttempts: 9,
    incorrectAttempts: 3,
    lastAttemptAt: '2026-10-31T10:00:00Z',
    history: [
      { timestamp: '2026-10-30', isCorrect: true, previousMastery: 0.58, updatedMastery: 0.72 },
    ],
  },
  {
    id: 5,
    studentId: 1,
    conceptId: 5,
    conceptCode: 'CALC_DERIV_02',
    conceptName: 'Product & Quotient Rules',
    chapterId: 2,
    subjectId: 1,
    initialMastery: 0.20,
    currentMastery: 0.61,
    masteryClassification: 'Developing Understanding',
    totalAttempts: 15,
    correctAttempts: 9,
    incorrectAttempts: 6,
    lastAttemptAt: '2026-10-30T17:30:00Z',
    history: [
      { timestamp: '2026-10-30', isCorrect: true, previousMastery: 0.48, updatedMastery: 0.61 },
    ],
  },
  {
    id: 6,
    studentId: 1,
    conceptId: 6,
    conceptCode: 'CALC_DERIV_03',
    conceptName: 'The Chain Rule for Composite Functions',
    chapterId: 2,
    subjectId: 1,
    initialMastery: 0.20,
    currentMastery: 0.29,
    masteryClassification: 'Weak Understanding',
    totalAttempts: 8,
    correctAttempts: 2,
    incorrectAttempts: 6,
    lastAttemptAt: '2026-10-31T08:00:00Z',
    history: [
      { timestamp: '2026-10-31', isCorrect: false, previousMastery: 0.38, updatedMastery: 0.29 },
    ],
  },
];

export const mockQuestions: Question[] = [
  {
    id: 101,
    conceptId: 6,
    conceptName: 'The Chain Rule for Composite Functions',
    chapterTitle: 'Derivatives & Tangents',
    subjectName: 'Calculus I & Real Analysis',
    questionType: 'mcq',
    difficultyLevel: 'intermediate',
    questionText: 'Given the composite function f(x) = (3x² - 5x + 4)⁴, which expression represents the first derivative f\'(x)?',
    codeSnippet: 'f(x) = (3x^2 - 5x + 4)^4',
    options: [
      {
        id: 'A',
        text: "f'(x) = 4(3x² - 5x + 4)³",
        explanation: 'Incorrect. This only differentiates the outer exponent 4, omitting the inner derivative g\'(x).'
      },
      {
        id: 'B',
        text: "f'(x) = 4(3x² - 5x + 4)³ · (6x - 5)",
        explanation: 'Correct! By the chain rule: d/dx [u^4] = 4u^3 · (du/dx), where u = 3x² - 5x + 4 and u\' = 6x - 5.'
      },
      {
        id: 'C',
        text: "f'(x) = 4(6x - 5)³",
        explanation: 'Incorrect. The inner function u(x) was replaced prematurely instead of keeping u intact in the outer derivative.'
      },
      {
        id: 'D',
        text: "f'(x) = 12(3x² - 5x + 4)³ · (6x - 5)",
        explanation: 'Incorrect. Multiplied extra scalar factor of 3 unnecessarily into the outer derivative.'
      }
    ],
    correctAnswer: 'B',
    hints: [
      'Identify the outer function: Let u = (3x² - 5x + 4). Then f(u) = u⁴.',
      'Differentiate the outer layer: d/du [u⁴] = 4u³.',
      'Multiply by the derivative of the inner function: What is d/dx [3x² - 5x + 4]?'
    ],
    evaluationRubric: {
      keyConcepts: ['Chain rule formula d/dx [f(g(x))] = f\'(g(x)) * g\'(x)', 'Power rule applied to inner polynomial'],
      partialCreditCriteria: 'Student recognized power rule 4u^3 but missed inner factor 6x-5.',
      explanation: 'Always maintain the untouched inner kernel when differentiating outer power, then chain multiply by du/dx.'
    }
  },
  {
    id: 102,
    conceptId: 6,
    conceptName: 'The Chain Rule for Composite Functions',
    chapterTitle: 'Derivatives & Tangents',
    subjectName: 'Calculus I & Real Analysis',
    questionType: 'mcq',
    difficultyLevel: 'advanced',
    questionText: 'Find the derivative of y = sin(cos(2x)). Be sure to evaluate all nested trigonometric and linear layers.',
    codeSnippet: 'y = sin(cos(2x))',
    options: [
      {
        id: 'A',
        text: "dy/dx = 2 · cos(cos(2x)) · sin(2x)",
        explanation: 'Incorrect sign: derivative of cos(u) is -sin(u), so a negative factor is required.'
      },
      {
        id: 'B',
        text: "dy/dx = -2 · cos(cos(2x)) · sin(2x)",
        explanation: 'Correct! Outer: cos(cos(2x)), middle: -sin(2x), inner: 2. Combining gives -2 cos(cos(2x)) sin(2x).'
      },
      {
        id: 'C',
        text: "dy/dx = -cos(cos(2x)) · sin(2x)",
        explanation: 'Incorrect. Forgot to chain differentiate the innermost argument 2x (missing factor of 2).'
      },
      {
        id: 'D',
        text: "dy/dx = cos(-sin(2))",
        explanation: 'Incorrect. Conflated function composition with scalar multiplication.'
      }
    ],
    correctAnswer: 'B',
    hints: [
      'This is a three-layer composite: Outer = sin(u), Middle = cos(v), Inner = 2x.',
      'Take the derivative layer by layer: d/dx = cos(cos(2x)) · d/dx[cos(2x)].',
      'Remember d/dx[cos(2x)] = -sin(2x) · 2.'
    ],
    evaluationRubric: {
      keyConcepts: ['Nested chain rule across 3 functions', 'Trigonometric derivative signs', 'Linear argument factor'],
      partialCreditCriteria: 'Correct trig derivatives but forgot factor 2 from 2x or lost negative sign.',
      explanation: 'Three layers: [sin(...)]\' * [cos(...)]\' * [2x]\'.'
    }
  },
  {
    id: 103,
    conceptId: 3,
    conceptName: 'The Squeeze Theorem & Special Limits',
    chapterTitle: 'Limits & Continuity',
    subjectName: 'Calculus I & Real Analysis',
    questionType: 'mcq',
    difficultyLevel: 'intermediate',
    questionText: 'Evaluate the limit as x approaches 0: lim (x -> 0) [x² · cos(1/x)].',
    codeSnippet: 'lim_{x -> 0} x^2 * cos(1/x)',
    options: [
      {
        id: 'A',
        text: "0",
        explanation: 'Correct! Since -1 <= cos(1/x) <= 1, multiplying by x² >= 0 yields -x² <= x²cos(1/x) <= x². Since lim(-x²) = lim(x²) = 0, the limit is 0 by the Squeeze Theorem.'
      },
      {
        id: 'B',
        text: "Does Not Exist (oscillates wildly)",
        explanation: 'Incorrect. While cos(1/x) oscillates, the factor x² squeezes the amplitude down to zero as x -> 0.'
      },
      {
        id: 'C',
        text: "1",
        explanation: 'Incorrect. Conflated with the known limit lim(x->0) sin(x)/x = 1.'
      },
      {
        id: 'D',
        text: "Infinity",
        explanation: 'Incorrect. 1/x grows large inside the bounded cosine, but the exterior x² forces the product to 0.'
      }
    ],
    correctAnswer: 'A',
    hints: [
      'Notice that cos(anything) is strictly bounded between -1 and +1.',
      'Multiply the inequality -1 <= cos(1/x) <= 1 by x² (which is >= 0).',
      'What happens to both bounding boundaries as x -> 0?'
    ],
    evaluationRubric: {
      keyConcepts: ['Boundedness of trigonometric functions', 'Squeeze Theorem bounding inequality'],
      partialCreditCriteria: 'Recognized oscillation of 1/x but failed to evaluate dampening by x².',
      explanation: 'When an oscillating function is bounded between [-M, M], multiplying by g(x) -> 0 squeezes the result to 0.'
    }
  },
  {
    id: 104,
    conceptId: 2,
    conceptName: 'One-Sided Limits & Continuity',
    chapterTitle: 'Limits & Continuity',
    subjectName: 'Calculus I & Real Analysis',
    questionType: 'text',
    difficultyLevel: 'intermediate',
    questionText: 'Consider the piecewise function f(x) = { cx + 2 for x < 3, and x² - 1 for x >= 3 }. What value must constant c take so that f(x) is continuous at x = 3?',
    codeSnippet: 'f(x) = {\n  cx + 2,  for x < 3\n  x^2 - 1, for x >= 3\n}',
    correctAnswer: '2',
    hints: [
      'For f(x) to be continuous at x = 3, the left-hand limit must equal the right-hand limit.',
      'Compute the right-hand limit and f(3): 3² - 1 = 8.',
      'Set the left-hand expression equal to 8: c(3) + 2 = 8, then solve for c.'
    ],
    evaluationRubric: {
      keyConcepts: ['Definition of continuity: lim x->3- = lim x->3+ = f(3)', 'Solving linear algebraic constraint'],
      partialCreditCriteria: 'Evaluated right limit as 8 but made algebraic error solving 3c + 2 = 8.',
      explanation: '3c + 2 = 8 => 3c = 6 => c = 2.'
    }
  }
];

export const mockRecommendations: LearningRecommendation[] = [
  {
    id: 'rec-1',
    conceptId: 6,
    conceptName: 'The Chain Rule for Composite Functions',
    subjectName: 'Calculus I & Real Analysis',
    chapterTitle: 'Derivatives & Tangents',
    reason: 'weak_concept',
    urgency: 'high',
    estimatedMinutes: 12,
    currentMastery: 0.29,
  },
  {
    id: 'rec-2',
    conceptId: 3,
    conceptName: 'The Squeeze Theorem & Special Limits',
    subjectName: 'Calculus I & Real Analysis',
    chapterTitle: 'Limits & Continuity',
    reason: 'prerequisite_gap',
    urgency: 'high',
    estimatedMinutes: 10,
    currentMastery: 0.34,
  },
  {
    id: 'rec-3',
    conceptId: 5,
    conceptName: 'Product & Quotient Rules',
    subjectName: 'Calculus I & Real Analysis',
    chapterTitle: 'Derivatives & Tangents',
    reason: 'spaced_repetition',
    urgency: 'medium',
    estimatedMinutes: 8,
    currentMastery: 0.61,
  },
];

export const mockRevisionItems: RevisionItem[] = [
  {
    id: 'rev-1',
    conceptId: 3,
    conceptName: 'The Squeeze Theorem & Special Limits',
    subjectName: 'Calculus I',
    lastPracticed: '5 hours ago',
    dueStatus: 'due_today',
    retentionEstimate: 42,
    intervalDays: 1,
  },
  {
    id: 'rev-2',
    conceptId: 6,
    conceptName: 'The Chain Rule for Composite Functions',
    subjectName: 'Calculus I',
    lastPracticed: '10 hours ago',
    dueStatus: 'due_today',
    retentionEstimate: 35,
    intervalDays: 1,
  },
  {
    id: 'rev-3',
    conceptId: 2,
    conceptName: 'One-Sided Limits & Continuity',
    subjectName: 'Calculus I',
    lastPracticed: '2 days ago',
    dueStatus: 'due_soon',
    retentionEstimate: 76,
    intervalDays: 3,
  },
  {
    id: 'rev-4',
    conceptId: 1,
    conceptName: 'Intuitive Definition of Limits',
    subjectName: 'Calculus I',
    lastPracticed: '4 days ago',
    dueStatus: 'scheduled',
    retentionEstimate: 92,
    intervalDays: 7,
  },
];

export const mockConceptGraph: ConceptGraphData = {
  subjectId: 1,
  nodes: [
    {
      id: 1,
      conceptCode: 'CALC_LIMIT_01',
      name: 'Intuitive Limits',
      difficultyLevel: 'beginner',
      subjectId: 1,
      chapterId: 1,
      masteryProbability: 0.94,
      status: 'mastered',
      tierLevel: 0,
    },
    {
      id: 2,
      conceptCode: 'CALC_LIMIT_02',
      name: 'One-Sided & Continuity',
      difficultyLevel: 'intermediate',
      subjectId: 1,
      chapterId: 1,
      masteryProbability: 0.78,
      status: 'ready',
      tierLevel: 1,
    },
    {
      id: 3,
      conceptCode: 'CALC_LIMIT_03',
      name: 'Squeeze Theorem',
      difficultyLevel: 'intermediate',
      subjectId: 1,
      chapterId: 1,
      masteryProbability: 0.34,
      status: 'in_progress',
      tierLevel: 1,
    },
    {
      id: 4,
      conceptCode: 'CALC_DERIV_01',
      name: 'Derivative Definition',
      difficultyLevel: 'intermediate',
      subjectId: 1,
      chapterId: 2,
      masteryProbability: 0.72,
      status: 'ready',
      tierLevel: 2,
    },
    {
      id: 5,
      conceptCode: 'CALC_DERIV_02',
      name: 'Product & Quotient Rules',
      difficultyLevel: 'intermediate',
      subjectId: 1,
      chapterId: 2,
      masteryProbability: 0.61,
      status: 'ready',
      tierLevel: 2,
    },
    {
      id: 6,
      conceptCode: 'CALC_DERIV_03',
      name: 'The Chain Rule',
      difficultyLevel: 'advanced',
      subjectId: 1,
      chapterId: 2,
      masteryProbability: 0.29,
      status: 'in_progress',
      tierLevel: 3,
    },
  ],
  edges: [
    { fromConceptId: 1, toConceptId: 2, relationshipType: 'strict' },
    { fromConceptId: 2, toConceptId: 3, relationshipType: 'suggested' },
    { fromConceptId: 2, toConceptId: 4, relationshipType: 'strict' },
    { fromConceptId: 3, toConceptId: 4, relationshipType: 'suggested' },
    { fromConceptId: 4, toConceptId: 5, relationshipType: 'strict' },
    { fromConceptId: 4, toConceptId: 6, relationshipType: 'strict' },
    { fromConceptId: 5, toConceptId: 6, relationshipType: 'strict' },
  ],
};

export const mockActivityHistory: ActivitySummary[] = [
  { date: '2026-10-25', day: 'Sat', questionsAnswered: 12, studyMinutes: 35, masteryGain: 0.08 },
  { date: '2026-10-26', day: 'Sun', questionsAnswered: 18, studyMinutes: 50, masteryGain: 0.12 },
  { date: '2026-10-27', day: 'Mon', questionsAnswered: 8,  studyMinutes: 25, masteryGain: 0.05 },
  { date: '2026-10-28', day: 'Tue', questionsAnswered: 24, studyMinutes: 65, masteryGain: 0.15 },
  { date: '2026-10-29', day: 'Wed', questionsAnswered: 15, studyMinutes: 40, masteryGain: 0.09 },
  { date: '2026-10-30', day: 'Thu', questionsAnswered: 28, studyMinutes: 75, masteryGain: 0.18 },
  { date: '2026-10-31', day: 'Fri', questionsAnswered: 16, studyMinutes: 45, masteryGain: 0.10 },
];
