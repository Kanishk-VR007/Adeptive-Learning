import React, { useEffect, useRef, useState } from 'react';
import {
  Sparkles,
  Maximize2,
  RotateCcw,
  Activity,
  CheckCircle2,
  Layers,
  Brain,
  Repeat,
  HelpCircle,
  AlertTriangle,
} from 'lucide-react';

interface GalaxySatellite {
  id: string;
  name: string;
  icon: string;
  color: string;
  description: string;
  orbitRadius: number;
  orbitSpeed: number;
  inclination: number; // orbital tilt in radians
  phase: number;
  size: number;
}

const GALAXY_NODES: GalaxySatellite[] = [
  {
    id: 'diagnostic',
    name: 'Diagnostic Assessment',
    icon: 'Activity',
    color: '#00F0FF',
    description: 'Pinpoints baseline conceptual frontiers before practice starts',
    orbitRadius: 155,
    orbitSpeed: 0.016,
    inclination: 0.25,
    phase: 0,
    size: 20,
  },
  {
    id: 'mastery',
    name: 'Concept Mastery',
    icon: 'CheckCircle2',
    color: '#10B981',
    description: 'Tracks Bayesian Knowledge Tracing probability P(L) in real-time',
    orbitRadius: 195,
    orbitSpeed: 0.012,
    inclination: -0.32,
    phase: 1.05,
    size: 22,
  },
  {
    id: 'adaptive',
    name: 'Adaptive Questions',
    icon: 'HelpCircle',
    color: '#3B82F6',
    description: 'Dynamically serves questions tuned to individual proximal development',
    orbitRadius: 235,
    orbitSpeed: 0.014,
    inclination: 0.42,
    phase: 2.1,
    size: 21,
  },
  {
    id: 'misconception',
    name: 'Misconception Detection',
    icon: 'AlertTriangle',
    color: '#F59E0B',
    description: 'Diagnoses reasoning errors and categorizes root cognitive flaws',
    orbitRadius: 175,
    orbitSpeed: 0.019,
    inclination: -0.18,
    phase: 3.14,
    size: 20,
  },
  {
    id: 'spaced_repetition',
    name: 'Spaced Repetition',
    icon: 'Repeat',
    color: '#8B5CF6',
    description: 'Schedules review intervals via FSRS memory retention modeling',
    orbitRadius: 215,
    orbitSpeed: 0.011,
    inclination: 0.35,
    phase: 4.2,
    size: 21,
  },
  {
    id: 'analytics',
    name: 'Learning Analytics',
    icon: 'Layers',
    color: '#EC4899',
    description: 'Surfaces topological learning paths and mastery trajectory heatmaps',
    orbitRadius: 255,
    orbitSpeed: 0.009,
    inclination: -0.45,
    phase: 5.25,
    size: 22,
  },
];

interface Particle {
  x: number;
  y: number;
  z: number;
  size: number;
  speed: number;
  alpha: number;
}

export const LandingGalaxy: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const [activeNode, setActiveNode] = useState<GalaxySatellite | null>(null);
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
  const [isHovering, setIsHovering] = useState(false);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrameId: number;
    let time = 0;

    // Check reduced motion preference
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    // High DPI canvas scaling
    const resizeCanvas = () => {
      const rect = canvas.getBoundingClientRect();
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;
      ctx.scale(dpr, dpr);
    };

    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);

    // Generate ambient background stardust particles
    const particleCount = 70;
    const particles: Particle[] = Array.from({ length: particleCount }, () => ({
      x: (Math.random() - 0.5) * 600,
      y: (Math.random() - 0.5) * 600,
      z: Math.random() * 400 - 200,
      size: Math.random() * 1.8 + 0.6,
      speed: Math.random() * 0.003 + 0.001,
      alpha: Math.random() * 0.6 + 0.2,
    }));

    // Mouse coordinates tracking with spring interpolation
    let targetRotX = 0;
    let targetRotY = 0;
    let currentRotX = 0;
    let currentRotY = 0;

    const render = () => {
      const rect = canvas.getBoundingClientRect();
      const width = rect.width;
      const height = rect.height;
      const centerX = width / 2;
      const centerY = height / 2;

      ctx.clearRect(0, 0, width, height);

      // Spring mouse parallax
      targetRotX = (mousePos.y / height - 0.5) * 0.35;
      targetRotY = (mousePos.x / width - 0.5) * 0.45;
      currentRotX += (targetRotX - currentRotX) * 0.06;
      currentRotY += (targetRotY - currentRotY) * 0.06;

      const rotX = prefersReducedMotion ? 0.2 : currentRotX + 0.22;
      const rotY = prefersReducedMotion ? 0 : currentRotY;

      // 1. Draw Stardust Particles
      particles.forEach((p) => {
        p.z -= p.speed * 20;
        if (p.z < -200) p.z = 200;

        const scale = 300 / (300 + p.z);
        const px = centerX + p.x * scale;
        const py = centerY + p.y * scale;

        if (px >= 0 && px <= width && py >= 0 && py <= height) {
          ctx.beginPath();
          ctx.arc(px, py, p.size * scale, 0, Math.PI * 2);
          ctx.fillStyle = `rgba(148, 163, 184, ${p.alpha * scale})`;
          ctx.fill();
        }
      });

      // 2. Draw Central Sol Knowledge Core
      const corePulse = 1 + Math.sin(time * 2) * 0.04;
      const coreRadius = 38 * corePulse;

      // Outer Glow Aura
      const auraGradient = ctx.createRadialGradient(
        centerX,
        centerY,
        coreRadius * 0.5,
        centerX,
        centerY,
        coreRadius * 3.2
      );
      auraGradient.addColorStop(0, 'rgba(0, 240, 255, 0.45)');
      auraGradient.addColorStop(0.35, 'rgba(37, 99, 235, 0.25)');
      auraGradient.addColorStop(0.7, 'rgba(124, 58, 237, 0.12)');
      auraGradient.addColorStop(1, 'rgba(11, 15, 25, 0)');

      ctx.beginPath();
      ctx.arc(centerX, centerY, coreRadius * 3.2, 0, Math.PI * 2);
      ctx.fillStyle = auraGradient;
      ctx.fill();

      // Core Solid Sphere with Gradient
      const coreGradient = ctx.createRadialGradient(
        centerX - coreRadius * 0.3,
        centerY - coreRadius * 0.3,
        coreRadius * 0.1,
        centerX,
        centerY,
        coreRadius
      );
      coreGradient.addColorStop(0, '#FFFFFF');
      coreGradient.addColorStop(0.3, '#38BDF8');
      coreGradient.addColorStop(0.7, '#2563EB');
      coreGradient.addColorStop(1, '#0F172A');

      ctx.beginPath();
      ctx.arc(centerX, centerY, coreRadius, 0, Math.PI * 2);
      ctx.fillStyle = coreGradient;
      ctx.shadowColor = '#00F0FF';
      ctx.shadowBlur = 24;
      ctx.fill();
      ctx.shadowBlur = 0;

      // Core Equator Ring
      ctx.beginPath();
      ctx.ellipse(centerX, centerY, coreRadius * 1.5, coreRadius * 0.45, 0.3, 0, Math.PI * 2);
      ctx.strokeStyle = 'rgba(0, 240, 255, 0.35)';
      ctx.lineWidth = 1.5;
      ctx.stroke();

      // 3. Compute and Render Orbital Nodes & Constellation Lines
      const computedNodes: {
        node: GalaxySatellite;
        x: number;
        y: number;
        z: number;
        scale: number;
      }[] = [];

      GALAXY_NODES.forEach((node) => {
        const currentAngle = prefersReducedMotion ? node.phase : time * node.orbitSpeed * 35 + node.phase;

        // 3D Orbital Coordinates
        const unrotatedX = node.orbitRadius * Math.cos(currentAngle);
        const unrotatedY = node.orbitRadius * Math.sin(currentAngle) * Math.sin(node.inclination);
        const unrotatedZ = node.orbitRadius * Math.sin(currentAngle) * Math.cos(node.inclination);

        // Apply 3D Rotation (Pitch & Yaw)
        const cosX = Math.cos(rotX);
        const sinX = Math.sin(rotX);
        const cosY = Math.cos(rotY);
        const sinY = Math.sin(rotY);

        // Yaw around Y
        const x1 = unrotatedX * cosY + unrotatedZ * sinY;
        const z1 = -unrotatedX * sinY + unrotatedZ * cosY;

        // Pitch around X
        const y2 = unrotatedY * cosX - z1 * sinX;
        const z2 = unrotatedY * sinX + z1 * cosX;

        // Perspective Projection
        const fov = 420;
        const scale = fov / (fov + z2);
        const projX = centerX + x1 * scale;
        const projY = centerY + y2 * scale;

        computedNodes.push({
          node,
          x: projX,
          y: projY,
          z: z2,
          scale,
        });

        // Draw Orbital Path Guide Ellipse
        ctx.beginPath();
        ctx.ellipse(
          centerX,
          centerY,
          node.orbitRadius * scale,
          node.orbitRadius * Math.abs(Math.sin(node.inclination) * 0.8 + 0.35) * scale,
          node.inclination * 0.5,
          0,
          Math.PI * 2
        );
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
        ctx.lineWidth = 1;
        ctx.stroke();

        // Constellation Edge from Core to Node
        const edgeAlpha = Math.max(0.12, Math.min(0.65, scale * 0.45));
        ctx.beginPath();
        ctx.moveTo(centerX, centerY);
        ctx.lineTo(projX, projY);
        ctx.strokeStyle = `rgba(0, 240, 255, ${edgeAlpha})`;
        ctx.setLineDash([4, 6]);
        ctx.lineWidth = 1.2;
        ctx.stroke();
        ctx.setLineDash([]);
      });

      // Sort nodes by Z-depth for proper rendering order (back-to-front)
      computedNodes.sort((a, b) => b.z - a.z);

      // Render Nodes
      computedNodes.forEach(({ node, x, y, scale }) => {
        const isHovered = activeNode?.id === node.id;
        const radius = (node.size / 2) * scale * (isHovered ? 1.35 : 1);

        // Node Glow Halo
        const glow = ctx.createRadialGradient(x, y, radius * 0.2, x, y, radius * 2.5);
        glow.addColorStop(0, node.color);
        glow.addColorStop(1, 'rgba(0,0,0,0)');

        ctx.beginPath();
        ctx.arc(x, y, radius * 2.5, 0, Math.PI * 2);
        ctx.fillStyle = glow;
        ctx.fill();

        // Node Body
        ctx.beginPath();
        ctx.arc(x, y, radius, 0, Math.PI * 2);
        ctx.fillStyle = isHovered ? '#FFFFFF' : node.color;
        ctx.shadowColor = node.color;
        ctx.shadowBlur = isHovered ? 18 : 8;
        ctx.fill();
        ctx.shadowBlur = 0;

        // Node Text Tag Label
        ctx.font = `600 ${Math.max(10, Math.round(11 * scale))}px "Inter", sans-serif`;
        ctx.fillStyle = isHovered ? '#38BDF8' : '#E2E8F0';
        ctx.textAlign = 'center';
        ctx.fillText(node.name, x, y + radius + 15 * scale);
      });

      if (!prefersReducedMotion) {
        time += 0.016;
      }
      animationFrameId = requestAnimationFrame(render);
    };

    animationFrameId = requestAnimationFrame(render);

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener('resize', resizeCanvas);
    };
  }, [mousePos, activeNode]);

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    setMousePos({
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    });
  };

  return (
    <div
      ref={containerRef}
      onMouseMove={handleMouseMove}
      onMouseEnter={() => setIsHovering(true)}
      onMouseLeave={() => {
        setIsHovering(false);
        setActiveNode(null);
      }}
      className="relative w-full aspect-square max-w-[580px] mx-auto select-none flex items-center justify-center"
      data-testid="landing-knowledge-galaxy"
    >
      {/* Background Radial Glow */}
      <div className="absolute inset-0 bg-gradient-to-tr from-blue-900/20 via-cyan-900/10 to-purple-900/20 rounded-full blur-3xl pointer-events-none" />

      {/* Main Procedural WebGL/Canvas Viewport */}
      <canvas
        ref={canvasRef}
        className="w-full h-full cursor-grab active:cursor-grabbing relative z-10"
        style={{ touchAction: 'none' }}
      />

      {/* Floating HUD Node Information Badge */}
      {activeNode && (
        <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-20 px-4 py-2.5 rounded-2xl bg-slate-900/90 border border-cyan-500/40 backdrop-blur-md shadow-2xl animate-in fade-in zoom-in-95 duration-150 max-w-xs text-center pointer-events-none">
          <div className="text-xs font-bold text-white flex items-center justify-center gap-1.5">
            <span
              className="w-2 h-2 rounded-full"
              style={{ backgroundColor: activeNode.color }}
            />
            {activeNode.name}
          </div>
          <p className="text-[11px] text-slate-300 mt-0.5 leading-snug">
            {activeNode.description}
          </p>
        </div>
      )}

      {/* Interactive Satellite Filter Pill Carousel */}
      <div className="absolute -bottom-7 left-0 right-0 z-20 flex items-center justify-center gap-1.5 overflow-x-auto py-1 px-2 no-scrollbar">
        {GALAXY_NODES.map((node) => (
          <button
            key={node.id}
            onClick={() => setActiveNode(activeNode?.id === node.id ? null : node)}
            className={`px-2.5 py-1 rounded-full text-[10px] font-semibold transition-all border shrink-0 ${
              activeNode?.id === node.id
                ? 'bg-cyan-500/20 border-cyan-400 text-cyan-300 shadow-glow-cyan/40 scale-105'
                : 'bg-slate-900/70 border-slate-800 text-slate-400 hover:text-slate-200 hover:border-slate-700'
            }`}
          >
            {node.name}
          </button>
        ))}
      </div>
    </div>
  );
};
