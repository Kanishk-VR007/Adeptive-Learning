import React from 'react';
import {
  StudentProfile,
  Subject,
  ConceptMastery,
  LearningRecommendation,
  RevisionItem,
} from '../types';
import { OverallMasteryOverview, SubjectProgressSummary } from '../services/progressService';
import { KnowledgeGalaxy } from '../components/galaxy/KnowledgeGalaxy';
import { LearningOverviewCard } from '../components/dashboard/LearningOverviewCard';
import { ContinueLearningCard } from '../components/dashboard/ContinueLearningCard';
import { WeakConceptsCard } from '../components/dashboard/WeakConceptsCard';
import { TodaysPlanCard } from '../components/dashboard/TodaysPlanCard';
import { SubjectProgressCard } from '../components/progress/SubjectProgressCard';

interface DashboardPageProps {
  profile: StudentProfile;
  overview: OverallMasteryOverview;
  subjects: Subject[];
  subjectSummaries: SubjectProgressSummary[];
  weakConcepts: ConceptMastery[];
  recommendations: LearningRecommendation[];
  revisions: RevisionItem[];
  onStartLearning: (conceptId?: number) => void;
  onSelectSubject: (subjectId: number) => void;
  onNavigateToRevision: () => void;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({
  profile,
  overview,
  subjects,
  subjectSummaries,
  weakConcepts,
  recommendations,
  revisions,
  onStartLearning,
  onSelectSubject,
  onNavigateToRevision,
}) => {
  const topRecommendation = recommendations[0] || {
    conceptId: 6,
    conceptName: 'The Chain Rule for Composite Functions',
    subjectName: 'Calculus I & Real Analysis',
    chapterTitle: 'Derivatives & Tangents',
    urgency: 'high',
    estimatedMinutes: 12,
  };

  return (
    <div className="space-y-6 pb-12" data-testid="dashboard-page">
      {/* Hero Section: Welcome & 3D Knowledge Galaxy Visualization */}
      <section className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
        {/* Left Hero: Interactive Continue Learning Spotlight */}
        <div className="lg:col-span-6 flex flex-col justify-between space-y-4">
          <div className="p-6 rounded-3xl bg-gradient-to-br from-slate-900 via-slate-900/90 to-background border border-slate-800 shadow-card-soft relative overflow-hidden flex flex-col justify-between h-full">
            <div>
              <div className="flex items-center justify-between mb-3">
                <span className="text-[11px] font-bold uppercase tracking-wider text-cyan-400">
                  Active Adaptive Diagnostic
                </span>
                <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-blue-600/20 text-blue-300 border border-blue-500/30">
                  Syllabus Sprint 2026
                </span>
              </div>

              <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-100 tracking-tight leading-tight mb-2">
                Master Complex Syllabi with <span className="gradient-text-blue-cyan">Adaptive AI</span>
              </h2>
              <p className="text-xs sm:text-sm text-slate-300 max-w-xl leading-relaxed mb-6">
                Your Bayesian Knowledge Tracing profile dynamically evaluates comprehension at each step,
                generating targeted remediation and Keplerian concept visualizations.
              </p>
            </div>

            <ContinueLearningCard
              subjectName={topRecommendation.subjectName}
              chapterTitle={topRecommendation.chapterTitle}
              conceptName={topRecommendation.conceptName}
              conceptDifficulty="Advanced"
              onContinue={() => onStartLearning(topRecommendation.conceptId)}
            />
          </div>
        </div>

        {/* Right Hero: Flagship 3D Knowledge Galaxy */}
        <div className="lg:col-span-6 flex flex-col justify-center">
          <KnowledgeGalaxy
            masteries={weakConcepts}
            subjectTitle={topRecommendation.subjectName}
            onSelectConcept={(conceptId) => onStartLearning(conceptId)}
            className="w-full h-full min-h-[360px]"
          />
        </div>
      </section>

      {/* Main Grid: Learning Overview, Weak Concepts & Today's Plan */}
      <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <LearningOverviewCard
          overallMastery={overview.overallMasteryPercentage}
          conceptsCompleted={overview.totalConceptsMastered}
          totalConcepts={overview.totalConceptsLearned}
          questionsAnswered={overview.totalQuestionsAnswered}
          studyMinutes={overview.totalStudyMinutes}
        />

        <WeakConceptsCard
          concepts={weakConcepts}
          onPracticeConcept={(conceptId) => onStartLearning(conceptId)}
        />

        <TodaysPlanCard
          suggestedConcepts={recommendations}
          dailyPracticeTarget={15}
          completedTodayCount={9}
          upcomingRevisions={revisions}
          onSelectConcept={(conceptId) => onStartLearning(conceptId)}
          onOpenRevision={onNavigateToRevision}
        />
      </section>

      {/* Subject Summary Row */}
      <section>
        <div className="flex items-center justify-between mb-3 px-1">
          <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider">
            Syllabus Mastery Breakdown
          </h3>
          <span className="text-xs text-slate-400">Click a subject to inspect syllabus</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {subjectSummaries.map((summary) => (
            <SubjectProgressCard
              key={summary.subjectId}
              summary={summary}
              onSelectSubject={onSelectSubject}
            />
          ))}
        </div>
      </section>
    </div>
  );
};
