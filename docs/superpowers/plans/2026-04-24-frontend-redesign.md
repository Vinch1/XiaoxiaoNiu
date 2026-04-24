# Frontend Redesign: Modern Dark Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the XiaoxiaoNiu frontend from Neon Cathedral to Modern Dark (Linear/Vercel aesthetic) while preserving all functionality.

**Architecture:** Full CSS rewrite + JSX cleanup. Two files changed: `styles.css` (complete replacement) and `App.jsx` (remove decorative elements, update copy). No functional changes.

**Tech Stack:** React 18, plain CSS with custom properties, Vite

---

### Task 1: Rewrite styles.css

**Files:**
- Rewrite: `Frontend/src/styles.css`

- [ ] **Step 1: Replace entire styles.css with Modern Dark design system**

Complete file replacement — new color tokens, typography, layout, components, and animations. All class names preserved for JSX compatibility.

- [ ] **Step 2: Commit**

```bash
git add Frontend/src/styles.css
git commit -m "style: rewrite CSS from Neon Cathedral to Modern Dark"
```

---

### Task 2: Clean up App.jsx

**Files:**
- Modify: `Frontend/src/App.jsx`

- [ ] **Step 1: Remove decorative HTML elements**

Remove from JSX:
- 4 background decoration divs (cathedral-vignette, cathedral-grain, ambient-left, ambient-right)
- Dropzone orbit spans (2x)
- Dropzone altar element with all children (ring-outer, ring-inner, core)
- Dropzone icon span (✦)
- Cow pin decorative spans: shadow, impact, 2x smoke, 3x spark (7 elements per cow)
- Empty stage altar with all children (3x rings, 2x columns, mark)
- Hero subtext paragraph

- [ ] **Step 2: Update copy text**

- Panel kickers: "Invocation"→"Upload", "Vision"→"Preview", "Revelation"→"Results"
- h2 headings: "Offer the Screenshot"→"Upload Screenshot", "The Board Appears"→"Board Preview", "Herd Ledger"→"Results"
- Status label: "Chamber"→"Status"
- Dropzone: icon→📤, "Choose a board image"→"Upload a screenshot", hint→"Supports PNG, JPG"
- Empty stage text: simplify to "Upload a screenshot to see the results."
- Empty list text: simplify to "No results yet."

- [ ] **Step 3: Commit**

```bash
git add Frontend/src/App.jsx
git commit -m "refactor: remove decorative elements and simplify copy"
```

---

### Task 3: Verify

- [ ] **Step 1: Run Vite build to check for errors**

```bash
cd Frontend && npm run build
```

Expected: Build succeeds with no errors.

- [ ] **Step 2: Start dev server and visually verify**

```bash
cd Frontend && npm run dev
```

Verify:
- Page loads with dark background, no decoration layers
- Upload button works, file picker opens
- Solve request works, cow pins appear with simplified animation
- Visit counter displays
- Status card shows correct states
- Responsive layout stacks at narrow widths
- Reset button clears state
