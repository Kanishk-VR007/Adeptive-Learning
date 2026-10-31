# AdeptLearn – REA Animation & Micro-Interaction Specification

## Executive Summary

This specification establishes the motion design system for **AdeptLearn**. Synthesizing empirical findings from REA observations of Duolingo (tactile motivation), Spline (3D spatial physics), Brilliant (step-by-step cognitive reveals), and Linear (snappy, low-latency UI transitions), this document provides mathematical timing curves, CSS keyframe definitions, and 3D canvas interaction algorithms.

---

## 1. Core Timing Curves & Physics Tokens

AdeptLearn utilizes a dual motion system: **cubic-bezier curves** for UI interface elements and **spring physics / continuous orbital mechanics** for 3D visualizations and interactive cards.

### 1.1 Easing Curves

```css
:root {
  /* Standard smooth transition for color, border, and opacity */
  --ease-standard: cubic-bezier(0.2, 0.0, 0.0, 1.0);
  
  /* Snappy entrance for modals, flyouts, and dropdowns (Linear style) */
  --ease-enter: cubic-bezier(0.16, 1, 0.3, 1);
  
  /* Acceleration curve for dismissals and exits */
  --ease-exit: cubic-bezier(0.7, 0, 0.84, 0);
  
  /* Tactile bouncy curve for celebratory badges and score increments (Duolingo style) */
  --ease-bounce: cubic-bezier(0.34, 1.56, 0.64, 1);
  
  /* Smooth deceleration for scroll reveals and card transitions */
  --ease-decelerate: cubic-bezier(0.0, 0.0, 0.2, 1);

  /* Duration Tokens */
  --duration-instant: 100ms;
  --duration-fast: 200ms;
  --duration-base: 300ms;
  --duration-slow: 500ms;
  --duration-cinematic: 800ms;
}
```

---

## 2. Micro-Interactions & Component Behaviors

### 2.1 Tactile Button Press (Duolingo Inspired)
Primary action buttons (`Submit Answer`, `Start Diagnostic`, `Continue`) feature a tactile pseudo-3D bottom bevel that depresses upon user click.

```css
.btn-tactile-primary {
  background: linear-gradient(180deg, #2563EB 0%, #1D4ED8 100%);
  border: 1px solid rgba(255, 255, 255, 0.15);
  box-shadow: 0 4px 0 #1E40AF, 0 8px 16px rgba(37, 99, 235, 0.25);
  transition: transform var(--duration-instant) var(--ease-standard),
              box-shadow var(--duration-instant) var(--ease-standard);
}

.btn-tactile-primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 5px 0 #1E40AF, 0 12px 20px rgba(37, 99, 235, 0.35);
}

.btn-tactile-primary:active {
  transform: translateY(3px);
  box-shadow: 0 1px 0 #1E40AF, 0 2px 4px rgba(37, 99, 235, 0.2);
}
```

### 2.2 Question Option Card Selection
Option cards in the diagnostic and practice modes undergo a three-stage state lifecycle: **Idle -> Hover/Selected -> Evaluation (Correct/Incorrect)**.

- **Hover State**: Elevates by 2px, border transitions to electric blue (`#2563EB`), subtle radial background glow activates.
- **Selected State**: Border intensifies to neon cyan (`#00F0FF`), background tints with `rgba(0, 240, 255, 0.06)`.
- **Correct State**: Border transitions to emerald (`#10B981`), emits a soft 12px box-shadow glow, icon triggers celebratory checkmark scale-in.
- **Incorrect State**: Gentle 4px horizontal shake animation (duration 350ms), border changes to crimson rose (`#EF4444`).

```css
@keyframes shake-gentle {
  0%, 100% { transform: translateX(0); }
  20%, 60% { transform: translateX(-4px); }
  40%, 80% { transform: translateX(4px); }
}

.option-card-incorrect {
  animation: shake-gentle 350ms var(--ease-bounce);
  border-color: #EF4444 !important;
  background-color: rgba(239, 68, 68, 0.08) !important;
}

.option-card-correct {
  animation: pulse-glow 600ms var(--ease-enter);
  border-color: #10B981 !important;
  background-color: rgba(16, 185, 129, 0.08) !important;
  box-shadow: 0 0 24px rgba(16, 185, 129, 0.25);
}

@keyframes pulse-glow {
  0% { transform: scale(1); }
  50% { transform: scale(1.02); }
  100% { transform: scale(1); }
}
```

---

## 3. 3D Knowledge Galaxy Orbital Physics (Spline Inspired)

The flagship 3D visualization represents knowledge concepts as celestial bodies orbiting around subject mastery cores.

```
       [Central Exam Core: Sol]
               /       \
      (Orbit 1)         (Orbit 2)
       /                     \
[Linear Algebra]        [Calculus]
       |                     |
 (P(L) = 0.85)          (P(L) = 0.42)
  [Glowing Cyan]         [Subtle Amber]
```

### 3.1 Mathematical Orbit Formulation

Each concept node position $P_i(t) = (x_i, y_i, z_i)$ at time $t$ is calculated via:

$$x_i(t) = R_i \cdot \cos(\omega_i \cdot t + \phi_i)$$
$$y_i(t) = A_i \cdot \sin(2 \cdot (\omega_i \cdot t + \phi_i))$$
$$z_i(t) = R_i \cdot \sin(\omega_i \cdot t + \phi_i)$$

Where:
- $R_i$: Radius of the orbital layer (120px to 360px depending on prerequisite depth).
- $\omega_i$: Angular velocity (inversely proportional to radius: $\omega_i = \frac{k}{\sqrt{R_i}}$ for Keplerian fidelity).
- $\phi_i$: Initial phase offset to prevent visual clustering.
- $A_i$: Vertical oscillation amplitude (15px to 30px) for realistic 3D volumetric depth.

### 3.2 Interactive Raycasting & Hover Mechanics
1. **Raycaster Detection**: On mouse movement over the `<canvas>`, a Three.js raycaster tests intersection against node mesh bounding spheres.
2. **Magnification Transition**: Hovered nodes smoothly interpolate scale from $1.0 \times$ to $1.35 \times$ over 180ms using linear interpolation:
   $$S_{t+1} = S_t + (S_{\text{target}} - S_t) \cdot 0.15$$
3. **Orbital Glow Shader**: Hovered nodes trigger a fragment shader intensity multiplier from $1.0$ to $2.5$, illuminating connecting prerequisite edges with animated pulse particles.
4. **Camera Inertia & Parallax**: Mouse offset from screen center $(dx, dy)$ imparts subtle camera pan rotation:
   $$\text{Camera.rotation.y} = dx \cdot 0.0004$$
   $$\text{Camera.rotation.x} = -dy \cdot 0.0004$$

---

## 4. Spaced Revision Flashcard 3D Flip Physics

The revision deck utilizes a 3D perspective card flip simulating real card physics:

```css
.flashcard-perspective-container {
  perspective: 1200px;
}

.flashcard-inner {
  position: relative;
  width: 100%;
  height: 100%;
  transform-style: preserve-3d;
  transition: transform var(--duration-slow) var(--ease-enter);
}

.flashcard-inner.is-flipped {
  transform: rotateY(180deg);
}

.flashcard-face {
  position: absolute;
  inset: 0;
  backface-visibility: hidden;
  -webkit-backface-visibility: hidden;
  border-radius: 1rem;
}

.flashcard-back {
  transform: rotateY(180deg);
}
```

---

## 5. Staggered List & Content Entrance

For syllabus chapters, diagnostic results, and study plan recommendations, list items enter in a coordinated cascade (Linear style):

```css
.stagger-item {
  opacity: 0;
  transform: translateY(12px);
  animation: stagger-in var(--duration-base) var(--ease-enter) forwards;
}

.stagger-item:nth-child(1) { animation-delay: 40ms; }
.stagger-item:nth-child(2) { animation-delay: 80ms; }
.stagger-item:nth-child(3) { animation-delay: 120ms; }
.stagger-item:nth-child(4) { animation-delay: 160ms; }
.stagger-item:nth-child(5) { animation-delay: 200ms; }
.stagger-item:nth-child(6) { animation-delay: 240ms; }

@keyframes stagger-in {
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
```

---

## 6. Accessibility & Reduced Motion Compliance

In accordance with W3C WCAG 2.2 Level AA:

```css
@media (prefers-reduced-motion: reduce) {
  *, ::before, ::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
  
  .flashcard-inner {
    transition: none !important;
  }
  
  /* 3D Knowledge Galaxy halts continuous orbital rotation; displays static layout */
  .galaxy-canvas {
    animation: none !important;
  }
}
```
