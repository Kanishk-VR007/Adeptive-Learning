import React, { useState } from 'react';
import { Network, ArrowRight, Target } from 'lucide-react';
import { ConceptGraphData, GraphNode } from '../../types';

interface ConceptPrereqGraphProps {
  graphData: ConceptGraphData;
  onSelectConceptToPractice: (conceptId: number) => void;
}

export const ConceptPrereqGraph: React.FC<ConceptPrereqGraphProps> = ({
  graphData,
  onSelectConceptToPractice,
}) => {
  const [selectedNodeId, setSelectedNodeId] = useState<number>(6); // Default highlight Chain Rule

  const selectedNode = graphData.nodes.find((n) => n.id === selectedNodeId) || graphData.nodes[0];

  // Find incoming prerequisites and outgoing dependents for selected node
  const prerequisites = graphData.edges
    .filter((e) => e.toConceptId === selectedNodeId)
    .map((e) => graphData.nodes.find((n) => n.id === e.fromConceptId))
    .filter(Boolean) as GraphNode[];

  const dependents = graphData.edges
    .filter((e) => e.fromConceptId === selectedNodeId)
    .map((e) => graphData.nodes.find((n) => n.id === e.toConceptId))
    .filter(Boolean) as GraphNode[];

  // Group nodes by tier level
  const tiers = [0, 1, 2, 3];

  return (
    <div
      className="p-5 rounded-2xl bg-background-card border border-slate-800/80 shadow-card-soft"
      data-testid="concept-prereq-graph"
    >
      <div className="flex flex-wrap items-center justify-between gap-3 mb-5 border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-cyan-500/15 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
            <Network className="w-4 h-4" />
          </div>
          <div>
            <h3 className="font-semibold text-sm text-slate-100">Prerequisite Concept DAG Map</h3>
            <p className="text-[11px] text-slate-400">Directed Acyclic Knowledge Graph (FastAPI DAG Schema)</p>
          </div>
        </div>

        {/* Legend */}
        <div className="flex items-center gap-3 text-[11px]">
          <span className="flex items-center gap-1.5 text-slate-300">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 shadow-sm" />
            Mastered (&ge;90%)
          </span>
          <span className="flex items-center gap-1.5 text-slate-300">
            <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 shadow-sm" />
            Developing (40-89%)
          </span>
          <span className="flex items-center gap-1.5 text-slate-300">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-500 shadow-sm" />
            Weak (&lt;40%)
          </span>
        </div>
      </div>

      {/* 2D DAG Visual Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 p-4 rounded-xl bg-slate-900/60 border border-slate-800/80 mb-5 overflow-x-auto">
        {tiers.map((tier) => {
          const tierNodes = graphData.nodes.filter((n) => n.tierLevel === tier);
          const tierTitle =
            tier === 0
              ? 'Foundation'
              : tier === 1
              ? 'Core Limits'
              : tier === 2
              ? 'Differentiation'
              : 'Advanced Chain';

          return (
            <div key={tier} className="space-y-3 min-w-[160px]">
              <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 text-center pb-1 border-b border-slate-800">
                {tierTitle}
              </div>

              <div className="space-y-2.5">
                {tierNodes.map((node) => {
                  const isSelected = selectedNodeId === node.id;
                  const isPrereq = prerequisites.some((p) => p.id === node.id);
                  const isDependent = dependents.some((d) => d.id === node.id);
                  const pct = Math.round(node.masteryProbability * 100);

                  let statusColor = 'border-slate-700 bg-slate-900';
                  let badgeColor = 'text-slate-400';
                  if (node.masteryProbability >= 0.90) {
                    statusColor = 'border-emerald-500/40 bg-emerald-950/20';
                    badgeColor = 'text-emerald-400';
                  } else if (node.masteryProbability >= 0.40) {
                    statusColor = 'border-cyan-500/40 bg-cyan-950/20';
                    badgeColor = 'text-cyan-400';
                  } else {
                    statusColor = 'border-rose-500/40 bg-rose-950/20';
                    badgeColor = 'text-rose-400';
                  }

                  return (
                    <button
                      key={node.id}
                      onClick={() => setSelectedNodeId(node.id)}
                      className={`w-full text-left p-3 rounded-xl border transition-all relative ${statusColor} ${
                        isSelected
                          ? 'ring-2 ring-cyan-400 shadow-glow-cyan'
                          : isPrereq
                          ? 'ring-1 ring-amber-400/60 bg-amber-950/10'
                          : isDependent
                          ? 'ring-1 ring-electric-400/60'
                          : 'hover:border-slate-600'
                      }`}
                      data-testid={`dag-node-${node.id}`}
                    >
                      <div className="flex items-center justify-between gap-1 mb-1">
                        <span className="text-[10px] font-mono text-slate-400 truncate">
                          {node.conceptCode}
                        </span>
                        <span className={`text-[11px] font-mono font-bold ${badgeColor}`}>
                          {pct}%
                        </span>
                      </div>

                      <div className="text-xs font-semibold text-slate-200 line-clamp-2">
                        {node.name}
                      </div>

                      {/* Pill indicator */}
                      <div className="mt-2 flex items-center justify-between text-[10px] text-slate-400">
                        <span className="capitalize">{node.difficultyLevel}</span>
                        {isSelected && <span className="text-cyan-400 font-bold">Selected</span>}
                        {isPrereq && <span className="text-amber-400 font-semibold">Prereq</span>}
                        {isDependent && <span className="text-electric-400 font-semibold">Leads To</span>}
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      {/* Selected Node Details Drawer */}
      {selectedNode && (
        <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="text-sm font-bold text-slate-100">{selectedNode.name}</span>
              <span className="text-xs font-mono text-cyan-400">({selectedNode.conceptCode})</span>
              <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 capitalize">
                {selectedNode.difficultyLevel}
              </span>
            </div>

            <div className="flex flex-wrap items-center gap-3 text-xs text-slate-400">
              <span>
                Prerequisites:{' '}
                <strong className="text-amber-300 font-normal">
                  {prerequisites.length > 0
                    ? prerequisites.map((p) => p.name).join(', ')
                    : 'None (Root Concept)'}
                </strong>
              </span>
              <span>•</span>
              <span>
                Enables:{' '}
                <strong className="text-electric-300 font-normal">
                  {dependents.length > 0
                    ? dependents.map((d) => d.name).join(', ')
                    : 'Advanced Topics'}
                </strong>
              </span>
            </div>
          </div>

          <button
            onClick={() => onSelectConceptToPractice(selectedNode.id)}
            className="px-4 py-2 rounded-xl bg-gradient-to-r from-electric-600 to-cyan-500 hover:from-electric-500 hover:to-cyan-400 text-white font-semibold text-xs flex items-center gap-2 shadow-glow-cyan transition-all transform active:scale-95 shrink-0"
            data-testid="practice-selected-dag-node"
          >
            <Target className="w-3.5 h-3.5" />
            <span>Practice {selectedNode.name}</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      )}
    </div>
  );
};
