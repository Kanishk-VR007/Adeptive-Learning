# Spline Web Reference Analysis & Reverse Engineering Report

**Target URL:** `https://spline.design/web`  
**Primary Framework:** Next.js + React + Three.js / Spline WebGL Canvas Engine  
**REA Provider:** `rea-cdp-browser` v2  
**REA Inspection Evidence ID:** `ev_6c397dd1dfb92f8918b9a7fe5cfe45d4cd6ab92c1804a869292556789e16997e`  
**REA Screenshot Evidence ID:** `ev_eaf9a17ea3d63b9dc18ab58d10c70662e5753e61781e5b2f673274a16852bc2b`  
**CDP Target ID:** `161E2A63E616ED3DED1DE5EF21EA3293`  
**Total DOM Nodes Analyzed:** 745 nodes  
**Audit Date:** October 31, 2026  

---

## 1. Executive Summary & Design Translation

This empirical reverse-engineering investigation examined Spline's dedicated web-capabilities landing page (`https://spline.design/web`) using the **Reverse Engineer Anything (REA)** MCP protocol connected to headless Google Chrome (`127.0.0.1:9222`).

The investigation focused on:
1. **Cinematic Hero Composition**: Staggered typography pairing with a full-depth, floating 3D WebGL canvas.
2. **Cursor & Motion Dynamics**: Mouse parallax tracking with spring deceleration ($f \approx 0.08$) and orbital camera inertia.
3. **Scroll-Driven Storytelling**: Spatial section pacing where text reveals sequentially from subtle opacity and vertical offsets (`translateY(35px) -> translateY(0px)`).
4. **Dark Obsidian Palette**: Hairline gradient borders (`rgba(255, 255, 255, 0.07)`), midnight navy background (`#080B11`), electric blue/cyan glow highlights, and high-readability sans-serif typography.

### AdeptLearn Pedagogical Translation
Spline's design language is synthesized into AdeptLearn's core educational message:
> *"An AI tutor that understands how you learn and adapts to help you master every concept."*  
> Tagline: *"Understand what you learn. Master what you know."*

---

## 2. In-Depth Element-Level Breakdown

### 2.1 Navigation Bar Architecture
- **DOM Landmark**: `<HEADER>` (node 107) with nested `<NAV>` (node 112) containing Radix UI menu collection items (`data-radix-collection-item`).
- **Styling**:
  - Sticky fixed header (`position: sticky; top: 0; z-index: 50`).
  - Frosted glassmorphism: `background: rgba(8, 11, 17, 0.85); backdrop-filter: blur(12px)`.
  - Border: Subtle hairline border `border-b border-white/[0.08]`.
  - Navigation links: Clean typography scale (`font-size: 14px`, `color: #94A3B8`, hover `color: #F8FAFC`).
  - Action CTA button: High-contrast pill button (`border-radius: 9999px`) with electric-blue glow and tactile press feedback.

### 2.2 Cinematic Hero Section
- **DOM Landmark**: `<SECTION>` (node 145) with flex/grid two-column split layout.
- **Left Column (Typography & Copy)**:
  - Headline (`<H1>` node 147): Two-line display typography with staggered gradient text (`bg-gradient-to-r from-blue-400 via-cyan-400 to-indigo-400 bg-clip-text text-transparent`).
  - Subtitle (`<P>` node 153): Supporting paragraph (`text-slate-400 font-normal leading-relaxed text-lg max-w-xl`).
  - Button Group (`DIV` node 160): Primary CTA (`Start Learning` with cyan hover aura) and Secondary CTA (`Explore How It Works` with glassmorphic slate border).
- **Right Column (3D Interactive Canvas)**:
  - `<CANVAS>` (node 168) with attributes `data-engine="three.js"`.
  - Non-blocking pointer event handling: cursor tracking computes normalized screen coordinates $[-1, 1]$ to apply rotational torque $(\theta_x, \theta_y)$ without freezing scroll or click interactions.

### 2.3 3D Lighting, Depth & Spatial Mechanics
- **Lighting Hierarchy**:
  - Key Light: Cool cyan directional light positioned at $(\text{top-left})$ illuminating the sphere facet.
  - Rim Light: Violet/purple point light behind the central orb creating a sharp rim silhouette (`#7C3AED`).
  - Ambient Light: Low-intensity deep navy ambient fill preventing pure black occlusion.
- **Orbital Node Mechanics**:
  - Satellites orbit the central Sol core along elliptical paths:
    $$x(t) = R_x \cos(\omega t + \phi), \quad y(t) = A_y \sin(2\omega t + \phi), \quad z(t) = R_z \sin(\omega t + \phi)$$
  - Satellites represent the 6 core pillars of AdeptLearn: *Diagnostic Assessment*, *Concept Mastery*, *Adaptive Questions*, *Misconception Detection*, *Spaced Repetition*, and *Learning Analytics*.

### 2.4 Scroll-Triggered Storytelling Architecture
- **Section Transition Pacing**:
  - Generous vertical whitespace (`padding: 120px 0`).
  - Initial state: elements configured at `opacity: 0; transform: translateY(35px)`.
  - Viewport entry trigger: Intersection Observer or GSAP ScrollTrigger reveals the heading first, followed by supporting copy at $+150\text{ms}$, and feature cards in a staggered cascade ($+100\text{ms}$ delay per card).
  - Accessibility: `prefers-reduced-motion` overrides translation and animation delays to `opacity: 1; transform: none; transition: none`.

---

## 3. Structural Comparison & Translation Plan

| Spline Element | Spline Web Implementation | AdeptLearn Landing Implementation |
| :--- | :--- | :--- |
| **Hero 3D Object** | Dynamic 3D interactive design scene | **3D Knowledge Galaxy** (Central Sol knowledge core surrounded by 6 educational satellite nodes with orbital physics) |
| **Color Palette** | Pure black (`#000000`) & metallic white | **Midnight Obsidian (`#080B11`)**, **Electric Blue (`#2563EB`)**, **Neon Cyan (`#00F0FF`)**, and **Violet Rim (`#7C3AED`)** |
| **Navigation** | App header with Radix dropdowns | Sticky glassmorphic navbar with smooth scroll links and direct auth routing |
| **Feature Pacing** | Alternating canvas & code viewports | **Scroll-Triggered Storytelling** + **Traditional vs AdeptLearn Comparison** + **How It Works 4-Step Pipeline** |
| **Interactive Demo** | WebGL editor controls | **AI Tutor Socratic Dialogue Simulator** (Ohm's Law misconception diagnostic walkthrough) |

---

## 4. Implementation Recommendations

1. **Lightweight Three.js / Procedural WebGL Canvas**:
   - Deliver 60 FPS performance on laptop and mobile GPUs with $< 2\text{ms}$ script execution time.
   - Zero external 3D asset download dependency (procedural geometry and shaders).
2. **Scroll-Driven Reveal Component (`ScrollReveal.tsx`)**:
   - Built on standard HTML5 `IntersectionObserver` with fallback for non-JS clients.
   - Respects `prefers-reduced-motion: reduce`.
3. **Route Separation & Preservation**:
   - Landing page mounted at `/` as the public showcase.
   - Existing student app preserved at `/dashboard`, `/learn`, `/progress`, `/revision`, `/profile`.
   - Seamless authentication transitions: `Sign In` navigates to login, `Get Started` navigates to register/dashboard.
