# Frontend Redesign: Modern Dark

## Context

The current frontend uses a "Neon Cathedral" aesthetic — heavy glassmorphism, spinning ring decorations, 14 keyframe animations, 4 decorative background layers, and ceremonial copy. The user wants a complete visual overhaul to a Modern Dark style (Linear/Vercel) while preserving all functionality.

## Scope

- **Files modified:** `Frontend/src/App.jsx` (markup cleanup), `Frontend/src/styles.css` (full rewrite)
- **Not modified:** Backend, API contracts, `main.jsx`, `vite.config.js`, `package.json`
- **Functional behavior preserved:** File upload, solve request, cow overlay with normalized positioning, visit counter, status states, reset, responsive layout

## Design Decisions

### Color System

| Token | Value | Usage |
|-------|-------|-------|
| `--bg` | `#09090b` | Page background |
| `--panel` | `rgba(255,255,255,0.03)` | Card/panel background |
| `--panel-hover` | `rgba(255,255,255,0.05)` | Hover state |
| `--border` | `rgba(255,255,255,0.06)` | Panel/card borders |
| `--text` | `#fafafa` | Primary text |
| `--text-secondary` | `#a1a1aa` | Secondary text |
| `--text-tertiary` | `#71717a` | Labels, hints |
| `--accent` | `#a78bfa` | Primary accent (buttons, highlights) |
| `--accent-hover` | `#8b5cf6` | Button hover |
| `--success` | `#34d399` | Success state |
| `--error` | `#f87171` | Error state |

Background: pure `#09090b` with one subtle radial gradient at the top center (`rgba(167,139,250,0.06)` fading to transparent). No vignette, no grain, no ambient blurs, no `body::before`.

### Typography

- Font stack: `Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`
- Monospace: `ui-monospace, SFMono-Regular, monospace`
- Remove Fraunces and IBM Plex Mono
- h1: `clamp(2.4rem, 4vw, 3.6rem)`, weight 700, line-height 1.1
- h2: `clamp(1.5rem, 2.5vw, 2rem)`, weight 600, line-height 1.15
- Body: 1rem/400, line-height 1.6
- Labels: 0.75rem monospace, uppercase, 0.05em letter-spacing

### Layout

- Three-column grid preserved
- Gap: `32px` (was 24px)
- Panel `border-radius`: `16px` (was 30px)
- Panel styling: `background: var(--panel)` + `border: 1px solid var(--border)`, no backdrop-filter, no ::before gloss, no stacked box-shadows
- Single subtle shadow on panels: `0 1px 3px rgba(0,0,0,0.3)`

### Components

**Hero:**
- Single row: emoji + brand name + visit counter
- One h1 headline + one line of description
- Remove subtext paragraph

**Dropzone:**
- Remove all decorative children (orbits, altar rings, ✦ icon)
- Dashed border, centered upload icon, file name, one hint line
- Hover: border solidifies + slight purple tint

**Buttons:**
- Primary: solid `var(--accent)` fill, white text, `border-radius: 10px`
- Secondary: transparent + border, `border-radius: 10px`
- Hover: darken/lighten, no translate, no glow
- Disabled: opacity 0.4

**Status Card:**
- Remove ::before gloss
- Left 3px border stripe for status color (idle=transparent, loading=accent, success=green, error=red)

**Metric Cards:**
- Transparent background, no border
- Large number (tabular-nums) + small label

**Cow Pin Animation (simplified):**
- Keep: cow emoji drop + coordinate tag fade-in
- Remove: shadow, impact wave, 2x smoke, 3x spark elements
- Animation: 600ms (was 1200ms), simplified bounce without rotation
- Stagger preserved

**Empty Stage:**
- Remove spinning altar, rings, columns, "牧" character
- Simple: muted icon + one line of text

**Herd Ledger:**
- Row hover: border brighten + background tint, no translateX
- "Pinned" chip → small dot + text

**Visit Counter:**
- Remove all pseudo-element animations (sheen, storm, thunder)
- Keep: scale pulse on count change, 200ms

**Entrance Animation:**
- Keep `reveal-up`, reduce to 500ms (was 820ms)

### HTML Changes (App.jsx)

Remove from JSX:
- `<div className="cathedral-vignette">`
- `<div className="cathedral-grain">`
- `<div className="ambient ambient-left">`
- `<div className="ambient ambient-right">`
- Dropzone orbit spans (`.dropzone-orbit`)
- Dropzone altar spans (`.dropzone-altar` and children)
- Cow pin shadow, impact, smoke, spark spans (7 per cow)
- Empty stage altar (rings, columns, mark)
- Hero subtext paragraph
- Dropzone icon span (✦)

Simplify copy:
- Panel kickers: "Upload" / "Preview" / "Results" (was "Invocation" / "Vision" / "Revelation")
- h2 headings: "Upload Screenshot" / "Board Preview" / "Results" (was "Offer the Screenshot" / "The Board Appears" / "Herd Ledger")
- Status label: "Status" (was "Chamber")
- Dropzone: "Upload a screenshot" / "Supports PNG, JPG"

### Responsive

- Breakpoints unchanged (1220px, 860px)
- Same stacking behavior
- Reduced border-radius at small screens: `12px` (was 24px)

### Animations Summary

Keep (simplified):
- `reveal-up` — 500ms entrance
- `pin-drop` — 600ms simplified bounce
- `cow-tag-settle` — 600ms fade-in
- `visit-counter-pulse` — 200ms scale

Remove:
- `altar-spin`, `altar-spin-reverse`
- `cow-shadow-land`, `cow-impact-wave`
- `cow-smoke-back`, `cow-smoke-front`
- `cow-spark-left`, `cow-spark-right`, `cow-spark-center`
- `visit-counter-sheen`, `visit-counter-storm`, `visit-counter-thunder`

## Implementation Notes

- CSS is a full rewrite, not incremental edits
- App.jsx changes are deletions of decorative elements and copy updates
- No new dependencies
- No functional behavior changes
