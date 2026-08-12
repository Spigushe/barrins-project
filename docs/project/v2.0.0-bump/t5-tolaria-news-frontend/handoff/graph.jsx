// graph.jsx — abstract node/embedding visualization for the banner.
// Reads as both arcane sigil (concentric rings, glowing nodes) and ML
// embedding (clustered points, similarity edges). Original; no MTG art.

function NodeGraph({ density = 64, accent = '#7BE0D6', accentSoft = '#3a6f78',
                    ink = '#F0EAD6', motion = true, style = 'graph' }) {
  const svgRef = React.useRef(null);
  const rafRef = React.useRef(0);
  const tRef   = React.useRef(0);

  // Deterministic PRNG so layout doesn't reshuffle between renders.
  const rng = React.useMemo(() => {
    let s = 0xC0FFEE ^ density ^ (style === 'graph' ? 0 : style === 'constellation' ? 17 : 31);
    return () => {
      s = (s * 1664525 + 1013904223) >>> 0;
      return s / 0xFFFFFFFF;
    };
  }, [density, style]);

  // Build node positions in polar coords across 3 concentric "rings".
  // Inner ring = dense cluster (token core), outer = sparse halo.
  const nodes = React.useMemo(() => {
    const arr = [];
    const W = 600, H = 600, cx = W / 2, cy = H / 2;
    const ringCount = style === 'constellation' ? 5 : 3;
    for (let i = 0; i < density; i++) {
      const ringIdx = Math.floor(rng() * ringCount);
      const ringFrac = (ringIdx + 1) / ringCount;
      const baseR = 60 + ringFrac * 220;
      const jitter = (rng() - 0.5) * (style === 'constellation' ? 80 : 40);
      const r = baseR + jitter;
      const theta = rng() * Math.PI * 2;
      const x = cx + Math.cos(theta) * r;
      const y = cy + Math.sin(theta) * r;
      arr.push({
        x, y, r,
        theta,
        size: 0.8 + rng() * (ringIdx === 0 ? 2.6 : 1.6),
        hue: rng(),
        seed: rng() * 1000,
        pulseRate: 0.4 + rng() * 0.9,
        // Drift — each node sways gently around its seeded position.
        driftAmpX:  1.2 + rng() * 2.4,   // 1.2–3.6 px amplitude
        driftAmpY:  1.2 + rng() * 2.4,
        driftRateX: 0.08 + rng() * 0.10, // 0.08–0.18 Hz — very slow
        driftRateY: 0.08 + rng() * 0.10,
        driftSeedX: rng() * 1000,
        driftSeedY: rng() * 1000,
      });
    }
    return arr;
  }, [density, rng, style]);

  // Build a sparse edge set — nearest-neighbor within a radius.
  const edges = React.useMemo(() => {
    const out = [];
    const maxDist = style === 'constellation' ? 70 : 95;
    const maxPerNode = style === 'constellation' ? 2 : 3;
    for (let i = 0; i < nodes.length; i++) {
      const candidates = [];
      for (let j = 0; j < nodes.length; j++) {
        if (i === j) continue;
        const dx = nodes[i].x - nodes[j].x;
        const dy = nodes[i].y - nodes[j].y;
        const d = Math.hypot(dx, dy);
        if (d < maxDist) candidates.push({ j, d });
      }
      candidates.sort((a, b) => a.d - b.d);
      for (let k = 0; k < Math.min(maxPerNode, candidates.length); k++) {
        const { j, d } = candidates[k];
        if (i < j) out.push({ i, j, d, strength: 1 - d / maxDist });
      }
    }
    return out;
  }, [nodes, style]);

  // Starfield was previously generated here, but the full-screen background
  // starfield in <Starfield> (app.jsx) now owns that visual role. The graph
  // nodes themselves carry the twinkle inside the rings.

  // Concentric guide rings — give the viz a "sigil" quality and ground it.
  const rings = [80, 150, 220, 280];

  // Per-ring animation parameters — slow, subtle breathing on each guide ring,
  // halo, and hero ring. Read by the rAF loop below.
  const ringAnim = React.useMemo(() => ({
    rings: [
      { rate: 0.18, seed: 1.20, floor: 0.10, ceil: 0.22 },   // r=80
      { rate: 0.22, seed: 3.40, floor: 0.10, ceil: 0.22 },   // r=150
      { rate: 0.16, seed: 0.75, floor: 0.10, ceil: 0.22 },   // r=220
      { rate: 0.28, seed: 5.10, floor: 0.12, ceil: 0.24 },   // r=280
    ],
    halo:     { rate: 0.45, seed: 2.40, floor: 0.60, ceil: 1.00 },
    heroRing: { rate: 0.55, seed: 4.10, floor: 0.40, ceil: 0.85 },
  }), []);

  // Per-node floor/ceiling for richer twinkle (mutated once, after node creation).
  React.useMemo(() => {
    let s = 0xABC123 ^ density;
    const r = () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 0xFFFFFFFF; };
    nodes.forEach((n) => {
      n.floor = 0.15 + r() * 0.25;          // 0.15–0.40
      n.ceil  = 0.75 + r() * 0.25;          // 0.75–1.00
      n.pulseRate = 0.6 + r() * 1.4;        // 0.6–2.0 Hz — a touch livelier
    });
  }, [nodes, density]);

  // Animation loop — pulse opacities and gentle drift.
  React.useEffect(() => {
    if (!motion) return undefined;
    let last = performance.now();
    const tick = (now) => {
      const dt = (now - last) / 1000;
      last = now;
      tRef.current += dt;
      const svg = svgRef.current;
      if (svg) {
        const t = tRef.current;
        // Pulse node opacity + drift cx/cy — each node has its own twinkle range
        // AND its own slow positional sway, so the constellation feels alive.
        const nodeEls = svg.querySelectorAll('[data-pulse]');
        nodeEls.forEach((el, i) => {
          const n = nodes[i];
          if (!n) return;
          const range = n.ceil - n.floor;
          const v = n.floor + range * (0.5 + 0.5 * Math.sin(t * n.pulseRate + n.seed));
          el.setAttribute('opacity', v.toFixed(3));
          const dx = n.driftAmpX * Math.sin(t * n.driftRateX + n.driftSeedX);
          const dy = n.driftAmpY * Math.sin(t * n.driftRateY + n.driftSeedY);
          el.setAttribute('cx', (n.x + dx).toFixed(2));
          el.setAttribute('cy', (n.y + dy).toFixed(2));
        });
        // Concentric guide rings — each breathes its stroke-opacity slowly
        const ringEls = svg.querySelectorAll('[data-ring]');
        ringEls.forEach((el, i) => {
          const p = ringAnim.rings[i];
          if (!p) return;
          const range = p.ceil - p.floor;
          const v = p.floor + range * (0.5 + 0.5 * Math.sin(t * p.rate + p.seed));
          el.setAttribute('stroke-opacity', v.toFixed(3));
        });
        // Hero halo + ring — brighten and dim subtly
        const halo = svg.querySelector('[data-halo]');
        if (halo) {
          const p = ringAnim.halo;
          const range = p.ceil - p.floor;
          const v = p.floor + range * (0.5 + 0.5 * Math.sin(t * p.rate + p.seed));
          halo.setAttribute('opacity', v.toFixed(3));
        }
        const heroRing = svg.querySelector('[data-herohalo]');
        if (heroRing) {
          const p = ringAnim.heroRing;
          const range = p.ceil - p.floor;
          const v = p.floor + range * (0.5 + 0.5 * Math.sin(t * p.rate + p.seed));
          heroRing.setAttribute('stroke-opacity', v.toFixed(3));
        }
        // Rotate outer ring group very slowly
        const outer = svg.querySelector('[data-rotate]');
        if (outer) outer.setAttribute('transform', `rotate(${(t * 1.6).toFixed(2)} 300 300)`);
        // Edges — keep endpoints stuck to their drifting nodes
        const edgeEls = svg.querySelectorAll('[data-edge]');
        edgeEls.forEach((el) => {
          const ni = nodes[+el.getAttribute('data-i')];
          const nj = nodes[+el.getAttribute('data-j')];
          if (!ni || !nj) return;
          const dxi = ni.driftAmpX * Math.sin(t * ni.driftRateX + ni.driftSeedX);
          const dyi = ni.driftAmpY * Math.sin(t * ni.driftRateY + ni.driftSeedY);
          const dxj = nj.driftAmpX * Math.sin(t * nj.driftRateX + nj.driftSeedX);
          const dyj = nj.driftAmpY * Math.sin(t * nj.driftRateY + nj.driftSeedY);
          el.setAttribute('x1', (ni.x + dxi).toFixed(2));
          el.setAttribute('y1', (ni.y + dyi).toFixed(2));
          el.setAttribute('x2', (nj.x + dxj).toFixed(2));
          el.setAttribute('y2', (nj.y + dyj).toFixed(2));
        });
      }
      rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafRef.current);
  }, [motion, nodes, ringAnim]);

  // (ringAnim defined earlier near the top of the component)


  return (
    <svg ref={svgRef} viewBox="0 0 600 600"
         xmlns="http://www.w3.org/2000/svg"
         style={{ width: '100%', height: '100%', display: 'block' }}
         aria-hidden="true">
      <defs>
        <radialGradient id="bg-glow" cx="50%" cy="50%" r="50%">
          <stop offset="0%"  stopColor={accent} stopOpacity="0.22" />
          <stop offset="55%" stopColor={accent} stopOpacity="0.04" />
          <stop offset="100%" stopColor={accent} stopOpacity="0" />
        </radialGradient>
        <radialGradient id="node-glow" cx="50%" cy="50%" r="50%">
          <stop offset="0%"  stopColor={accent} stopOpacity="1" />
          <stop offset="60%" stopColor={accent} stopOpacity="0.4" />
          <stop offset="100%" stopColor={accent} stopOpacity="0" />
        </radialGradient>
        <filter id="soft-blur" x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="0.6" />
        </filter>
      </defs>

      {/* Ambient glow */}
      <circle cx="300" cy="300" r="290" fill="url(#bg-glow)" />

      {/* Concentric rings — scholarly armillary feel.
          Each ring breathes its stroke-opacity independently. */}
      <g stroke={ink} fill="none" strokeWidth="0.5">
        {rings.map((r) => (
          <circle key={r} cx="300" cy="300" r={r}
                  data-ring="" strokeOpacity="0.18" />
        ))}
      </g>

      {/* Tick marks on outermost ring (rotating slowly) */}
      <g data-rotate="" opacity="0.35" stroke={accentSoft} strokeWidth="0.6">
        {Array.from({ length: 48 }).map((_, i) => {
          const a = (i / 48) * Math.PI * 2;
          const r1 = 278, r2 = i % 6 === 0 ? 268 : 274;
          const x1 = 300 + Math.cos(a) * r1;
          const y1 = 300 + Math.sin(a) * r1;
          const x2 = 300 + Math.cos(a) * r2;
          const y2 = 300 + Math.sin(a) * r2;
          return <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} />;
        })}
      </g>

      {/* Edges — endpoints follow node drift. data-i/data-j carry node
          indices so the rAF loop can rewrite x1/y1/x2/y2 each frame. */}
      <g stroke={accent} strokeWidth="0.5" fill="none" filter="url(#soft-blur)">
        {edges.map((e, k) => (
          <line key={k} data-edge="" data-i={e.i} data-j={e.j}
                x1={nodes[e.i].x} y1={nodes[e.i].y}
                x2={nodes[e.j].x} y2={nodes[e.j].y}
                opacity={(0.08 + e.strength * 0.35).toFixed(3)} />
        ))}
      </g>

      {/* Halo behind hero node */}
      <circle cx="300" cy="300" r="22" fill="url(#node-glow)"
              data-halo="" opacity="0.9" />

      {/* Nodes */}
      <g>
        {nodes.map((n, i) => (
          <circle key={i} cx={n.x} cy={n.y} r={n.size}
                  fill={ink} data-pulse=""
                  opacity={0.7} />
        ))}
      </g>

      {/* Center hero node */}
      <circle cx="300" cy="300" r="3.6" fill={ink} />
      <circle cx="300" cy="300" r="6.5" fill="none" stroke={ink}
              strokeWidth="0.5" data-herohalo="" strokeOpacity="0.6" />

      {/* Faint diamond cardinals — Tolarian-academy compass nod */}
      <g stroke={ink} strokeWidth="0.4" opacity="0.4" fill="none">
        <path d="M300 60 L300 80 M300 540 L300 520 M60 300 L80 300 M540 300 L520 300" />
      </g>
    </svg>
  );
}

window.NodeGraph = NodeGraph;
