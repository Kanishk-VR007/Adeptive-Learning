import React, { useState } from 'react';
import {
  ConceptMastery,
  ConceptGraphData,
  ActivitySummary,
} from '../types';
import { OverallMasteryOverview, SubjectProgressSummary } from '../services/progressService';
import { MasteryCircularGauge } from '../components/progress/MasteryCircularGauge';
import { SubjectProgressCard } from '../components/progress/SubjectProgressCard';
import { ActivityTrendChart } from '../components/progress/ActivityTrendChart';
import { ConceptPrereqGraph } from '../components/progress/ConceptPrereqGraph';
import { KnowledgeGalaxy } from '../components/galaxy/KnowledgeGalaxy';
import { Badge } from '../components/common/Badge';
import { ProgressBar } from '../components/common/ProgressBar';
import {
  Award,
  CheckCircle2,
  AlertTriangle,
  TrendingUp,
  Search,
  Filter,
  ArrowRight,
  Target,
  Sparkles,
} from 'lucide-react';

interface ProgressPageProps {
  overview: OverallMasteryOverview;
  subjectSummaries: SubjectProgressSummary[];
  allMasteries: ConceptMastery[];
  strongConcepts: ConceptMastery[];
  weakConcepts: ConceptMastery[];
  graphData: ConceptGraphData;
  activityHistory: ActivitySummary[];
  onStartLearning: (conceptId: number) => void;
  onSelectSubject: (subjectId: number) => void;
}

export const ProgressPage: React.FC<ProgressPageProps> = ({
  overview,
  subjectSummaries,
  allMasteries,
  strongConcepts,
  weakConcepts,
  graphData,
  activityHistory,
  onStartLearning,
  onSelectSubject,
}) => {
  const [filterTier, setFilterTier] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [graphView, setGraphView] = useState<'3d' | '2d'>('3d');

  const filteredMasteries = allMasteries.filter((m) => {
    const matchesSearch =
      m.conceptName.toLowerCase().includes(searchQuery.toLowerCase()) ||
      m.conceptCode.toLowerCase().includes(searchQuery.toLowerCase());

    if (!matchesSearch) return false;
    if (filterTier === 'all') return true;
    if (filterTier === 'mastered') return m.currentMastery >= 0.90;
    if (filterTier === 'good') return m.currentMastery >= 0.70 && m.currentMastery < 0.90;
    if (filterTier === 'developing') return m.currentMastery >= 0.40 && m.currentMastery < 0.70;
    if (filterTier === 'weak') return m.currentMastery < 0.40;
    return true;
  });

  return (
    <div className="space-y-6 pb-12" data-testid="progress-page">
      {/* Top Banner: Circular Progress & Mastery Overview */}
      <section className="grid grid-cols-1 md:grid-cols-12 gap-6 items-stretch">
        <div className="md:col-span-4 p-6 rounded-2xl bg-background-card border border-slate-800/80 shadow-card-soft flex flex-col items-center justify-center text-center">
          <MasteryCircularGauge percentage={overview.overallMasteryPercentage} size={160} />
          <h3 className="text-sm font-bold text-slate-100 mt-4">Total Curriculum Mastery</h3>
          <p className="text-xs text-slate-400 max-w-xs mt-1">
            Aggregated across Calculus, Linear Algebra, and Data Structures modules.
          </p>
        </div>

        <div className="md:col-span-8 p-6 rounded-2xl bg-background-card border border-slate-800/80 shadow-card-soft flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-electric-600/20 border border-electric-500/30 flex items-center justify-center text-electric-400">
                  <Award className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="font-semibold text-sm text-slate-100">Mastery Distribution</h3>
                  <p className="text-[11px] text-slate-400">Continuous Bayesian Probability Tiers</p>
                </div>
              </div>
              <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-300 border border-cyan-500/30">
                {overview.totalQuestionsAnswered} Total Questions Evaluated
              </span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
              <div className="p-3 rounded-xl bg-emerald-950/20 border border-emerald-800/30">
                <span className="text-[10px] uppercase font-bold text-emerald-400 block mb-1">
                  Mastered (&ge;90%)
                </span>
                <span className="text-xl font-bold text-slate-100">
                  {allMasteries.filter((m) => m.currentMastery >= 0.90).length}
                </span>
              </div>

              <div className="p-3 rounded-xl bg-blue-950/20 border border-blue-800/30">
                <span className="text-[10px] uppercase font-bold text-blue-400 block mb-1">
                  Good (70-89%)
                </span>
                <span className="text-xl font-bold text-slate-100">
                  {allMasteries.filter((m) => m.currentMastery >= 0.70 && m.currentMastery < 0.90).length}
                </span>
              </div>

              <div className="p-3 rounded-xl bg-amber-950/20 border border-amber-800/30">
                <span className="text-[10px] uppercase font-bold text-amber-400 block mb-1">
                  Developing (40-69%)
                </span>
                <span className="text-xl font-bold text-slate-100">
                  {allMasteries.filter((m) => m.currentMastery >= 0.40 && m.currentMastery < 0.70).length}
                </span>
              </div>

              <div className="p-3 rounded-xl bg-rose-950/20 border border-rose-800/30">
                <span className="text-[10px] uppercase font-bold text-rose-400 block mb-1">
                  Weak (&lt;40%)
                </span>
                <span className="text-xl font-bold text-slate-100">
                  {allMasteries.filter((m) => m.currentMastery < 0.40).length}
                </span>
              </div>
            </div>
          </div>

          {/* Quick summary status */}
          <div className="p-3 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-300 flex items-center justify-between">
            <span className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-cyan-400" />
              <span>Recommended daily goal: 3 questions on Weak Concepts</span>
            </span>
            <button
              onClick={() => onStartLearning(weakConcepts[0]?.conceptId || 6)}
              className="text-xs font-semibold text-cyan-400 hover:underline flex items-center gap-1"
            >
              <span>Practice Now</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </section>

      {/* Prerequisite Structure: 3D Galaxy vs 2D DAG Switcher */}
      <section className="space-y-3">
        <div className="flex items-center justify-between px-1">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider">
              Knowledge Graph Visualization
            </h3>
            <span className="text-[11px] text-slate-400">
              Interactive BKT Prerequisite Architecture
            </span>
          </div>

          <div className="flex items-center gap-1.5 p-1 rounded-xl bg-slate-900 border border-slate-800 text-xs">
            <button
              onClick={() => setGraphView('3d')}
              className={`px-3 py-1 rounded-lg font-medium transition-all ${
                graphView === '3d'
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              3D Galaxy
            </button>
            <button
              onClick={() => setGraphView('2d')}
              className={`px-3 py-1 rounded-lg font-medium transition-all ${
                graphView === '2d'
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              2D DAG Tree
            </button>
          </div>
        </div>

        {graphView === '3d' ? (
          <KnowledgeGalaxy
            graphData={graphData}
            masteries={allMasteries}
            subjectTitle={subjectSummaries[0]?.subjectName || 'Calculus & Real Analysis'}
            onSelectConcept={onStartLearning}
          />
        ) : (
          <ConceptPrereqGraph
            graphData={graphData}
            onSelectConceptToPractice={(conceptId) => onStartLearning(conceptId)}
          />
        )}
      </section>

      {/* Side-by-Side: Strong vs Weak Concepts */}
      <section className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Strong Concepts */}
        <div className="p-5 rounded-2xl bg-background-card border border-slate-800/80 shadow-card-soft">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
              <CheckCircle2 className="w-4 h-4" />
            </div>
            <div>
              <h3 className="font-semibold text-sm text-slate-100">Strongest Concepts</h3>
              <p className="text-[11px] text-slate-400">High retention and accuracy</p>
            </div>
          </div>

          <div className="space-y-2.5">
            {strongConcepts.map((c) => (
              <div
                key={c.id}
                className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 flex items-center justify-between"
              >
                <div>
                  <div className="text-xs font-semibold text-slate-200">{c.conceptName}</div>
                  <div className="text-[10px] text-slate-400">{c.correctAttempts} of {c.totalAttempts} correct</div>
                </div>
                <div className="text-right">
                  <div className="text-xs font-mono font-bold text-emerald-400">
                    {Math.round(c.currentMastery * 100)}%
                  </div>
                  <Badge label="Mastered" variant="mastery" tier="Mastered" size="sm" />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Weak Concepts */}
        <div className="p-5 rounded-2xl bg-background-card border border-slate-800/80 shadow-card-soft">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-8 h-8 rounded-lg bg-rose-500/15 border border-rose-500/30 flex items-center justify-center text-rose-400">
              <AlertTriangle className="w-4 h-4" />
            </div>
            <div>
              <h3 className="font-semibold text-sm text-slate-100">Concepts Needing Focus</h3>
              <p className="text-[11px] text-slate-400">Target these to boost exam score</p>
            </div>
          </div>

          <div className="space-y-2.5">
            {weakConcepts.map((c) => (
              <div
                key={c.id}
                className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 flex items-center justify-between"
              >
                <div>
                  <div className="text-xs font-semibold text-slate-200">{c.conceptName}</div>
                  <div className="text-[10px] text-rose-400">Needs Practice</div>
                </div>
                <button
                  onClick={() => onStartLearning(c.conceptId)}
                  className="px-2.5 py-1 rounded-lg bg-electric-600/30 hover:bg-electric-600 text-cyan-300 hover:text-white border border-cyan-500/30 text-xs font-medium transition-colors"
                >
                  Practice ({Math.round(c.currentMastery * 100)}%)
                </button>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 7-Day Activity Trend Chart */}
      <section>
        <ActivityTrendChart data={activityHistory} />
      </section>

      {/* Full Concept Mastery Table with Filter */}
      <section className="p-5 rounded-2xl bg-background-card border border-slate-800/80 shadow-card-soft">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
          <div>
            <h3 className="font-semibold text-sm text-slate-100">All Concept Masteries</h3>
            <p className="text-[11px] text-slate-400">Comprehensive syllabus status tracking</p>
          </div>

          {/* Search & Tier Filters */}
          <div className="flex flex-wrap items-center gap-2">
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 transform -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search concepts..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-8 pr-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-xs text-slate-200 placeholder-slate-500 outline-none focus:border-cyan-400"
              />
            </div>

            <select
              value={filterTier}
              onChange={(e) => setFilterTier(e.target.value)}
              className="px-2.5 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-xs text-slate-200 outline-none focus:border-cyan-400"
            >
              <option value="all">All Tiers</option>
              <option value="mastered">Mastered (&ge;90%)</option>
              <option value="good">Good (70-89%)</option>
              <option value="developing">Developing (40-69%)</option>
              <option value="weak">Weak (&lt;40%)</option>
            </select>
          </div>
        </div>

        {/* Table list */}
        <div className="divide-y divide-slate-800">
          {filteredMasteries.map((m) => {
            const pct = Math.round(m.currentMastery * 100);
            return (
              <div
                key={m.id}
                className="py-3 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-slate-900/40 px-2 rounded-lg transition-colors"
              >
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-xs text-slate-200">{m.conceptName}</span>
                    <span className="text-[10px] font-mono text-slate-400">{m.conceptCode}</span>
                  </div>
                  <div className="text-[11px] text-slate-400 mt-0.5">
                    {m.correctAttempts} correct out of {m.totalAttempts} practice attempts
                  </div>
                </div>

                <div className="flex items-center gap-4 shrink-0">
                  <div className="w-28 hidden sm:block">
                    <ProgressBar value={pct} height="h-1.5" />
                  </div>
                  <span className="text-xs font-mono font-bold text-slate-200 w-10 text-right">
                    {pct}%
                  </span>
                  <Badge label={m.masteryClassification} variant="mastery" tier={m.masteryClassification} size="sm" />
                  <button
                    onClick={() => onStartLearning(m.conceptId)}
                    className="p-1.5 rounded-lg bg-slate-800 hover:bg-electric-600 text-slate-300 hover:text-white transition-colors"
                    title="Practice Concept"
                  >
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
};
