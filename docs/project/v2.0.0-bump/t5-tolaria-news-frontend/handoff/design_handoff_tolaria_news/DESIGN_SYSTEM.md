# Design System — tolaria_news

Pulled from the landing-banner prototype. Use these tokens as the foundation for every page.

## Color

### Themes

The prototype supports three themes; **Midnight is the default**. Twilight and Parchment are optional alternates.

#### Midnight (default — dark)
| Token | Value | Use |
|---|---|---|
| `--bg` | `#0B1220` | Page background |
| `--bg-2` | `#0E1830` | Secondary surfaces, gradient stops |
| `--ink` | `#F0EAD6` | Primary text, foreground |
| `--mute` | `rgba(240,234,214,0.62)` | Secondary text, labels |
| `--line` | `rgba(240,234,214,0.10)` | Borders, dividers, hairlines |

#### Twilight (dark alt)
| Token | Value |
|---|---|
| `--bg` | `#1A1230` |
| `--bg-2` | `#241844` |
| `--ink` | `#F4ECDB` |
| `--mute` | `rgba(244,236,219,0.62)` |
| `--line` | `rgba(244,236,219,0.10)` |

#### Parchment (light)
| Token | Value |
|---|---|
| `--bg` | `#F2EBD8` |
| `--bg-2` | `#E8DFC4` |
| `--ink` | `#1A1812` |
| `--mute` | `rgba(26,24,18,0.62)` |
| `--line` | `rgba(26,24,18,0.10)` |

### Accent

A single accent color drives CTAs, focus rings, the italic word in display headings, and the graph viz glow. Pick **one** for ship:

| Name | Hex | Vibe |
|---|---|---|
| **Teal (default)** | `#7BE0D6` | Calm, modern, scholarly |
| Gold | `#C7A455` | Warmer, more "library / archive" |
| Periwinkle | `#8FA8FF` | Cool, data-feel |
| Terracotta | `#E08A6A` | Warm, editorial |

### Selection
`::selection { background: #7BE0D6; color: #0B1220; }` — adapts with the chosen accent.

## Typography

### Stacks
```css
--font-serif: 'EB Garamond', 'Cormorant Garamond', Georgia, serif;
--font-sans:  'Geist', ui-sans-serif, system-ui, -apple-system, 'Segoe UI', sans-serif;
--font-mono:  'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, monospace;
```

Load from Google Fonts:
```html
<link href="https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,500;1,400;1,500&family=Geist:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet" />
```

### Scale

| Role | Family | Size | Weight | Line-height | Letter-spacing | Notes |
|---|---|---|---|---|---|---|
| Display (H1) | serif | `clamp(44px, 6.2vw, 88px)` | 400 | 0.98 | `-0.02em` | Use italic + accent color on the last word (or last 1–2 words) for flourish |
| H2 | serif | 40–56px | 400 | 1.0 | `-0.02em` | |
| H3 | serif | 28–32px | 400 | 1.1 | `-0.015em` | Section headers |
| Body | sans | 17px | 400 | 1.55 | normal | `text-wrap: pretty` |
| Body (small) | sans | 13.5–14.5px | 400/500 | 1.5 | `0.01em` | Nav links, captions |
| Stat number | serif | 28px | 400 | 1.0 | `-0.02em` | Used in the stats row |
| Eyebrow / chip | mono | 11px | 400 | 1.4 | `0.04em` | Often paired with a glowing accent dot |
| Telemetry label | mono | 9.5–10.5px | 400 | 1.4 | `0.08–0.1em`, **UPPERCASE** | Overlays on the graph viz |
| Button | sans | 14.5px | 500 | 1 | normal | |

## Spacing

Loose 8px base scale used in the prototype:
```
4 · 8 · 10 · 12 · 16 · 20 · 24 · 28 · 32 · 40 · 48 · 56 · 60 · 80
```

Page padding: `56px` horizontal at desktop, `24px` on mobile.
Max content width: `1440px`, centered.

## Radii

| Token | Value | Use |
|---|---|---|
| `--r-sm` | 6–7px | Form fields, chips |
| `--r-md` | 8–10px | Buttons |
| `--r-lg` | 14px | Cards, panels |
| `--r-pill` | 999px | Eyebrow chip, tags |

## Borders & lines

Use `0.5px` hairlines wherever a divider is needed (`border: 0.5px solid var(--line)`). The `--line` token is intentionally low-opacity so it reads as a whisper rather than a hard rule.

## Shadows / elevation

The midnight theme leans on **glow** rather than drop-shadow:
```css
/* CTA primary, default */
box-shadow: 0 6px 20px <accent>33, 0 0 0 0.5px <accent>;
/* CTA primary, hover */
box-shadow: 0 12px 36px <accent>55, 0 0 0 0.5px <accent>;
```
Avoid soft black drop-shadows on dark backgrounds — they don't read. On Parchment, switch to a true drop-shadow.

## Motion

- **Hover lift** on buttons and cards: `transform: translateY(-1px)`, `transition: transform .15s, background .15s, border-color .15s`
- **Link color** transitions: 150ms
- **Graph viz**: nodes pulse via opacity sine wave (rate 0.4–1.3 Hz, varied per node); outer tick ring rotates at 1.6°/s
- **Reduced motion**: respect `prefers-reduced-motion: reduce` — disable the viz animation and the rotating ring; keep static composition

## Components

### Sigil (logo mark)
24–28px circle group, original geometry: outer ring (12r), middle ring (7r), diamond (4 verts at NESW), center dot + halo. **Not the planeswalker symbol or any MTG mark.** Pair with the wordmark "Barrin's Project" set in italic serif.

### Nav
Horizontal flex, max-width 1440, padded 22×56. Logo + nav links + `⌘K` hint + Sign-in button. Link hover transitions ink color from `--mute` → `--ink`.

### Button — primary
- Background: `var(--accent)`
- Text: `#0B1220` (always the dark midnight color, regardless of theme — sits on a bright accent)
- Padding: `14px 22px`
- Radius: 10px
- Trailing arrow icon (12px)
- Glow shadow (see above)

### Button — secondary / ghost
- Background: transparent
- Border: `0.5px solid var(--line)`, brightens to ~35% opacity on hover
- Same dimensions as primary

### Eyebrow chip
- `display: inline-flex`, `gap: 10px`
- `padding: 6px 11px 6px 9px`
- `border: 0.5px solid var(--line)`
- `border-radius: 999px`
- Background: `rgba(255,255,255,0.03)` on dark, `rgba(255,255,255,0.45)` on parchment
- Leading 6×6 accent-colored dot with `box-shadow: 0 0 8px var(--accent)`
- Mono 11px, uppercase letter-spacing

### Stat block
Vertical stack:
- Number: serif, 28px, tight
- Label: 11px, `--mute`, `letter-spacing: 0.12em`, **UPPERCASE**

### Telemetry callout (graph overlays)
Stacked label:
- Eyebrow: mono 9.5px, `--mute`, UPPERCASE, prefixed with an em-dash in accent color
- Main: italic serif 18px, `--ink`

### Bottom rail
Fixed-bottom mono band, 10.5px, `--mute`, uppercase, `letter-spacing: 0.1em`. Three columns: brand context · scroll indicator · system status.

### Node graph (decorative)
600×600 SVG, three concentric guide rings, 48 tick marks on the outer ring (rotating), sparse edge graph between procedurally-placed nodes, halo behind the center node. Each node animates its opacity with a per-node sine wave. See `design_files/graph.jsx` for the full implementation — port it to a real component or rewrite using d3-force for live data.

## Background field

Three layered effects on the page background:
1. **Radial wash** — `radial-gradient(900px 600px at 18% 35%, <accent>1F, transparent 70%)` for emanation behind the headline
2. **Secondary radial** — `radial-gradient(700px 500px at 85% 70%, <bg-2>, transparent 65%)` for tonal variation
3. **SVG grain** — fractal-noise filter at 50% opacity, `mix-blend-mode: overlay` (dark) or `multiply` (light)
4. **Horizon hairline** — `top: 80px; height: 0.5px; background: var(--line)` — quietly establishes the band under the nav

## Accessibility

- Body text on Midnight bg: ink `#F0EAD6` on `#0B1220` — ratio ~13.5:1, AAA
- Muted text on Midnight bg: ~62% alpha ink — ratio ~8:1, AAA for body
- Accent `#7BE0D6` on `#0B1220` — ratio ~11:1, AAA
- Primary button: `#0B1220` on `#7BE0D6` — ratio ~11:1, AAA
- Verify any new accent choice against the same baseline.

## What NOT to use

- No emoji (the prototype is deliberately emoji-free)
- No drop-shadows on dark theme (use glow)
- No mana symbols, card frames, planeswalker symbols, or any WotC visual IP
- No SVG illustrations of characters or scenes — keep imagery abstract/geometric
