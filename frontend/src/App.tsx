import React, { useState, useEffect } from 'react';
import {
  StudentProfile,
  Subject,
  ConceptMastery,
  LearningRecommendation,
  RevisionItem,
  ConceptGraphData,
  ActivitySummary,
} from './types';
import { learningService } from './services/learningService';
import { progressService, OverallMasteryOverview, SubjectProgressSummary } from './services/progressService';
import { profileService } from './services/profileService';
import { Sidebar, NavTab } from './components/common/Sidebar';
import { Header } from './components/common/Header';
import { DashboardPage } from './pages/DashboardPage';
import { LearningPage } from './pages/LearningPage';
import { ProgressPage } from './pages/ProgressPage';
import { RevisionPage } from './pages/RevisionPage';
import { ProfilePage } from './pages/ProfilePage';
import { LandingPage } from './pages/LandingPage';

export type AppRoute = 'landing' | 'app';

export const App: React.FC = () => {
  // Route state: defaults to 'landing' for public visitors at '/'
  const [currentRoute, setCurrentRoute] = useState<AppRoute>(() => {
    if (typeof window !== 'undefined') {
      const path = window.location.pathname;
      const hash = window.location.hash;
      if (path === '/app' || path.startsWith('/dashboard') || hash === '#app') {
        return 'app';
      }
    }
    return 'landing';
  });

  const [activeTab, setActiveTab] = useState<NavTab>('dashboard');
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState<boolean>(false);
  const [selectedSubjectId, setSelectedSubjectId] = useState<number>(1);
  const [targetConceptId, setTargetConceptId] = useState<number | undefined>(undefined);

  // Application Data States
  const [profile, setProfile] = useState<StudentProfile | null>(null);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [overview, setOverview] = useState<OverallMasteryOverview | null>(null);
  const [subjectSummaries, setSubjectSummaries] = useState<SubjectProgressSummary[]>([]);
  const [allMasteries, setAllMasteries] = useState<ConceptMastery[]>([]);
  const [weakConcepts, setWeakConcepts] = useState<ConceptMastery[]>([]);
  const [strongConcepts, setStrongConcepts] = useState<ConceptMastery[]>([]);
  const [recommendations, setRecommendations] = useState<LearningRecommendation[]>([]);
  const [revisions, setRevisions] = useState<RevisionItem[]>([]);
  const [graphData, setGraphData] = useState<ConceptGraphData | null>(null);
  const [activityHistory, setActivityHistory] = useState<ActivitySummary[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Initial Data Load
  const refreshData = async () => {
    try {
      const [
        p,
        subs,
        ov,
        summs,
        allM,
        weakM,
        strongM,
        recs,
        revs,
        gData,
        acts,
      ] = await Promise.all([
        profileService.getStudentProfile(),
        learningService.getSubjects(),
        progressService.getOverallOverview(),
        progressService.getSubjectProgress(),
        progressService.getAllConceptMasteries(),
        progressService.getWeakConcepts(),
        progressService.getStrongConcepts(),
        progressService.getLearningRecommendations(),
        profileService.getRevisionQueue(),
        progressService.getConceptGraph(),
        progressService.getActivityTrend(),
      ]);

      setProfile(p);
      setSubjects(subs);
      setOverview(ov);
      setSubjectSummaries(summs);
      setAllMasteries(allM);
      setWeakConcepts(weakM);
      setStrongConcepts(strongM);
      setRecommendations(recs);
      setRevisions(revs);
      setGraphData(gData);
      setActivityHistory(acts);
    } catch (err) {
      console.error('Failed to load initial application state:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    refreshData();
  }, []);

  // Listen to browser history popstate
  useEffect(() => {
    const handlePopState = () => {
      const hash = window.location.hash;
      const path = window.location.pathname;
      if (path === '/app' || hash === '#app') {
        setCurrentRoute('app');
      } else if (path === '/' && !hash) {
        setCurrentRoute('landing');
      }
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  const handleNavigateToApp = () => {
    setCurrentRoute('app');
    if (typeof window !== 'undefined' && window.history) {
      window.history.pushState(null, '', '#app');
    }
  };

  const handleNavigateToLanding = () => {
    setCurrentRoute('landing');
    if (typeof window !== 'undefined' && window.history) {
      window.history.pushState(null, '', '/');
    }
  };

  const handleStartLearning = (conceptId?: number) => {
    setTargetConceptId(conceptId);
    setActiveTab('learn');
    if (currentRoute !== 'app') {
      handleNavigateToApp();
    }
  };

  const handleSelectSubject = (subjectId: number) => {
    setSelectedSubjectId(subjectId);
    progressService.getConceptGraph(subjectId).then(setGraphData);
  };

  const handleReviewRevision = async (id: string, rating: 'hard' | 'good' | 'easy') => {
    await profileService.markRevisionReviewed(id, rating);
    const updated = await profileService.getRevisionQueue();
    setRevisions(updated);
  };

  const handleUpdatePreferences = async (prefs: Partial<StudentProfile['preferences']>) => {
    const updated = await profileService.updatePreferences(prefs);
    setProfile(updated);
  };

  // If visitor is on the public landing route, render LandingPage
  if (currentRoute === 'landing') {
    return (
      <LandingPage onEnterApp={handleNavigateToApp} />
    );
  }

  // App loading state
  if (isLoading || !profile || !overview || !graphData) {
    return (
      <div className="min-h-screen bg-background flex flex-col items-center justify-center text-slate-300">
        <div className="w-10 h-10 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin mb-4 shadow-glow-cyan" />
        <p className="text-sm font-semibold tracking-wide">Starting AdeptLearn Adaptive Tutor...</p>
      </div>
    );
  }

  const selectedSubject = subjects.find((s) => s.id === selectedSubjectId) || subjects[0];

  return (
    <div className="min-h-screen bg-background text-slate-100 flex">
      {/* Sidebar Navigation */}
      <Sidebar
        activeTab={activeTab}
        onSelectTab={(tab) => {
          setActiveTab(tab);
          if (tab !== 'learn') setTargetConceptId(undefined);
        }}
        isOpenMobile={isMobileSidebarOpen}
        onCloseMobile={() => setIsMobileSidebarOpen(false)}
        streakDays={profile.studyStreakDays}
        onNavigateToLanding={handleNavigateToLanding}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 lg:pl-64">
        {/* Header Bar */}
        <Header
          profile={profile}
          subjects={subjects}
          selectedSubjectId={selectedSubjectId}
          onSelectSubject={handleSelectSubject}
          onOpenMobileSidebar={() => setIsMobileSidebarOpen(true)}
          onNavigateToProfile={() => setActiveTab('profile')}
          onNavigateToLearn={() => setActiveTab('learn')}
          allMasteries={allMasteries}
          onStartLearning={handleStartLearning}
          onNavigateToRevision={() => setActiveTab('revision')}
        />

        {/* Page Content Container */}
        <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto">
          {activeTab === 'dashboard' && (
            <DashboardPage
              profile={profile}
              overview={overview}
              subjects={subjects}
              subjectSummaries={subjectSummaries}
              weakConcepts={weakConcepts}
              recommendations={recommendations}
              revisions={revisions}
              onStartLearning={handleStartLearning}
              onSelectSubject={handleSelectSubject}
              onNavigateToRevision={() => setActiveTab('revision')}
            />
          )}

          {activeTab === 'learn' && (
            <LearningPage
              currentSubject={selectedSubject}
              initialConceptId={targetConceptId}
              onNavigateHome={() => setActiveTab('dashboard')}
              onMasteryUpdated={refreshData}
            />
          )}

          {activeTab === 'progress' && (
            <ProgressPage
              overview={overview}
              subjectSummaries={subjectSummaries}
              allMasteries={allMasteries}
              strongConcepts={strongConcepts}
              weakConcepts={weakConcepts}
              graphData={graphData}
              activityHistory={activityHistory}
              onStartLearning={handleStartLearning}
              onSelectSubject={handleSelectSubject}
            />
          )}

          {activeTab === 'revision' && (
            <RevisionPage
              revisions={revisions}
              onReviewItem={handleReviewRevision}
              onPracticeConcept={handleStartLearning}
            />
          )}

          {activeTab === 'profile' && (
            <ProfilePage
              profile={profile}
              onUpdatePreferences={handleUpdatePreferences}
            />
          )}
        </main>
      </div>
    </div>
  );
};

export default App;
