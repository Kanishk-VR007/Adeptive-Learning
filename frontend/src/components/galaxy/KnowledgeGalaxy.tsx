import React, { useEffect, useRef, useState, useMemo } from 'react';
import { Play, Pause, RotateCcw, ZoomIn, ZoomOut, Sparkles, Eye, Info } from 'lucide-react';
import { ConceptGraphData, ConceptMastery } from '../../types';
import { GalaxyNodeHUD, GalaxyNodeData } from './GalaxyNodeHUD';

export interface KnowledgeGalaxyProps {
  graphData?: ConceptGraphData | null;
  masteries?: ConceptMastery[];
  subjectTitle?: string;
  onSelectConcept: (conceptId: number) => void;
  className?: string;
}

interface OrbitalConcept {
  id: number;
  name: string;
  subjectName: string;
  masteryProbability: number;
  prerequisites: string[];
  orbitRadius: number;
  speed: number;
  tilt: number;
  phase: number;
  color: string;
  size: number;
  // Dynamic 3D runtime values
  x: number;
  y: number;
  z: number;
  screenX: number;
  screenY: number;
  screenRadius: number;
}

export const KnowledgeGalaxy: React.FC<KnowledgeGalaxyProps> = ({
  graphData,
  masteries = [],
  subjectTitle = 'Calculus & Linear Algebra',
  onSelectConcept,
  className = '',
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);

  const [isPlaying, setIsPlaying] = useState<boolean>(true);
  const [zoomLevel, setZoomLevel] = useState<number>(1.0);
  const [hoveredNode, setHoveredNode] = useState<GalaxyNodeData | null>(null);
  const [selectedNode, setSelectedNode] = useState<GalaxyNodeData | null>(null);

  // Check prefers-reduced-motion
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(() => {
    if (typeof window !== 'undefined' && window.matchMedia) {
      return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    }
    return false;
  });

  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    const handler = (e: MediaQueryListEvent) => setPrefersReducedMotion(e.matches);
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, []);

  // Build orbital concepts mapping from graph data or default syllabus
  const orbitalConcepts = useMemo<OrbitalConcept[]>(() => {
    const defaultData = [
      { id: 1, name: 'Limits & Asymptotes', sub: 'Calculus', prob: 0.92, prereqs: [], orbit: 95, speed: 0.012, tilt: 0.35, phase: 0 },
      { id: 2, name: 'Derivatives & Rates', sub: 'Calculus', prob: 0.88, prereqs: ['Limits & Asymptotes'], orbit: 140, speed: -0.010, tilt: -0.25, phase: 1.2 },
      { id: 3, name: 'The Chain Rule', sub: 'Calculus', prob: 0.38, prereqs: ['Derivatives & Rates'], orbit: 185, speed: 0.008, tilt: 0.4, phase: 2.5 },
      { id: 4, name: 'Definite Integrals', sub: 'Calculus', prob: 0.65, prereqs: ['Derivatives & Rates'], orbit: 230, speed: -0.007, tilt: -0.3, phase: 3.8 },
      { id: 5, name: 'Integration by Parts', sub: 'Calculus', prob: 0.28, prereqs: ['Definite Integrals'], orbit: 275, speed: 0.006, tilt: 0.2, phase: 4.9 },
      { id: 6, name: 'Vector Spaces & Bases', sub: 'Linear Algebra', prob: 0.74, prereqs: [], orbit: 160, speed: 0.009, tilt: 0.5, phase: 0.8 },
      { id: 7, name: 'Matrix Inversion', sub: 'Linear Algebra', prob: 0.52, prereqs: ['Vector Spaces & Bases'], orbit: 215, speed: -0.008, tilt: -0.45, phase: 2.1 },
      { id: 8, name: 'Eigenvalues & Vectors', sub: 'Linear Algebra', prob: 0.34, prereqs: ['Matrix Inversion'], orbit: 310, speed: 0.005, tilt: 0.3, phase: 4.2 },
    ];

    return defaultData.map((d) => {
      // Color coded by BKT mastery
      let color = '#00F0FF'; // default cyan
      if (d.prob >= 0.75) color = '#10B981'; // Mastered Emerald
      else if (d.prob < 0.40) color = '#F43F5E'; // High risk Rose
      else color = '#3B82F6'; // Practicing Blue

      return {
        id: d.id,
        name: d.name,
        subjectName: d.sub,
        masteryProbability: d.prob,
        prerequisites: d.prereqs,
        orbitRadius: d.orbit,
        speed: d.speed,
        tilt: d.tilt,
        phase: d.phase,
        color,
        size: 7 + Math.round(d.prob * 4),
        x: 0,
        y: 0,
        z: 0,
        screenX: 0,
        screenY: 0,
        screenRadius: 7,
      };
    });
  }, [graphData, masteries]);

  // Starfield constellation background particles
  const stars = useMemo(() => {
    return Array.from({ length: 60 }, () => ({
      x: (Math.random() - 0.5) * 800,
      y: (Math.random() - 0.5) * 600,
      z: (Math.random() - 0.5) * 400,
      size: Math.random() * 2 + 0.8,
      alpha: Math.random() * 0.7 + 0.2,
    }));
  }, []);

  // Main 3D Canvas Rendering Loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animId: number;
    let time = 0;

    let width = (canvas.width = canvas.parentElement?.clientWidth || 700);
    let height = (canvas.height = canvas.parentElement?.clientHeight || 450);

    const handleResize = () => {
      if (!canvas || !canvas.parentElement) return;
      width = canvas.width = canvas.parentElement.clientWidth;
      height = canvas.height = canvas.parentElement.clientHeight;
    };
    window.addEventListener('resize', handleResize);

    // Mouse parallax offsets
    let mouseX = 0;
    let mouseY = 0;
    let currentTiltX = 0;
    let currentTiltY = 0;

    const handleMouseMove = (e: MouseEvent) => {
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      const x = e.clientX - rect.left - width / 2;
      const y = e.clientY - rect.top - height / 2;
      mouseX = x / (width / 2);
      mouseY = y / (height / 2);

      // Hit testing for nodes
      let foundNode: GalaxyNodeData | null = null;
      for (const node of orbitalConcepts) {
        const dx = e.clientX - rect.left - node.screenX;
        const dy = e.clientY - rect.top - node.screenY;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist <= node.screenRadius + 8) {
          foundNode = {
            id: node.id,
            name: node.name,
            subjectName: node.subjectName,
            masteryProbability: node.masteryProbability,
            prerequisites: node.prerequisites,
            x: node.screenX,
            y: node.screenY,
          };
          break;
        }
      }
      setHoveredNode(foundNode);
    };

    const handleClick = (e: MouseEvent) => {
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      for (const node of orbitalConcepts) {
        const dx = e.clientX - rect.left - node.screenX;
        const dy = e.clientY - rect.top - node.screenY;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist <= node.screenRadius + 10) {
          setSelectedNode({
            id: node.id,
            name: node.name,
            subjectName: node.subjectName,
            masteryProbability: node.masteryProbability,
            prerequisites: node.prerequisites,
            x: node.screenX,
            y: node.screenY,
          });
          return;
        }
      }
      setSelectedNode(null);
    };

    canvas.addEventListener('mousemove', handleMouseMove);
    canvas.addEventListener('click', handleClick);

    const fov = 400; // Camera perspective field of view

    const render = () => {
      if (isPlaying && !prefersReducedMotion) {
        time += 1;
      }

      // Smooth camera parallax inertia
      currentTiltX += (mouseX * 0.25 - currentTiltX) * 0.05;
      currentTiltY += (mouseY * 0.15 - currentTiltY) * 0.05;

      ctx.clearRect(0, 0, width, height);

      const centerX = width / 2;
      const centerY = height / 2;

      // 1. Draw Background Space Gradients & Nebulae
      const spaceGrad = ctx.createRadialGradient(
        centerX,
        centerY,
        20,
        centerX,
        centerY,
        Math.max(width, height) / 1.5
      );
      spaceGrad.addColorStop(0, 'rgba(15, 23, 42, 0.9)');
      spaceGrad.addColorStop(0.5, 'rgba(11, 15, 25, 0.95)');
      spaceGrad.addColorStop(1, 'rgba(8, 11, 17, 1)');
      ctx.fillStyle = spaceGrad;
      ctx.fillRect(0, 0, width, height);

      // 2. Draw Stars with Parallax
      stars.forEach((s) => {
        const rotY = s.x * Math.cos(currentTiltX) - s.z * Math.sin(currentTiltX);
        const rotZ = s.x * Math.sin(currentTiltX) + s.z * Math.cos(currentTiltX);
        const rotX = rotY;
        const rotY2 = s.y * Math.cos(currentTiltY) - rotZ * Math.sin(currentTiltY);
        const finalZ = s.y * Math.sin(currentTiltY) + rotZ * Math.cos(currentTiltY) + 500;

        if (finalZ > 20) {
          const scale = fov / finalZ;
          const sx = centerX + rotX * scale;
          const sy = centerY + rotY2 * scale;

          ctx.beginPath();
          ctx.arc(sx, sy, Math.max(0.5, s.size * scale), 0, Math.PI * 2);
          ctx.fillStyle = `rgba(226, 232, 240, ${s.alpha * 0.6})`;
          ctx.fill();
        }
      });

      // 3. Draw Keplerian Orbit Rings
      const uniqueRadii = Array.from(new Set(orbitalConcepts.map((c) => c.orbitRadius)));
      uniqueRadii.forEach((rad) => {
        ctx.beginPath();
        ctx.ellipse(
          centerX,
          centerY,
          rad * zoomLevel,
          rad * 0.35 * zoomLevel,
          currentTiltX * 0.5,
          0,
          Math.PI * 2
        );
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.06)';
        ctx.lineWidth = 1;
        ctx.setLineDash([3, 5]);
        ctx.stroke();
        ctx.setLineDash([]);
      });

      // 4. Draw Central Exam Sol Core
      const solRadius = 24 * zoomLevel;
      const solGrad = ctx.createRadialGradient(centerX, centerY, 2, centerX, centerY, solRadius * 2);
      solGrad.addColorStop(0, '#FFFFFF');
      solGrad.addColorStop(0.2, '#60A5FA');
      solGrad.addColorStop(0.6, 'rgba(37, 99, 235, 0.4)');
      solGrad.addColorStop(1, 'rgba(37, 99, 235, 0)');

      ctx.beginPath();
      ctx.arc(centerX, centerY, solRadius * 2.2, 0, Math.PI * 2);
      ctx.fillStyle = solGrad;
      ctx.fill();

      ctx.beginPath();
      ctx.arc(centerX, centerY, solRadius * 0.8, 0, Math.PI * 2);
      ctx.fillStyle = '#38BDF8';
      ctx.shadowColor = '#00F0FF';
      ctx.shadowBlur = 18;
      ctx.fill();
      ctx.shadowBlur = 0;

      // 5. Update & Project Orbital Concepts
      orbitalConcepts.forEach((node) => {
        const currentAngle = node.phase + (prefersReducedMotion ? 0 : time * node.speed);
        const rad = node.orbitRadius * zoomLevel;

        // 3D formulation with Keplerian ellipse and vertical oscillation
        const unrotX = Math.cos(currentAngle) * rad;
        const unrotZ = Math.sin(currentAngle) * rad;
        const unrotY = Math.sin(currentAngle * 2) * (20 * zoomLevel);

        // Apply camera tilt
        const rotY = unrotX * Math.cos(currentTiltX) - unrotZ * Math.sin(currentTiltX);
        const rotZ = unrotX * Math.sin(currentTiltX) + unrotZ * Math.cos(currentTiltX);
        const rotX = rotY;
        const rotY2 = unrotY * Math.cos(currentTiltY) - rotZ * Math.sin(currentTiltY);
        const finalZ = unrotY * Math.sin(currentTiltY) + rotZ * Math.cos(currentTiltY) + fov;

        node.x = rotX;
        node.y = rotY2;
        node.z = finalZ;

        const scale = fov / finalZ;
        node.screenX = centerX + rotX * scale;
        node.screenY = centerY + rotY2 * scale;
        node.screenRadius = node.size * scale;
      });

      // Sort nodes back-to-front for proper depth occlusion
      const sortedNodes = [...orbitalConcepts].sort((a, b) => b.z - a.z);

      // 6. Draw Prerequisite Constellation Edges
      sortedNodes.forEach((node) => {
        if (!node.prerequisites || node.prerequisites.length === 0) return;

        node.prerequisites.forEach((prereqName) => {
          const parent = orbitalConcepts.find((c) => c.name === prereqName);
          if (!parent) return;

          const isHoveredLine =
            hoveredNode?.id === node.id ||
            hoveredNode?.id === parent.id ||
            selectedNode?.id === node.id;

          ctx.beginPath();
          ctx.moveTo(parent.screenX, parent.screenY);
          // Curved quadratic bezier connection line
          const midX = (parent.screenX + node.screenX) / 2;
          const midY = (parent.screenY + node.screenY) / 2 - 15;
          ctx.quadraticCurveTo(midX, midY, node.screenX, node.screenY);

          ctx.strokeStyle = isHoveredLine
            ? 'rgba(0, 240, 255, 0.7)'
            : 'rgba(255, 255, 255, 0.12)';
          ctx.lineWidth = isHoveredLine ? 2 : 1;
          ctx.stroke();

          // Flowing particle pulses traveling from prereq to target
          if (!prefersReducedMotion) {
            const pulseT = ((time * 0.02 + node.id * 0.3) % 1);
            const px = (1 - pulseT) * (1 - pulseT) * parent.screenX + 2 * (1 - pulseT) * pulseT * midX + pulseT * pulseT * node.screenX;
            const py = (1 - pulseT) * (1 - pulseT) * parent.screenY + 2 * (1 - pulseT) * pulseT * midY + pulseT * pulseT * node.screenY;

            ctx.beginPath();
            ctx.arc(px, py, 2.5, 0, Math.PI * 2);
            ctx.fillStyle = isHoveredLine ? '#00F0FF' : '#94A3B8';
            ctx.shadowColor = '#00F0FF';
            ctx.shadowBlur = 6;
            ctx.fill();
            ctx.shadowBlur = 0;
          }
        });
      });

      // 7. Render Individual Concept Nodes
      sortedNodes.forEach((node) => {
        const isHovered = hoveredNode?.id === node.id;
        const isSelected = selectedNode?.id === node.id;
        const r = node.screenRadius * (isHovered || isSelected ? 1.4 : 1.0);

        // Node Glow Halo
        const glowGrad = ctx.createRadialGradient(
          node.screenX,
          node.screenY,
          r * 0.5,
          node.screenX,
          node.screenY,
          r * 2.8
        );
        glowGrad.addColorStop(0, node.color);
        glowGrad.addColorStop(1, 'rgba(0,0,0,0)');

        ctx.beginPath();
        ctx.arc(node.screenX, node.screenY, r * 2.8, 0, Math.PI * 2);
        ctx.fillStyle = glowGrad;
        ctx.fill();

        // Solid Node Sphere
        ctx.beginPath();
        ctx.arc(node.screenX, node.screenY, r, 0, Math.PI * 2);
        ctx.fillStyle = node.color;
        ctx.shadowColor = node.color;
        ctx.shadowBlur = isHovered ? 20 : 8;
        ctx.fill();
        ctx.shadowBlur = 0;

        // Outer Target Ring on Hover/Select
        if (isHovered || isSelected) {
          ctx.beginPath();
          ctx.arc(node.screenX, node.screenY, r + 5, 0, Math.PI * 2);
          ctx.strokeStyle = '#FFFFFF';
          ctx.lineWidth = 1.5;
          ctx.stroke();
        }

        // Text Label
        ctx.font = `${isHovered ? '600' : '500'} 11px Inter, sans-serif`;
        ctx.fillStyle = isHovered ? '#FFFFFF' : '#CBD5E1';
        ctx.textAlign = 'center';
        ctx.fillText(node.name, node.screenX, node.screenY + r + 14);
      });

      animId = requestAnimationFrame(render);
    };

    animId = requestAnimationFrame(render);

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener('resize', handleResize);
      canvas.removeEventListener('mousemove', handleMouseMove);
      canvas.removeEventListener('click', handleClick);
    };
  }, [orbitalConcepts, stars, isPlaying, zoomLevel, prefersReducedMotion, hoveredNode, selectedNode]);

  return (
    <div
      ref={containerRef}
      className={`relative w-full h-[420px] lg:h-[480px] rounded-3xl overflow-hidden border border-white/[0.08] shadow-2xl bg-slate-950 ${className}`}
      data-testid="knowledge-galaxy-container"
    >
      {/* 3D Canvas Viewport */}
      <canvas
        ref={canvasRef}
        className="w-full h-full cursor-grab active:cursor-grabbing block"
        aria-label="Interactive 3D Knowledge Galaxy concept graph"
      />

      {/* Floating HUD pinned to node */}
      {(selectedNode || hoveredNode) && (
        <GalaxyNodeHUD
          node={selectedNode || hoveredNode}
          onClose={() => {
            setSelectedNode(null);
            setHoveredNode(null);
          }}
          onPractice={(conceptId) => onSelectConcept(conceptId)}
        />
      )}

      {/* Top Overlay Badge & Title */}
      <div className="absolute top-4 left-4 z-10 pointer-events-none">
        <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-slate-900/80 backdrop-blur-md border border-white/10 text-xs font-medium text-slate-300">
          <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
          <span>3D Knowledge Galaxy</span>
          <span className="text-slate-500">•</span>
          <span className="text-cyan-400 font-semibold">{subjectTitle}</span>
        </div>
      </div>

      {/* Bottom Floating Spatial Controls (Spline style) */}
      <div className="absolute bottom-4 right-4 z-10 flex items-center gap-1.5 p-1.5 rounded-2xl bg-slate-900/85 backdrop-blur-xl border border-white/10 shadow-lg">
        <button
          onClick={() => setIsPlaying(!isPlaying)}
          className="p-2 rounded-xl text-slate-300 hover:text-white hover:bg-slate-800 transition-colors"
          title={isPlaying ? 'Pause orbital rotation' : 'Resume orbital rotation'}
          aria-label={isPlaying ? 'Pause orbit' : 'Play orbit'}
        >
          {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4 text-cyan-400" />}
        </button>
        <button
          onClick={() => setZoomLevel((z) => Math.min(1.6, z + 0.15))}
          className="p-2 rounded-xl text-slate-300 hover:text-white hover:bg-slate-800 transition-colors"
          title="Zoom in"
          aria-label="Zoom in"
        >
          <ZoomIn className="w-4 h-4" />
        </button>
        <button
          onClick={() => setZoomLevel((z) => Math.max(0.6, z - 0.15))}
          className="p-2 rounded-xl text-slate-300 hover:text-white hover:bg-slate-800 transition-colors"
          title="Zoom out"
          aria-label="Zoom out"
        >
          <ZoomOut className="w-4 h-4" />
        </button>
        <button
          onClick={() => setZoomLevel(1.0)}
          className="p-2 rounded-xl text-slate-300 hover:text-white hover:bg-slate-800 transition-colors"
          title="Reset zoom"
          aria-label="Reset zoom"
        >
          <RotateCcw className="w-4 h-4" />
        </button>
      </div>

      {/* Legend & BKT Mastery Status Bar */}
      <div className="absolute bottom-4 left-4 z-10 hidden sm:flex items-center gap-3 px-3 py-1.5 rounded-xl bg-slate-900/80 backdrop-blur-md border border-white/10 text-[11px] text-slate-400">
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 shadow-glow-emerald" />
          <span>Mastered (&ge; 75%)</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-blue-400" />
          <span>Practicing</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-rose-400" />
          <span>Weak Gap (&lt; 40%)</span>
        </div>
      </div>
    </div>
  );
};
