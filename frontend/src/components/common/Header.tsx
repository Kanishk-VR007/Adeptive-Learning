import React, { useState, useEffect } from 'react';
import {
  Bell,
  Menu,
  Flame,
  BookOpen,
  CheckCircle2,
  Clock,
  ChevronDown,
  Activity,
  Server,
} from 'lucide-react';
import { StudentProfile, Subject, ConceptMastery } from '../../types';
import { Omnibar } from '../ui/Omnibar';
import {
  isUsingMock,
  setUseMock,
  checkBackendHealth,
  subscribeConnectionState,
  BackendConnectionState,
} from '../../services/apiClient';

interface HeaderProps {
  profile: StudentProfile;
  subjects: Subject[];
  selectedSubjectId: number;
  onSelectSubject: (id: number) => void;
  onOpenMobileSidebar: () => void;
  onNavigateToProfile: () => void;
  onNavigateToLearn: () => void;
  allMasteries?: ConceptMastery[];
  onStartLearning?: (conceptId: number) => void;
  onNavigateToRevision?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  profile,
  subjects,
  selectedSubjectId,
  onSelectSubject,
  onOpenMobileSidebar,
  onNavigateToProfile,
  onNavigateToLearn,
  allMasteries = [],
  onStartLearning,
  onNavigateToRevision,
}) => {
  const [showNotifications, setShowNotifications] = useState(false);
  const [showSubjectDropdown, setShowSubjectDropdown] = useState(false);
  const [connectionState, setConnectionState] = useState<BackendConnectionState>('checking');
  const [useMockMode, setUseMockMode] = useState<boolean>(isUsingMock());

  useEffect(() => {
    checkBackendHealth();
    const unsubscribe = subscribeConnectionState((state, isMock) => {
      setConnectionState(state);
      setUseMockMode(isMock);
    });
    return unsubscribe;
  }, []);

  const handleToggleMock = () => {
    const nextMock = !useMockMode;
    setUseMock(nextMock);
    setUseMockMode(nextMock);
    if (!nextMock) {
      checkBackendHealth();
    }
  };

  const selectedSubject = subjects.find((s) => s.id === selectedSubjectId) || subjects[0];

  const notifications = [
    {
      id: 1,
      title: 'Revision Due: The Chain Rule',
      time: '15m ago',
      type: 'urgent',
      read: false,
    },
    {
      id: 2,
      title: 'Streak Achievement: 7 Days Unlocked!',
      time: '2h ago',
      type: 'celebration',
      read: false,
    },
    {
      id: 3,
      title: 'BKT Model updated: +14% Calculus Mastery',
      time: 'Yesterday',
      type: 'info',
      read: true,
    },
  ];

  return (
    <header
      className="sticky top-0 z-30 h-16 bg-background/90 backdrop-blur-md border-b border-slate-800/80 px-4 lg:px-8 flex items-center justify-between gap-4"
      data-testid="dashboard-header"
    >
      {/* Left: Mobile hamburger & welcome text */}
      <div className="flex items-center gap-3 shrink-0">
        <button
          onClick={onOpenMobileSidebar}
          className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 lg:hidden"
          aria-label="Open navigation menu"
        >
          <Menu className="w-5 h-5" />
        </button>

        <div className="hidden sm:block">
          <h1 className="text-base font-semibold text-slate-100 flex items-center gap-2">
            Welcome back, <span className="gradient-text-blue-cyan font-bold">{profile.fullName}</span> 👋
          </h1>
          <p className="text-[11px] text-slate-400">Target: {profile.targetExam}</p>
        </div>
      </div>

      {/* Center Group: Subject Switcher Dropdown & AI Omnibar */}
      <div className="flex items-center gap-3 flex-1 max-w-xl justify-center">
        {/* Subject Switcher Dropdown */}
        <div className="relative shrink-0">
          <button
            onClick={() => setShowSubjectDropdown(!showSubjectDropdown)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-700/60 hover:border-cyan-500/50 text-xs font-medium text-slate-200 transition-all shadow-sm"
            data-testid="subject-selector-button"
          >
            <BookOpen className="w-3.5 h-3.5 text-cyan-400" />
            <span className="truncate max-w-[100px] sm:max-w-[140px]">
              {selectedSubject ? selectedSubject.name : 'Select Subject'}
            </span>
            <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
          </button>

          {showSubjectDropdown && (
            <div className="absolute top-full mt-2 left-0 w-64 bg-slate-900 border border-slate-700 rounded-xl shadow-xl z-50 p-1.5 animate-in fade-in duration-100">
              <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 px-3 py-1.5">
                Target Syllabi
              </div>
              {subjects.map((sub) => (
                <button
                  key={sub.id}
                  onClick={() => {
                    onSelectSubject(sub.id);
                    setShowSubjectDropdown(false);
                  }}
                  className={`w-full text-left px-3 py-2 rounded-lg text-xs flex items-center justify-between transition-colors ${
                    sub.id === selectedSubjectId
                      ? 'bg-blue-600/20 text-cyan-300 font-semibold border border-cyan-500/20'
                      : 'text-slate-300 hover:bg-slate-800'
                  }`}
                >
                  <div>
                    <div className="font-medium">{sub.name}</div>
                    <div className="text-[10px] text-slate-400">{sub.code} • {sub.totalConcepts} Concepts</div>
                  </div>
                  {sub.id === selectedSubjectId && <CheckCircle2 className="w-4 h-4 text-cyan-400" />}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* StudyFetch / Linear style AI Omnibar */}
        {allMasteries.length > 0 && onStartLearning && (
          <Omnibar
            concepts={allMasteries}
            subjects={subjects}
            onStartLearning={onStartLearning}
            onNavigateToRevision={onNavigateToRevision}
          />
        )}
      </div>

      {/* Right: Backend Connection Status, Streak, Notifications, Profile Avatar */}
      <div className="flex items-center gap-2 sm:gap-3 shrink-0">
        {/* Backend Live/Mock Connection Status Toggle Pill */}
        <button
          onClick={handleToggleMock}
          title={
            useMockMode
              ? 'Currently in Standalone Mock Mode. Click to connect to Live FastAPI Backend.'
              : connectionState === 'connected'
              ? 'Connected to Live FastAPI Backend (Port 8000). Click to switch to Mock Mode.'
              : 'Live Backend Offline (FastAPI Port 8000 unreachable). Click to switch to Mock Mode.'
          }
          className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium transition-all border ${
            !useMockMode && connectionState === 'connected'
              ? 'bg-emerald-500/10 border-emerald-500/40 text-emerald-400 hover:bg-emerald-500/20 shadow-glow-sm'
              : useMockMode
              ? 'bg-cyan-500/10 border-cyan-500/30 text-cyan-300 hover:bg-cyan-500/20'
              : 'bg-rose-500/10 border-rose-500/30 text-rose-400 hover:bg-rose-500/20'
          }`}
          data-testid="backend-status-pill"
        >
          <Server className="w-3 h-3" />
          <span className="hidden md:inline">
            {!useMockMode && connectionState === 'connected'
              ? 'Live FastAPI'
              : useMockMode
              ? 'Mock Mode'
              : 'Backend Offline'}
          </span>
          <span
            className={`w-1.5 h-1.5 rounded-full ${
              !useMockMode && connectionState === 'connected'
                ? 'bg-emerald-400 animate-pulse'
                : useMockMode
                ? 'bg-cyan-400'
                : 'bg-rose-400'
            }`}
          />
        </button>

        {/* Streak Pill */}
        <div
          className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-400 text-xs font-semibold cursor-pointer hover:bg-amber-500/20 transition-colors"
          title={`${profile.studyStreakDays} Day Streak!`}
        >
          <Flame className="w-4 h-4 fill-amber-400" />
          <span>{profile.studyStreakDays}</span>
        </div>

        {/* Notification Bell */}
        <div className="relative">
          <button
            onClick={() => setShowNotifications(!showNotifications)}
            className="p-2 rounded-xl text-slate-400 hover:text-slate-100 hover:bg-slate-800/80 transition-colors relative"
            aria-label="View notifications"
            data-testid="notification-button"
          >
            <Bell className="w-5 h-5" />
            <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-cyan-400 shadow-glow-cyan" />
          </button>

          {showNotifications && (
            <div className="absolute right-0 top-full mt-2 w-80 bg-slate-900 border border-slate-700/80 rounded-2xl shadow-2xl z-50 p-3">
              <div className="flex items-center justify-between border-b border-slate-800 pb-2 mb-2 px-1">
                <span className="text-xs font-bold text-slate-200 uppercase tracking-wider">
                  Notifications
                </span>
                <span className="text-[10px] text-cyan-400 font-medium cursor-pointer hover:underline">
                  Mark all as read
                </span>
              </div>
              <div className="space-y-2">
                {notifications.map((n) => (
                  <div
                    key={n.id}
                    className="p-2.5 rounded-xl bg-slate-900/60 border border-slate-800 hover:border-slate-700 transition-colors cursor-pointer"
                    onClick={() => {
                      setShowNotifications(false);
                      if (n.type === 'urgent') onNavigateToLearn();
                    }}
                  >
                    <div className="flex items-center justify-between text-xs font-semibold text-slate-200">
                      <span className="truncate">{n.title}</span>
                      <span className="text-[10px] text-slate-400 flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {n.time}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Profile Avatar */}
        <button
          onClick={onNavigateToProfile}
          className="flex items-center gap-2 pl-1 focus:outline-none group"
          data-testid="header-profile-button"
        >
          <div className="w-9 h-9 rounded-full ring-2 ring-cyan-500/30 group-hover:ring-cyan-400 overflow-hidden transition-all shadow-sm">
            <img
              src={profile.avatarUrl}
              alt={profile.fullName}
              className="w-full h-full object-cover"
              onError={(e) => {
                (e.currentTarget as HTMLImageElement).src = 'https://ui-avatars.com/api/?name=Alex+Chen&background=2563EB&color=fff';
              }}
            />
          </div>
        </button>
      </div>
    </header>
  );
};
