import React from 'react';
import {
  LayoutDashboard,
  GraduationCap,
  LineChart,
  RotateCcw,
  User,
  Sparkles,
  ChevronRight,
  Flame,
  X,
  Compass,
} from 'lucide-react';

export type NavTab = 'dashboard' | 'learn' | 'progress' | 'revision' | 'profile';

interface SidebarProps {
  activeTab: NavTab;
  onSelectTab: (tab: NavTab) => void;
  isOpenMobile: boolean;
  onCloseMobile: () => void;
  streakDays?: number;
  onNavigateToLanding?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  onSelectTab,
  isOpenMobile,
  onCloseMobile,
  streakDays = 7,
  onNavigateToLanding,
}) => {
  const navItems: { id: NavTab; label: string; icon: React.ReactNode; badge?: string }[] = [
    { id: 'dashboard', label: 'Dashboard', icon: <LayoutDashboard className="w-5 h-5" /> },
    { id: 'learn', label: 'Learn', icon: <GraduationCap className="w-5 h-5" />, badge: 'Adaptive' },
    { id: 'progress', label: 'My Progress', icon: <LineChart className="w-5 h-5" /> },
    { id: 'revision', label: 'Revision', icon: <RotateCcw className="w-5 h-5" />, badge: '3 Due' },
    { id: 'profile', label: 'Profile', icon: <User className="w-5 h-5" /> },
  ];

  return (
    <>
      {/* Mobile Backdrop */}
      {isOpenMobile && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 lg:hidden"
          onClick={onCloseMobile}
          data-testid="mobile-backdrop"
        />
      )}

      {/* Sidebar Container */}
      <aside
        className={`fixed top-0 bottom-0 left-0 z-50 w-64 bg-background-card border-r border-slate-800/80 flex flex-col transition-transform duration-300 ease-in-out lg:translate-x-0 ${
          isOpenMobile ? 'translate-x-0' : '-translate-x-full'
        }`}
        data-testid="sidebar-container"
      >
        {/* Brand Header */}
        <div className="h-16 flex items-center justify-between px-6 border-b border-slate-800/80">
          <div
            className="flex items-center gap-3 cursor-pointer group"
            onClick={onNavigateToLanding}
            title="Return to Public Introduction Page"
          >
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-electric-600 to-cyan-400 flex items-center justify-center shadow-glow-cyan group-hover:scale-105 transition-transform">
              <Compass className="w-5 h-5 text-white" />
            </div>
            <div>
              <span className="font-extrabold text-base tracking-tight gradient-text-blue-cyan">
                AdeptLearn
              </span>
              <span className="block text-[10px] uppercase font-semibold text-slate-400 tracking-wider">
                Exam-Prep AI
              </span>
            </div>
          </div>

          <button
            onClick={onCloseMobile}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 lg:hidden"
            aria-label="Close sidebar"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation Items */}
        <nav className="flex-1 px-4 py-6 space-y-1.5 overflow-y-auto">
          {navItems.map((item) => {
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => {
                  onSelectTab(item.id);
                  onCloseMobile();
                }}
                className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all group ${
                  isActive
                    ? 'bg-gradient-to-r from-electric-600/25 to-cyan-500/10 text-cyan-300 border border-cyan-500/30 shadow-glow-blue/20'
                    : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/50'
                }`}
                data-testid={`nav-item-${item.id}`}
              >
                <div className="flex items-center gap-3">
                  <span className={`${isActive ? 'text-cyan-400' : 'text-slate-400 group-hover:text-slate-200'}`}>
                    {item.icon}
                  </span>
                  <span>{item.label}</span>
                </div>

                <div className="flex items-center gap-1.5">
                  {item.badge && (
                    <span
                      className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                        isActive
                          ? 'bg-cyan-500/20 text-cyan-300'
                          : 'bg-slate-800 text-slate-400 group-hover:text-slate-300'
                      }`}
                    >
                      {item.badge}
                    </span>
                  )}
                  {isActive && <ChevronRight className="w-4 h-4 text-cyan-400" />}
                </div>
              </button>
            );
          })}

          {/* Quick Return to Public Showcase */}
          {onNavigateToLanding && (
            <div className="pt-4 mt-4 border-t border-slate-800/60">
              <button
                onClick={onNavigateToLanding}
                className="w-full flex items-center gap-3 px-3.5 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-cyan-300 hover:bg-slate-800/50 transition-colors"
                title="View Cinematic Introduction Page"
              >
                <Compass className="w-4 h-4 text-cyan-400" />
                <span>Showcase Intro Page</span>
              </button>
            </div>
          )}
        </nav>

        {/* Bottom Study Streak Card */}
        <div className="p-4 border-t border-slate-800/80">
          <div className="p-3.5 rounded-xl bg-slate-900/90 border border-amber-500/20 flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400">
              <Flame className="w-5 h-5 fill-amber-400 animate-pulse-subtle" />
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="font-bold text-sm text-slate-200">{streakDays} Days</span>
                <span className="text-[10px] uppercase font-bold text-amber-400">Streak!</span>
              </div>
              <p className="text-[11px] text-slate-400">Practice today to keep it active</p>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
};
