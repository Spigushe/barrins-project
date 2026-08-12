# Animating the stars — Landing-page visualization

Full handoff spec for every animated element on `/` (the landing banner). The current prototype implements all of this in `design_files/graph.jsx` (the node graph) and `design_files/app.jsx` (the full-screen starfield). Treat this document as the canonical reference for the implementation in `tolaria_news`.

The viz reads as both **arcane sigil** (concentric rings, glowing nodes) and **ML embedding space** (clustered points, similarity edges). The motion is the thing that sells it — without it, the SVG reads as static decoration.

---

## Two distinct populations of "stars"

| | Full-screen starfield | Graph constellation |
|---|---|---|
| **Where** | Fixed-position SVG covering the entire viewport, behind every element | Inside the 600×600 graph SVG, within the concentric rings |
| **Role** | Ambient atmosphere across the whole page | Focal data visualization (the embedding space) |
| **Count** | ~1 per 9,000px² (≈144 on 1440×900, cap 200) | 80 in production (range 20–160 via tweak) |
| **Size** | 0.4–1.5 px | 0.8–3.4 px (inner ring has bigger nodes) |
| **Pulse rate** | 0.8–3.2 Hz | 0.6–2.0 Hz |
| **Opacity range** | floor 0.05–0.23, ceiling 0.45–0.90 (per star) | floor 0.15–0.40, ceiling 0.75–1.00 (per node) |
| **Edges** | None | Sparse kNN, accent-colored |
| **Lives in** | `<Starfield>` (app.jsx) | `<NodeGraph>` (graph.jsx) |

---

## Layer stack inside the graph SVG (back-to-front)

1. **Ambient glow** — radial gradient at center, accent at 22% alpha → transparent. Static.
2. **Concentric guide rings** — 4 rings at r = 80, 150, 220, 280. **Each breathes its `stroke-opacity` independently** (see *Ring breathing* below).
3. **Outer tick ring** — 48 line segments at r ≈ 274, every 6th tick longer. **Rotates slowly** (see *Rotation*).
4. **Edges** — sparse nearest-neighbor lines, accent stroke, opacity = `0.08 + (1 - d/maxDist) × 0.35`. Light blur filter. Currently static; see *Optional extras*.
5. **Center halo** — radial-gradient circle r = 22. **Brightens and dims** subtly.
6. **Nodes** — circles, ink fill, r = 0.8–3.4 px. **Each twinkles** with its own floor/ceiling range. The load-bearing stars.
7. **Hero node** — 3.6r solid + 6.5r ring at center. The 6.5r ring **breathes its stroke-opacity**. Inner dot is static.
8. **Cardinal tick marks** — short lines at N/S/E/W, ink at 40% alpha. Static.

---

## Animation rules

All animations share a single `requestAnimationFrame` loop, a single time accumulator `t` (seconds since mount), and write via `setAttribute` for cheap GPU-batched updates. **No animation library required.**

### 1. Node twinkle + drift — graph constellation

Each node gets seeded twinkle AND positional drift parameters at mount:

```js
// Twinkle
n.floor      = 0.15 + r() * 0.25     // 0.15–0.40 — dim baseline
n.ceil       = 0.75 + r() * 0.25     // 0.75–1.00 — bright peak
n.pulseRate  = 0.6  + r() * 1.4      // 0.6–2.0 Hz
n.seed       = r()  * 1000
// Drift (per-axis so motion isn't a straight line)
n.driftAmpX  = 1.2 + r() * 2.4       // 1.2–3.6 px
n.driftAmpY  = 1.2 + r() * 2.4
n.driftRateX = 0.08 + r() * 0.10     // 0.08–0.18 Hz — full cycle 5–12s
n.driftRateY = 0.08 + r() * 0.10
n.driftSeedX = r() * 1000
n.driftSeedY = r() * 1000
```

Per frame:
```js
// Opacity
opacity = n.floor + (n.ceil - n.floor) * (0.5 + 0.5 * Math.sin(t * n.pulseRate + n.seed))
// Position offset from seeded base
dx = n.driftAmpX * Math.sin(t * n.driftRateX + n.driftSeedX)
dy = n.driftAmpY * Math.sin(t * n.driftRateY + n.driftSeedY)
el.setAttribute('cx', n.x + dx)
el.setAttribute('cy', n.y + dy)
```

**Independent X and Y axes** are non-negotiable — if you use a single drift rate the node traces a diagonal line back-and-forth, which reads mechanical. Independent rates give each node a tiny **Lissajous orbit**, which reads organic.

The **per-node floor/ceiling is non-negotiable**. Collapsing it to a single global range produces a uniform heartbeat that reads as boring — the constellation needs unequal stars.

### 2. Starfield twinkle + drift — full-screen ambient

Same math as node drift, wider envelope:

```js
s.floor      = 0.05 + r() * 0.18
s.ceil       = 0.45 + r() * 0.45
s.pulseRate  = 0.8  + r() * 2.4         // 0.8–3.2 Hz — faster twinkle
s.seed       = r() * 1000
s.driftAmpX  = 3 + r() * 9              // 3–12 px — wider drift
s.driftAmpY  = 3 + r() * 9
s.driftRateX = 0.05 + r() * 0.07        // 0.05–0.12 Hz — slower than nodes
s.driftRateY = 0.05 + r() * 0.07
```

The starfield is more dramatic (wider range, faster pulse, **wider drift**) because it lives in the periphery — atmosphere, not data. The graph is calmer (narrower range, slower pulse, **tighter drift**) because it's where the eye lands.

Drift amplitudes are deliberately small relative to inter-element distance — stars never collide or swap positions, they just shimmer slightly off their anchors.

Density:
```js
count = Math.min(200, Math.round((window.innerWidth * window.innerHeight) / 9000))
```

Recomputes on resize. Position seeds are stable for a given viewport size so resizing doesn't cause "the universe to reshuffle".

### 3. Ring breathing — concentric guide rings

Each of the 4 rings has its own slow rate and seed:

```js
ringAnim.rings = [
  { rate: 0.18, seed: 1.20, floor: 0.10, ceil: 0.22 },   // r=80
  { rate: 0.22, seed: 3.40, floor: 0.10, ceil: 0.22 },   // r=150
  { rate: 0.16, seed: 0.75, floor: 0.10, ceil: 0.22 },   // r=220
  { rate: 0.28, seed: 5.10, floor: 0.12, ceil: 0.24 },   // r=280
];
```

Per frame, animate `stroke-opacity` (not `opacity` — keeps the stroke-only behavior intact):

```js
ringEls.forEach((el, i) => {
  const p = ringAnim.rings[i];
  const range = p.ceil - p.floor;
  const v = p.floor + range * (0.5 + 0.5 * Math.sin(t * p.rate + p.seed));
  el.setAttribute('stroke-opacity', v.toFixed(3));
});
```

Rates are **deliberately slow** (0.16–0.28 Hz — full cycles every 3.5–6 seconds). The rings define the geometry of the composition; if they pulse too hard the center of gravity wobbles and the eye can't anchor.

### 4. Hero halo + ring — center brightness breathing

```js
ringAnim.halo     = { rate: 0.45, seed: 2.40, floor: 0.60, ceil: 1.00 };  // r=22 radial glow
ringAnim.heroRing = { rate: 0.55, seed: 4.10, floor: 0.40, ceil: 0.85 };  // r=6.5 thin ring
```

- The **halo** animates `opacity` (it's a fill).
- The **hero ring** animates `stroke-opacity` (it's a stroke).

Faster than the guide rings, slower than the nodes — calls attention to the center without becoming a strobe.

### 5. Outer tick ring rotation

```js
ring.setAttribute('transform', `rotate(${(t * 1.6).toFixed(2)} 300 300)`);
//                                          ↑ 1.6° per second
```

≈225 seconds per full revolution. Deliberately slow — subliminal motion. **Do not speed this up.**

### 6. Edges — follow the drift

The edges connect nodes; if nodes drift but edges stay anchored at original positions, you get a visual desync (lines floating near nodes instead of touching them). The rAF loop **rewrites each edge's `x1/y1/x2/y2`** so endpoints stick to their drifting nodes:

```js
// In JSX, every edge carries data-i / data-j indices into the nodes array.
edgeEls.forEach((el) => {
  const ni = nodes[+el.getAttribute('data-i')];
  const nj = nodes[+el.getAttribute('data-j')];
  // …compute dxi/dyi/dxj/dyj from each endpoint's drift params…
  el.setAttribute('x1', ni.x + dxi);
  el.setAttribute('y1', ni.y + dyi);
  el.setAttribute('x2', nj.x + dxj);
  el.setAttribute('y2', nj.y + dyj);
});
```

Opacity stays static (still distance-weighted from `nodes[].x/y` at render time — close enough since drift is small relative to edge length).

---

## Single `requestAnimationFrame` loop

```jsx
React.useEffect(() => {
  if (!motion) return undefined;
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return undefined;
  let last = performance.now();
  const tick = (now) => {
    const dt = (now - last) / 1000;
    last = now;
    tRef.current += dt;
    const svg = svgRef.current;
    if (svg) {
      const t = tRef.current;
      // (1) nodes
      svg.querySelectorAll('[data-pulse]').forEach((el, i) => { /* … */ });
      // (2) guide rings
      svg.querySelectorAll('[data-ring]').forEach((el, i) => { /* … */ });
      // (3) halo
      const halo = svg.querySelector('[data-halo]'); /* … */
      // (4) hero ring
      const heroRing = svg.querySelector('[data-herohalo]'); /* … */
      // (5) outer tick rotation
      const outer = svg.querySelector('[data-rotate]'); /* … */
    }
    rafRef.current = requestAnimationFrame(tick);
  };
  rafRef.current = requestAnimationFrame(tick);
  return () => cancelAnimationFrame(rafRef.current);
}, [motion, nodes, ringAnim]);
```

The full-screen `<Starfield>` runs its own independent rAF loop so its lifecycle is decoupled from the graph (resize handler, separate mount).

**Use `data-*` attributes**, not class names or refs-per-element — querying once per frame for ~85 elements is < 0.5ms and the code stays declarative in JSX.

---

## Reduced motion

**Respect `prefers-reduced-motion: reduce` everywhere.** When the user has it on:

- Skip the rAF loop entirely in both `<NodeGraph>` and `<Starfield>`.
- Set each animated element to its midpoint:
  - Nodes → `(floor + ceil) / 2`
  - Starfield stars → `(floor + ceil) / 2`
  - Guide rings → 0.18 (the original static value)
  - Halo → 0.9
  - Hero ring → 0.6
  - Outer tick ring → `rotate(0)`

```js
const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
if (reduceMotion) return;
```

The static composition still reads as a sigil — only the live feel is lost. **Do not** offer a UI toggle that overrides reduced motion; the OS-level preference is authoritative.

---

## Responsive behavior

- **Desktop (≥ 768px)**: full graph viz + full-screen starfield.
- **Tablet / mobile (< 768px)**: **graph viz hides entirely**. The hero headline + CTAs carry the page. The full-screen starfield stays — it's cheap and still reads at small sizes.

Don't try to scale the graph down for mobile; at small sizes the rings collide and the node count becomes illegible.

---

## Performance budget

| What | Target |
|---|---|
| Node count (production) | 80 |
| Full-screen starfield (1440×900) | ~144 |
| Full-screen starfield (cap) | 200 |
| Edges (computed) | ≤ 240 |
| rAF frame budget | < 3ms total on a 2020 MacBook |
| Initial paint impact | None (SVG inlined, no async load) |

If you blow the frame budget at high densities, two options before reaching for Canvas/WebGL:

1. **Batch by transform**: group nodes into a `<g>` per ring and animate a single attribute on the group. Loses per-node twinkle freedom.
2. **Throttle frame rate**: skip every other frame (effective 30fps). Sine math doesn't care; visually almost identical.

**Don't reach for WebGL.** The visual is simple enough that SVG + DOM rAF is fine to 300+ elements on any modern device. WebGL adds complexity without proportional benefit at this scale.

---

## Tweaks the design system exposes

Already wired into the prototype's Tweaks panel (`app.jsx`):

| Tweak | Default | Range | What it changes |
|---|---|---|---|
| `vizDensity` | 80 | 20–160 | Number of graph nodes |
| `vizStyle` | `graph` | `graph` / `constellation` | 3 rings + denser edges vs. 5 rings + sparser edges |
| `motion` | `true` | toggle | Kills the rAF loop for the graph (the starfield has its own independent loop and reduced-motion handling) |

Surface these in dev/QA builds only. **Production should ship a single configured composition** — the tweaks panel is a design-time tool.

---

## Porting from prototype to production

The prototype uses plain JSX + `requestAnimationFrame` + `setAttribute`. To port to `tolaria_news` (Vite + React + TypeScript):

1. **Lift the JSX as-is** into a `<NodeGraph />` component. No JSX changes needed.
2. **Type the node/star/ring parameter shapes** so the rAF loop's destructuring stays safe.
3. **Use `useRef` for the SVG and the rAF handle** — these survive re-renders cleanly. Don't drive frame state through `useState`.
4. **`useMemo` is the right tool** for the seeded position arrays (so they don't reshuffle on every render) but **don't `useMemo` the animation loop itself** — it goes in `useEffect`.
5. **Inline the SVG**. Don't lazy-load it; the file is < 4KB and is part of the first paint hero.

### When `barrins_api` exposes a real embedding endpoint

Replace the procedural node array with the API response:

1. `GET /api/embeddings/commanders` → `[{ id, name, x, y, ring, ... }]`
2. Use real `x`/`y` for positions; keep the polar logic only for the `ring` assignment if the API returns one.
3. Derive `floor` / `ceil` / `pulseRate` / `seed` from a **hash of the commander ID** so each commander always has the same twinkle signature across sessions.
4. **Edges should come from the API too** (kNN already computed server-side). Don't compute them client-side at scale.

The visual treatment (pulse, rings, edges, ticks, starfield) is data-agnostic — only the source of nodes changes.

---

## What NOT to do

- **Don't add shooting stars, comets, or particle trails.** The starfield twinkles in place; movement across the viewBox breaks the calm instrument feel.
- **Don't sync the twinkle rates.** All stars on the same period reads as a strobe; staggered seeds read as atmosphere.
- **Don't make the rotation faster than 2°/s.** It's load-bearing for the calm feel.
- **Don't make the rings pulse faster than 0.35 Hz.** They define the geometry; if they breathe too hard the center of gravity wobbles.
- **Don't unify the per-node / per-star opacity ranges into a global one.** The inconsistency *is* the design.
- **Don't tie pulse to mouse hover.** Tested — feels gimmicky and the viz is decorative, not interactive. The graph nodes are not clickable targets.
- **Don't drive any of this through React state.** `setState` on every frame for 200+ elements melts the reconciler. Imperative `setAttribute` is 50–100× cheaper and entirely appropriate for animation.
- **Don't replace SVG with Canvas before you've measured a real perf problem.** SVG handles this scene fine; only switch if profiling actually shows it.

---

## Files in the prototype

| File | Contains |
|---|---|
| `design_files/graph.jsx` | `<NodeGraph>` — concentric rings, nodes, edges, ticks, halo, hero ring, ring breathing |
| `design_files/app.jsx` | `<Starfield>` — full-screen ambient layer |
| `design_files/index.html` | Loads both as Babel JSX scripts |

Open `design_files/index.html` in a browser to see all animations live. The motion is much easier to evaluate in person than from screenshots.

---

## Inspiration / reference

The motion vocabulary is closer to **scientific-instrument dashboards** (telescope mounts, radar repeaters, oscilloscope persistence, observatory armillary spheres) than to particle systems. Think slow sweep, persistent glow, individual signal noise — not fireworks.
