# AdeptLearn – Complete Frontend Design System Specification

## 1. Design Vision & Philosophy

**AdeptLearn** is a next-generation adaptive exam-preparation platform designed to deliver deep cognitive engagement. Informed by empirical reverse engineering of world-class educational and developer platforms (Brilliant, StudyFetch, Duolingo, Spline, Linear), the AdeptLearn interface combines:
1. **Linear's Pristine Dark Aesthetic**: Hairline borders, obsidian surfaces, and zero-clutter information architecture.
2. **Brilliant's Cognitive Clarity**: Focused problem layouts with embedded formula viewports and instant modular explanations.
3. **Duolingo's Motivational Energy**: Tactile button feedback, micro-celebrations, streak counters, and segmented mastery bars.
4. **Spline's Spatial Immersion**: An interactive **3D Knowledge Galaxy** that turns abstract dependency graphs into an exploratory celestial space.

---

## 2. Design Tokens

### 2.1 Color Palette

```css
:root {
  /* Surface Layers (Deep Obsidian & Midnight Navy) */
  --bg-primary: #080B11;          /* Base canvas background */
  --bg-secondary: #0B0F19;        /* Main card & container background */
  --bg-surface: #111827;          /* Elevated surface & dropdowns */
  --bg-surface-elevated: #1E293B; /* Active selection / hover layer */
  --bg-surface-glass: rgba(11, 15, 25, 0.75); /* Glassmorphism backdrop */

  /* Hairline Borders */
  --border-subtle: rgba(255, 255, 255, 0.07);
  --border-medium: rgba(255, 255, 255, 0.12);
  --border-highlight: rgba(0, 240, 255, 0.35);

  /* Primary Brand Accents */
  --accent-electric: #2563EB;     /* Electric Blue - Primary Actions */
  --accent-electric-hover: #1D4ED8;
  --accent-cyan: #00F0FF;         /* Neon Cyan - Interactive Highlights */
  --accent-cyan-glow: rgba(0, 240, 255, 0.25);
  --accent-purple: #7C3AED;       /* Prerequisite Bridge Violet */

  /* Semantic Feedback States */
  --success-emerald: #10B981;     /* Correct Answer / Mastered State */
  --success-glow: rgba(16, 185, 129, 0.25);
  --warning-amber: #F59E0B;       /* Review Needed / High Slip Risk */
  --warning-glow: rgba(245, 158, 11, 0.25);
  --error-rose: #EF4444;          /* Incorrect Answer / Remediation */
  --error-glow: rgba(239, 68, 68, 0.25);

  /* Typography Hierarchy */
  --text-primary: #F8FAFC;        /* 100% High Contrast Text */
  --text-secondary: #94A3B8;      /* Supporting Labels & Explanations */
  --text-muted: #64748B;          /* Metadata, Hotkeys, Footnotes */
  --text-cyan: #38BDF8;           /* Concept Tags & Formula Variables */
}
```

### 2.2 Typography Scale

AdeptLearn pairs modern geometric sans **Plus Jakarta Sans / Inter** for UI clarity with **JetBrains Mono** for algorithmic and mathematical formulas.

| Token | Size | Weight | Line Height | Letter Spacing | Usage |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `font-display` | `3.25rem` (52px) | Bold (700) | `1.1` | `-0.03em` | Hero Headline |
| `font-h1` | `2.25rem` (36px) | SemiBold (600) | `1.2` | `-0.02em` | Section Titles, Modal Headers |
| `font-h2` | `1.75rem` (28px) | SemiBold (600) | `1.25` | `-0.015em` | Card Headers, Problem Prompt |
| `font-h3` | `1.25rem` (20px) | Medium (500) | `1.35` | `-0.01em` | Question Options, Node Labels |
| `font-body` | `1.0rem` (16px) | Regular (400) | `1.5` | `0` | Primary Body, Explanations |
| `font-small` | `0.875rem` (14px) | Regular (400) | `1.4` | `0.005em` | Metadata, Tags, Badges |
| `font-caption` | `0.75rem` (12px) | Medium (500) | `1.3` | `0.02em` | Hotkey Hints (`kbd`), Mastery Stats |
| `font-mono` | `0.9375rem` (15px) | Regular (400) | `1.45` | `0` | Code Snippets, LaTeX Math, Formulas |

---

## 3. Core Component Specifications

### 3.1 Header & AI Omnibar
- **Location**: Fixed top navigation bar (`h-16 border-b border-white/[0.07] bg-slate-950/80 backdrop-blur-xl z-50`).
- **Elements**:
  - Left: Logo icon with cyan orbital ring + "AdeptLearn" wordmark.
  - Center: **AI Omnibar** (`w-96 bg-slate-900/90 border border-slate-800 rounded-full px-4 py-1.5 flex items-center justify-between text-sm text-slate-400 hover:border-blue-500/50 transition-colors`).
    - Hotkey badge `<kbd class="px-1.5 py-0.5 text-xs bg-slate-800 rounded border border-slate-700 text-slate-300">⌘K</kbd>`.
  - Right:
    - Daily Streak counter (`🔥 7 Days` with amber flame glow).
    - Mastery Index pill (`⚡ 84% Exam Ready`).
    - Profile avatar with active diagnostic status indicator.

### 3.2 Split-Screen Hero with 3D Knowledge Galaxy
- **Layout**: 2-column grid (`grid-cols-1 lg:grid-cols-12 gap-8 py-12 items-center`).
- **Left Column (Col 1-7)**:
  - Pill Tag: `⚡ BKT-Powered Exam Readiness Engine`.
  - Main Headline: "Master Complex Exams Through **Adaptive Intelligence**."
  - Subtitle: "Dynamic Bayesian Knowledge Tracing diagnoses your weaknesses in real time, serving precision drills and automated spaced revision."
  - Primary Action Group:
    - Primary Button: `Start Diagnostic Test` (Tactile Electric-Blue with glow).
    - Secondary Button: `Explore Knowledge DAG` (Glass border with cyan arrow).
  - Quick Metrics Strip: Total syllabus coverage, average diagnostic time, mastery acceleration multiplier.
- **Right Column (Col 8-12)**:
  - **3D Knowledge Galaxy Canvas Container**:
    - Aspect ratio: `4/3` on desktop, interactive Three.js/Spline viewport with dark spatial ambient lighting.
    - Central Sun: Active syllabus target (e.g., "Machine Learning Exam").
    - Orbital Nodes: Sub-concepts color-coded by mastery probability ($P(L)$):
      - Green ($P(L) \ge 0.75$): Mastered concept.
      - Amber ($0.40 \le P(L) < 0.75$): In practice / high slip risk.
      - Cyan / Unfilled ($P(L) < 0.40$): Prerequisite gap.
    - Hover Card HUD: Floating glass tag displaying concept name, estimated mastery time, and direct drill trigger.

### 3.3 Adaptive Question Interface
- **Layout**: Focused cognitive card container (`max-w-3xl mx-auto space-y-6`).
- **Header**:
  - Concept Breadcrumb: `Calculus II > Integration Techniques > By Parts`.
  - Difficulty Badge: `Level: Adaptive (θ = +1.4)`.
  - Progress Sub-Segments: 4-step segmented bar with active progress indicator.
- **Question Body**:
  - Clear H2 text prompt with math rendering support ($LaTeX$ via KaTeX).
  - Code/Formula Viewport: Syntax-highlighted snippet inside dark inset card (`bg-slate-950/80 border border-slate-800/80 rounded-xl p-4 font-mono`).
- **Interactive Option Stack**:
  - 4 vertical option cards (`grid gap-3.5`).
  - Option index pill (`A`, `B`, `C`, `D` or hotkeys `1`, `2`, `3`, `4`).
  - Click feedback: Transitions smoothly through selection, evaluation, and explanation phases.
- **Instant Explainer Drawer**:
  - Expands automatically post-answer submission.
  - Contains **Why this is correct / incorrect**, key underlying theorem, and recommended follow-up concept.

### 3.4 Spaced Revision Deck (Leitner 5-Box System)
- **Concept**: Flashcards scheduled via adaptive spaced repetition.
- **Card Mechanics**:
  - 3D Flip Card with front (Prompt / Formula) and back (Full Derivation / Explanation).
  - Spacebar or click-to-flip trigger.
  - Confidence Rating Actions:
    - `Again (< 1 Day)` (Rose)
    - `Hard (2 Days)` (Amber)
    - `Good (4 Days)` (Blue)
    - `Easy (7 Days)` (Emerald)
  - Visual Leitner Box progression indicator showing cards migrating between Box 1 (Daily) and Box 5 (Mastered).

---

## 4. Sprint-Ready Element Implementation Plan

The following component suite will be integrated into the existing `frontend/src/` architecture:

```
frontend/src/
├── components/
│   ├── ui/
│   │   ├── Button.tsx            # Enhanced with tactile 3D bottom bevel
│   │   ├── Card.tsx              # Enhanced with hairline gradient borders
│   │   ├── Badge.tsx             # Semantic mastery & difficulty pills
│   │   └── Omnibar.tsx           # StudyFetch-style command bar with hotkeys
│   ├── galaxy/
│   │   ├── KnowledgeGalaxy.tsx   # Three.js 3D orbital concept graph canvas
│   │   └── GalaxyNodeHUD.tsx     # Floating glassmorphic concept inspector
│   ├── tutor/
│   │   ├── AdaptiveQuestionCard.tsx # Brilliant-style question & option stack
│   │   ├── ExplainerDrawer.tsx   # Animated cognitive step-by-step explainer
│   │   └── SegmentedProgressBar.tsx # Duolingo-style milestone progress bar
│   └── revision/
│       ├── SpacedFlashcardDeck.tsx # 3D perspective flip card revision deck
│       └── LeitnerBoxTracker.tsx # 5-stage Leitner spaced repetition visualizer
```

---

## 5. Verification & Quality Standards

- **Zero Layout Shifts (CLS < 0.05)**: All dynamic drawers, explainer reveals, and 3D canvases use explicit aspect-ratio and grid-template dimension reservations.
- **High Frame Rates (60 FPS minimum)**: 3D orbital calculations run in a `requestAnimationFrame` loop optimized with object pooling, avoiding garbage collection spikes.
- **Full Keyboard Operability**: Complete compliance with W3C WAI-ARIA authoring practices for interactive widgets, dialogs, and learning drills.
