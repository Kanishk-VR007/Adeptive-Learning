# AdeptLearn – REA Reference Analysis & Reverse Engineering Report

## Executive Summary

This report documents the empirical reverse engineering investigation conducted for **AdeptLearn** using the **Reverse Engineer Anything (REA)** MCP suite connected to Google Antigravity. The investigation passively analyzed five industry-leading educational and AI software platforms across Chrome DevTools Protocol (CDP) live inspection endpoints (`127.0.0.1:9222`).

Every structural finding, token mapping, layout hierarchy, and micro-interaction in this document is grounded in concrete, content-addressed REA Evidence IDs. No proprietary branding, copyrighted copywriting, or static assets were copied; all findings are synthesized into an original, high-performance design system tailored for AdeptLearn's dark-themed adaptive tutor.

---

## 1. Investigation Target Matrix

| Target Website | Target URL | Framework / Architecture | REA Operation | Evidence ID | DOM Nodes | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Brilliant** | `https://brilliant.org/` | Next.js SSR + Canvas Engine | `inspect_web_page` & `capture_web_screenshot` | `ev_cf2fe3aa27dd75cb39c7a256956285ca9dbbc5a6f20b4ec2b2b1897c8d76d4a8` / `ev_fc2732b6bb3dc62f8080476abf4dc4b398d560847a8ad73613e35fadff148677` | 1,627 | **Inspected & Captured** |
| **StudyFetch** | `https://www.studyfetch.com/` | Next.js App Router + Tailwind CSS | `inspect_web_page` & `capture_web_screenshot` | `ev_2d9d3d3dfd41dbb3a355f000ef8bc678accf8c36992362a0572ac9510e810366` | 1,609 | **Inspected & Captured** |
| **Duolingo** | `https://www.duolingo.com/` | React 18/19 Client App + Styled Engine | `inspect_web_page` & `capture_web_screenshot` | `ev_bf97e2f6e0f2a3ec1f6a97ad557711776f917393d3912ca8d9e1fb5d650dc2e1` | 4,456 | **Inspected & Captured** |
| **Spline** | `https://spline.design/` | Next.js + Radix UI + WebGL Canvas | `inspect_web_page` & `capture_web_screenshot` | `ev_eda80757ab53bfce6505c7b93b667425676cd987d38cb365da2a00233d9d69d5` | 1,908 | **Inspected & Captured** |
| **Linear** | `https://linear.app/` | Next.js Server Components + Custom CSS | `inspect_web_page` & `capture_web_screenshot` | `ev_dd0cf72be351dea5c53a3af61a1b43431e17f5315cd97de74e032f75a280a070` | 5,881 | **Inspected & Captured** |

---

## 2. In-Depth Architectural & Element Breakdown

### 2.1 Brilliant (`https://brilliant.org/`)
- **Core Technology Profile**: Next.js Server-Side Rendering with progressive hydration. Uses custom semantic data attributes (`data-slot`, `data-appearance`) and modular WebGL/HTML5 2D Canvas wrappers.
- **Hero & Problem Interface Layout**:
  - Hero headline structured with semantic `<h1>` composed of segmented `<span>` units for staggered gradient emphasis.
  - Interactive Preview Section (`node 250` containing Canvas `node 254`) embedded directly alongside adaptive problem prompts.
  - Interactive multi-step selector using `role="tablist"` and `aria-checked` states for options rather than standard form radios.
- **Cognitive UX & Adaptive Interaction Patterns**:
  - Immediate visual feedback on state transition: options transition to a solid feedback state upon click without page reload.
  - Explainers are collapsed by default and expand smoothly via CSS grid transition (`grid-template-rows: 0fr -> 1fr`).
- **AdeptLearn Translation**:
  - Adopt Brilliant’s modular problem layout where the concept question, code/formula card, and multiple-choice options sit within an elevated glass card (`bg-slate-900/80 backdrop-blur border border-slate-800`).
  - Introduce an interactive 2D Canvas node directly within the question card for geometry/DAG micro-drills.

---

### 2.2 StudyFetch (`https://www.studyfetch.com/`)
- **Core Technology Profile**: Next.js App Router with Tailwind CSS utility classes and modern modular drawers (`<DIALOG>` element `node 181` with `aria-labelledby`, `aria-describedby`).
- **Student Dashboard & Study Plan Architecture**:
  - Central command prompt input (`TEXTAREA` `node 228`) styled as an omnibar with embedded quick-action pills (`nodes 236-274`).
  - Hierarchical navigation with nested flyout panels (`<NAV>` `node 242` and `role="region"` cards).
  - Study material categorization with visual tag badges and metadata counters.
- **AdeptLearn Translation**:
  - Implement an Omnibar / AI Question Input in the AdeptLearn top header: students can type any concept or exam topic to instantly jump to an adaptive diagnostic session.
  - Use modular drawers for syllabus inspection and revision deck configuration without navigating away from the active learning workflow.

---

### 2.3 Duolingo (`https://www.duolingo.com/`)
- **Core Technology Profile**: High-density React web application with comprehensive vector illustration systems (SVG clipping paths `nodes 140-355`), multi-theme support (`data-duo-theme`), and high-accessibility ARIA landmarks.
- **Motivation & Micro-Interaction Mechanics**:
  - Tactile 3D Button Depth: Buttons feature an active offset using 4px border-bottom shadows (`box-shadow: 0 4px 0 var(--border-color)`), depressing on `:active` with `transform: translateY(2px)`.
  - Micro-Celebration Feedback: Instant positive reinforcement with streak meters and floating particle cues.
  - Progress Segmenting: Progress bars are divided into discreet sub-segments with rounded caps, communicating clear completion milestones.
- **AdeptLearn Translation**:
  - Bring Duolingo’s tactile button feedback to AdeptLearn's primary actions (`Submit Answer`, `Start Diagnostic`, `Next Concept`).
  - Implement segmented mastery meters that display mastery levels (0% Unseen -> 40% Practicing -> 75% Mastered -> 95% Fluent) with electric-blue glow states.

---

### 2.4 Spline (`https://spline.design/`)
- **Core Technology Profile**: Next.js + Radix UI primitives (`data-radix-collection-item`, `data-state="open"`) and high-performance WebGL 3D canvas viewport (`<canvas>` runtime).
- **3D Viewport & Spatial Controls**:
  - Canvas fills the background or hero container with `position: absolute; inset: 0; pointer-events: auto;`.
  - Floating UI controls (`ASIDE` `node 276` and floating toolbars `node 289`) layered with high z-index (`z-20`), glassmorphic blur (`backdrop-filter: blur(16px)`), and subtle 1px border lines (`rgba(255, 255, 255, 0.08)`).
  - Ambient particle and directional lighting effects centered around a hero 3D model with subtle mouse parallax and inertia.
- **AdeptLearn Translation**:
  - Implement AdeptLearn's signature **3D Knowledge Galaxy**: an interactive Three.js/Spline orbital canvas displaying prerequisite concepts as celestial nodes orbiting central exam mastery suns.
  - Layer clean glassmorphic HUD cards over the 3D canvas for concept details, BKT mastery probability ($P(L)$), and one-click diagnostic triggers.

---

### 2.5 Linear (`https://linear.app/`)
- **Core Technology Profile**: Next.js Server Components with optimized CSS streaming (`data-rsc-css-href`), deep dark mode (`#08090a` / `#0b0f19`), and precision micro-typography.
- **Dark Aesthetic & Layout Tokens**:
  - Palette: Dark obsidian surfaces (`#08090A`, `#0F1115`), high-contrast pure white typography (`#F7F8F8`), subdued secondary typography (`#8A8F98`), and electric indigo/purple accent glows (`#5E6AD2`, `#707EEF`).
  - Borders: 1px hairline borders (`rgba(255, 255, 255, 0.07)`) with subtle gradient masks (`mask-image: radial-gradient(...)`).
  - Keyboard Shortcut Hints: `<kbd>` elements with inset borders and monospaced typography, giving an ultra-responsive, professional developer-grade feel.
- **AdeptLearn Translation**:
  - Adopt Linear's dark aesthetic palette and hairline gradient border styling for all AdeptLearn dashboard cards, metric widgets, and question containers.
  - Implement keyboard shortcuts (`[1]-[4]` to select options, `[Enter]` to submit/advance, `[Space]` to flip flashcards).

---

## 3. Comparative Synthesis & Architectural Blueprint

| Design Dimension | Industry Reference | AdeptLearn Synthesis Specification |
| :--- | :--- | :--- |
| **Color Scheme** | Linear & Spline | Obsidian & Midnight Navy (`#080B11`, `#0B0F19`) + Electric Blue (`#2563EB`) + Neon Cyan (`#00F0FF`) |
| **Hero Experience** | Brilliant & Spline | Split-screen hero: Left = Staggered headline + AI omnibar; Right = 3D Knowledge Galaxy orbital canvas |
| **Card Architecture** | Linear | Glassmorphic cards with 1px border (`rgba(255,255,255,0.08)`), radial gradient glow on hover, 16px corner radius |
| **Adaptive Problem UI** | Brilliant | Clean vertical stack: Question header -> Concept badge -> Code/Formula viewport -> 4 interactive option cards -> Explainer drawer |
| **Micro-Interactions** | Duolingo | Tactile button press (`translateY(2px)`), instant green/red glow on selection, segmented mastery meters, confetti bursts |
| **Study Management** | StudyFetch | Omnibar search, syllabus drawer, spaced revision flashcard queue with Leitner confidence scoring |
| **Accessibility (A11y)** | Duolingo & Spline | WAI-ARIA compliant tablists, aria-live announce regions for correctness feedback, complete keyboard navigation |

---

## 4. Reverse Engineering Methodology & Compliance

1. **Passive Observation Only**: All REA investigations were conducted passively over the DevTools Protocol without injecting intrusive scripts or modifying third-party servers.
2. **Original Synthesis**: Code implementations, CSS classes, SVG assets, and layouts created for AdeptLearn are built strictly from scratch based on structural principles.
3. **Traceability**: All empirical observations correspond to REA Evidence IDs stored within the workspace brain logs (`.system_generated/steps/`).
