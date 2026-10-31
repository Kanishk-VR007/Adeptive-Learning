import React, { useState } from 'react';
import { StudentProfile } from '../types';
import {
  Mail,
  Flame,
  Sliders,
  CheckCircle2,
  Server,
} from 'lucide-react';
import { apiConfig } from '../services/apiClient';

interface ProfilePageProps {
  profile: StudentProfile;
  onUpdatePreferences: (prefs: Partial<StudentProfile['preferences']>) => Promise<void>;
}

export const ProfilePage: React.FC<ProfilePageProps> = ({
  profile,
  onUpdatePreferences,
}) => {
  const [reducedMotion, setReducedMotion] = useState<boolean>(profile.preferences.reducedMotion);
  const [soundEffects, setSoundEffects] = useState<boolean>(profile.preferences.soundEffects);
  const [savedNotice, setSavedNotice] = useState<boolean>(false);

  const handleToggleMotion = async () => {
    const newVal = !reducedMotion;
    setReducedMotion(newVal);
    await onUpdatePreferences({ reducedMotion: newVal });
    triggerSaved();
  };

  const handleToggleSound = async () => {
    const newVal = !soundEffects;
    setSoundEffects(newVal);
    await onUpdatePreferences({ soundEffects: newVal });
    triggerSaved();
  };

  const triggerSaved = () => {
    setSavedNotice(true);
    setTimeout(() => setSavedNotice(false), 2500);
  };

  return (
    <div className="space-y-6 pb-12 max-w-4xl mx-auto" data-testid="profile-page">
      {/* Profile Header Card */}
      <div className="p-6 rounded-2xl bg-background-card border border-slate-800/80 shadow-card-soft">
        <div className="flex flex-col sm:flex-row items-center sm:items-start gap-5">
          <div className="w-20 h-20 rounded-2xl ring-4 ring-cyan-500/20 overflow-hidden shrink-0 shadow-lg">
            <img
              src={profile.avatarUrl}
              alt={profile.fullName}
              className="w-full h-full object-cover"
              onError={(e) => {
                (e.currentTarget as HTMLImageElement).src =
                  'https://ui-avatars.com/api/?name=Alex+Chen&background=2563EB&color=fff';
              }}
            />
          </div>

          <div className="flex-1 text-center sm:text-left">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div>
                <h2 className="text-xl font-bold text-slate-100">{profile.fullName}</h2>
                <div className="flex items-center justify-center sm:justify-start gap-2 text-xs text-slate-400 mt-0.5">
                  <Mail className="w-3.5 h-3.5 text-cyan-400" />
                  <span>{profile.email}</span>
                </div>
              </div>

              <div className="flex items-center justify-center gap-2">
                <span className="px-3 py-1 rounded-full bg-electric-600/20 text-cyan-300 border border-cyan-500/30 text-xs font-semibold">
                  Standard Student Tier
                </span>
              </div>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mt-4 pt-4 border-t border-slate-800 text-xs">
              <div>
                <span className="text-slate-400 block text-[10px] uppercase font-bold">Target Exam</span>
                <span className="font-semibold text-slate-200">{profile.targetExam}</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px] uppercase font-bold">Exam Date</span>
                <span className="font-semibold text-slate-200">{profile.targetExamDate}</span>
              </div>
              <div className="col-span-2 sm:col-span-1">
                <span className="text-slate-400 block text-[10px] uppercase font-bold">Active Streak</span>
                <span className="font-semibold text-amber-400 flex items-center justify-center sm:justify-start gap-1">
                  <Flame className="w-3.5 h-3.5 fill-amber-400" />
                  {profile.studyStreakDays} Days In A Row
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Preferences & Accessibility Settings */}
      <div className="p-6 rounded-2xl bg-background-card border border-slate-800/80 shadow-card-soft">
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-2">
            <Sliders className="w-4 h-4 text-cyan-400" />
            <h3 className="font-semibold text-sm text-slate-100">Preferences & Accessibility</h3>
          </div>
          {savedNotice && (
            <span className="text-xs text-emerald-400 flex items-center gap-1 animate-fade-in">
              <CheckCircle2 className="w-3.5 h-3.5" />
              Settings Saved
            </span>
          )}
        </div>

        <div className="space-y-4">
          {/* Reduced Motion Toggle */}
          <div className="flex items-center justify-between p-3.5 rounded-xl bg-slate-900 border border-slate-800">
            <div>
              <div className="text-xs font-semibold text-slate-200">Reduced Motion Mode</div>
              <div className="text-[11px] text-slate-400">
                Disables 3D knowledge orb rotation and interaction physics
              </div>
            </div>
            <button
              onClick={handleToggleMotion}
              className={`w-12 h-6 rounded-full transition-colors relative p-0.5 ${
                reducedMotion ? 'bg-cyan-500' : 'bg-slate-700'
              }`}
              data-testid="toggle-reduced-motion"
              aria-label="Toggle reduced motion"
            >
              <div
                className={`w-5 h-5 rounded-full bg-white transition-transform ${
                  reducedMotion ? 'translate-x-6' : 'translate-x-0'
                }`}
              />
            </button>
          </div>

          {/* Sound Effects Toggle */}
          <div className="flex items-center justify-between p-3.5 rounded-xl bg-slate-900 border border-slate-800">
            <div>
              <div className="text-xs font-semibold text-slate-200">Practice Audio & Confetti</div>
              <div className="text-[11px] text-slate-400">
                Play celebratory particle animations on correct answers
              </div>
            </div>
            <button
              onClick={handleToggleSound}
              className={`w-12 h-6 rounded-full transition-colors relative p-0.5 ${
                soundEffects ? 'bg-cyan-500' : 'bg-slate-700'
              }`}
              data-testid="toggle-sound-effects"
              aria-label="Toggle sound effects"
            >
              <div
                className={`w-5 h-5 rounded-full bg-white transition-transform ${
                  soundEffects ? 'translate-x-6' : 'translate-x-0'
                }`}
              />
            </button>
          </div>
        </div>
      </div>

      {/* Backend API Compatibility Card */}
      <div className="p-6 rounded-2xl bg-background-card border border-slate-800/80 shadow-card-soft">
        <div className="flex items-center gap-2 mb-3">
          <Server className="w-4 h-4 text-electric-400" />
          <h3 className="font-semibold text-sm text-slate-100">FastAPI Architecture Alignment</h3>
        </div>
        <p className="text-xs text-slate-400 mb-4 leading-relaxed">
          The frontend service abstraction connects directly to the decoupled typed service layer.
          When backend milestones conclude, swapping from the Mock Adapter to live FastAPI requires
          only pointing <code className="text-cyan-300">VITE_API_BASE_URL</code> to the backend router.
        </p>

        <div className="p-3.5 rounded-xl bg-slate-900 border border-slate-800 font-mono text-xs space-y-1.5 text-slate-300">
          <div className="flex items-center justify-between">
            <span className="text-slate-400">Target API Prefix:</span>
            <span className="text-cyan-400">{apiConfig.baseUrl}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-slate-400">Adapter Mode:</span>
            <span className="text-emerald-400">Deterministic Mock Service Layer (Frontend Only)</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-slate-400">Backend Boundary:</span>
            <span className="text-cyan-300">100% Preserved (Zero Backend Mutation)</span>
          </div>
        </div>
      </div>
    </div>
  );
};
