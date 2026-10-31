import React, { useEffect, useRef, useState } from 'react';

interface KnowledgeOrbProps {
  className?: string;
  splineSceneUrl?: string; // Optional Spline URL
  interactive?: boolean;
}

export const KnowledgeOrb: React.FC<KnowledgeOrbProps> = ({
  className = '',
  splineSceneUrl,
  interactive = true,
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(() => {
    if (typeof window !== 'undefined' && window.matchMedia) {
      return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    }
    return false;
  });
  const [isSplineLoaded, setIsSplineLoaded] = useState(false);

  // Check reduced motion preference changes
  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    const handler = (e: MediaQueryListEvent) => setPrefersReducedMotion(e.matches);
    mediaQuery.addEventListener('change', handler);
    return () => mediaQuery.removeEventListener('change', handler);
  }, []);

  // Attempt to load Spline if URL is provided and not in reduced-motion mode
  useEffect(() => {
    if (!splineSceneUrl || prefersReducedMotion) return;

    let isMounted = true;
    const loadSpline = async () => {
      try {
        const { Application } = await import('@splinetool/runtime');
        const canvas = canvasRef.current;
        if (canvas && isMounted) {
          const app = new Application(canvas);
          await app.load(splineSceneUrl);
          if (isMounted) setIsSplineLoaded(true);
        }
      } catch (err) {
        console.warn('Spline load error, falling back to procedural Canvas Orb:', err);
      }
    };

    loadSpline();
    return () => {
      isMounted = false;
    };
  }, [splineSceneUrl, prefersReducedMotion]);

  // Procedural 3D Canvas Knowledge Orb with rotating nodes and constellation lines
  useEffect(() => {
    // If Spline loaded successfully or reduced motion is true, canvas animation is handled differently
    if (isSplineLoaded || prefersReducedMotion) return;

    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationFrameId: number;
    let width = (canvas.width = canvas.parentElement?.clientWidth || 380);
    let height = (canvas.height = canvas.parentElement?.clientHeight || 340);

    const handleResize = () => {
      if (!canvas || !canvas.parentElement) return;
      width = canvas.width = canvas.parentElement.clientWidth;
      height = canvas.height = canvas.parentElement.clientHeight;
    };
    window.addEventListener('resize', handleResize);

    // Orbiting concept nodes
    const nodes = [
      { angle: 0, speed: 0.012, radiusX: 110, radiusY: 35, tilt: 0.35, size: 7, label: 'Limits', color: '#00F0FF' },
      { angle: 1.8, speed: -0.015, radiusX: 125, radiusY: 45, tilt: -0.4, size: 8, label: 'Derivatives', color: '#3B82F6' },
      { angle: 3.4, speed: 0.009, radiusX: 140, radiusY: 40, tilt: 0.2, size: 6, label: 'Continuity', color: '#38BDF8' },
      { angle: 4.9, speed: -0.011, radiusX: 115, radiusY: 30, tilt: -0.25, size: 6, label: 'Chain Rule', color: '#60A5FA' },
    ];

    // Constellation background particles
    const particles = Array.from({ length: 28 }, () => ({
      x: (Math.random() - 0.5) * 260,
      y: (Math.random() - 0.5) * 220,
      z: (Math.random() - 0.5) * 100,
      size: Math.random() * 2 + 1,
      alpha: Math.random() * 0.7 + 0.3,
    }));

    let mouseX = 0;
    let mouseY = 0;
    let targetMouseX = 0;
    let targetMouseY = 0;

    const handleMouseMove = (e: MouseEvent) => {
      if (!interactive || !containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      targetMouseX = ((e.clientX - rect.left) / rect.width - 0.5) * 30;
      targetMouseY = ((e.clientY - rect.top) / rect.height - 0.5) * 20;
    };

    const container = containerRef.current;
    if (container && interactive) {
      container.addEventListener('mousemove', handleMouseMove);
    }

    let time = 0;

    const render = () => {
      time += 0.02;
      mouseX += (targetMouseX - mouseX) * 0.08;
      mouseY += (targetMouseY - mouseY) * 0.08;

      ctx.clearRect(0, 0, width, height);

      const centerX = width / 2 + mouseX;
      const centerY = height / 2 + mouseY + Math.sin(time * 0.8) * 6; // gentle floating

      // 1. Core Knowledge Orb Outer Glow
      const glowGrad = ctx.createRadialGradient(centerX, centerY, 10, centerX, centerY, 110);
      glowGrad.addColorStop(0, 'rgba(0, 240, 255, 0.45)');
      glowGrad.addColorStop(0.4, 'rgba(37, 99, 235, 0.25)');
      glowGrad.addColorStop(0.8, 'rgba(15, 23, 42, 0.1)');
      glowGrad.addColorStop(1, 'rgba(11, 15, 25, 0)');
      ctx.fillStyle = glowGrad;
      ctx.beginPath();
      ctx.arc(centerX, centerY, 110, 0, Math.PI * 2);
      ctx.fill();

      // 2. Central Core Sphere
      const sphereGrad = ctx.createRadialGradient(
        centerX - 18,
        centerY - 18,
        5,
        centerX,
        centerY,
        48
      );
      sphereGrad.addColorStop(0, '#E0F2FE');
      sphereGrad.addColorStop(0.3, '#38BDF8');
      sphereGrad.addColorStop(0.7, '#1D4ED8');
      sphereGrad.addColorStop(1, '#0B0F19');

      ctx.save();
      ctx.shadowColor = '#00F0FF';
      ctx.shadowBlur = 24;
      ctx.fillStyle = sphereGrad;
      ctx.beginPath();
      ctx.arc(centerX, centerY, 44, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();

      // 3. Floating Latitudinal Rings
      ctx.strokeStyle = 'rgba(56, 189, 248, 0.35)';
      ctx.lineWidth = 1.5;

      // Equatorial ring
      ctx.beginPath();
      ctx.ellipse(centerX, centerY, 70, 24, Math.PI / 8, 0, Math.PI * 2);
      ctx.stroke();

      // Secondary tilted ring
      ctx.strokeStyle = 'rgba(37, 99, 235, 0.3)';
      ctx.beginPath();
      ctx.ellipse(centerX, centerY, 85, 28, -Math.PI / 6, 0, Math.PI * 2);
      ctx.stroke();

      // 4. Draw Orbiting Concept Nodes and Connection Rays
      nodes.forEach((node) => {
        node.angle += node.speed;

        // 3D perspective mapping
        const cosAngle = Math.cos(node.angle);
        const sinAngle = Math.sin(node.angle);

        const x = centerX + cosAngle * node.radiusX;
        const y = centerY + sinAngle * node.radiusY + cosAngle * node.radiusX * node.tilt;
        const zScale = 0.8 + (sinAngle + 1) * 0.25; // 0.8 to 1.3

        // Connection line to central knowledge core
        ctx.strokeStyle = `rgba(0, 240, 255, ${0.15 * zScale})`;
        ctx.lineWidth = 1;
        ctx.setLineDash([3, 4]);
        ctx.beginPath();
        ctx.moveTo(centerX, centerY);
        ctx.lineTo(x, y);
        ctx.stroke();
        ctx.setLineDash([]);

        // Node Glow
        ctx.save();
        ctx.shadowColor = node.color;
        ctx.shadowBlur = 14 * zScale;
        ctx.fillStyle = node.color;
        ctx.beginPath();
        ctx.arc(x, y, node.size * zScale, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();

        // Node label
        ctx.fillStyle = 'rgba(226, 232, 240, 0.9)';
        ctx.font = `${Math.round(10 * zScale)}px Inter, sans-serif`;
        ctx.textAlign = 'center';
        ctx.fillText(node.label, x, y - 10 * zScale);
      });

      // 5. Constellation micro-dots
      particles.forEach((p) => {
        const px = centerX + p.x + Math.sin(time + p.z) * 4;
        const py = centerY + p.y + Math.cos(time + p.x) * 4;
        ctx.fillStyle = `rgba(147, 197, 253, ${p.alpha * 0.6})`;
        ctx.beginPath();
        ctx.arc(px, py, p.size, 0, Math.PI * 2);
        ctx.fill();
      });

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener('resize', handleResize);
      if (container && interactive) {
        container.removeEventListener('mousemove', handleMouseMove);
      }
    };
  }, [isSplineLoaded, prefersReducedMotion, interactive]);

  return (
    <div
      ref={containerRef}
      className={`relative flex items-center justify-center overflow-hidden rounded-2xl select-none ${className}`}
      data-testid="knowledge-orb-container"
    >
      {/* Background ambient glow */}
      <div className="absolute inset-0 bg-radial-gradient from-cyan-500/10 via-electric-600/5 to-transparent pointer-events-none" />

      {/* Reduced-Motion Static Fallback */}
      {prefersReducedMotion ? (
        <div
          className="w-48 h-48 rounded-full bg-gradient-to-tr from-electric-700 via-cyan-500 to-electric-300 shadow-glow-cyan flex items-center justify-center relative p-1"
          data-testid="reduced-motion-orb"
        >
          <div className="w-full h-full rounded-full bg-background-card flex flex-col items-center justify-center text-center p-4 border border-cyan-400/30">
            <span className="text-2xl font-bold gradient-text-blue-cyan">AdeptCore</span>
            <span className="text-xs text-slate-400 mt-1">Knowledge Engine</span>
          </div>
        </div>
      ) : (
        <canvas
          ref={canvasRef}
          className="w-full h-full max-h-[380px] pointer-events-none"
          data-testid="knowledge-orb-canvas"
        />
      )}

      {/* Floating status badge */}
      <div className="absolute bottom-3 left-4 right-4 flex items-center justify-between text-[11px] text-slate-400 bg-background/80 backdrop-blur-md px-3 py-1.5 rounded-lg border border-slate-700/50 pointer-events-none">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
          <span className="font-medium text-slate-300">BKT Knowledge Graph</span>
        </div>
        <span className="text-cyan-300 font-mono">6 Concepts Connected</span>
      </div>
    </div>
  );
};
