import { useEffect, useMemo, useRef } from 'react'

/**
 * Abstract node/embedding visualization — ported from the design handoff's
 * `design_files/graph.jsx` per `ANIMATING_STARS.md`. Purely decorative and
 * procedurally generated: per the handoff's own README, "the data is
 * procedurally generated... if `barrins_api` exposes a real embedding
 * endpoint, wire it up; otherwise keep it decorative" — no backend call, no
 * gating needed. Fixed to the "graph" composition (3 rings) at density 80,
 * matching ANIMATING_STARS.md's "production should ship a single
 * configured composition" (the prototype's density/style tweaks are
 * design-time only).
 */

interface Node {
  x: number
  y: number
  size: number
  pulseRate: number
  seed: number
  floor: number
  ceil: number
  driftAmpX: number
  driftAmpY: number
  driftRateX: number
  driftRateY: number
  driftSeedX: number
  driftSeedY: number
}

interface Edge {
  i: number
  j: number
  strength: number
}

const DENSITY = 80
const MAX_DIST = 95
const MAX_PER_NODE = 3
const RINGS = [80, 150, 220, 280]
const RING_ANIM = [
  { rate: 0.18, seed: 1.2, floor: 0.1, ceil: 0.22 },
  { rate: 0.22, seed: 3.4, floor: 0.1, ceil: 0.22 },
  { rate: 0.16, seed: 0.75, floor: 0.1, ceil: 0.22 },
  { rate: 0.28, seed: 5.1, floor: 0.12, ceil: 0.24 },
]
const HALO_ANIM = { rate: 0.45, seed: 2.4, floor: 0.6, ceil: 1.0 }
const HERO_RING_ANIM = { rate: 0.55, seed: 4.1, floor: 0.4, ceil: 0.85 }

function makeRng(seed: number) {
  let s = seed >>> 0
  return () => {
    s = (Math.imul(s, 1664525) + 1013904223) >>> 0
    return s / 0xffffffff
  }
}

export function NodeGraph({ accent, accentSoft }: { accent: string; accentSoft: string }) {
  const svgRef = useRef<SVGSVGElement>(null)
  const rafRef = useRef(0)
  const tRef = useRef(0)

  const nodes = useMemo<Node[]>(() => {
    const posRng = makeRng(0xc0ffee ^ DENSITY)
    const twinkleRng = makeRng(0xabc123 ^ DENSITY)
    const cx = 300
    const cy = 300
    const arr: Node[] = []
    for (let i = 0; i < DENSITY; i++) {
      const ringIdx = Math.floor(posRng() * 3)
      const ringFrac = (ringIdx + 1) / 3
      const baseR = 60 + ringFrac * 220
      const jitter = (posRng() - 0.5) * 40
      const r = baseR + jitter
      const theta = posRng() * Math.PI * 2
      arr.push({
        x: cx + Math.cos(theta) * r,
        y: cy + Math.sin(theta) * r,
        size: 0.8 + posRng() * (ringIdx === 0 ? 2.6 : 1.6),
        pulseRate: 0.6 + twinkleRng() * 1.4,
        seed: posRng() * 1000,
        floor: 0.15 + twinkleRng() * 0.25,
        ceil: 0.75 + twinkleRng() * 0.25,
        driftAmpX: 1.2 + posRng() * 2.4,
        driftAmpY: 1.2 + posRng() * 2.4,
        driftRateX: 0.08 + posRng() * 0.1,
        driftRateY: 0.08 + posRng() * 0.1,
        driftSeedX: posRng() * 1000,
        driftSeedY: posRng() * 1000,
      })
    }
    return arr
  }, [])

  const edges = useMemo<Edge[]>(() => {
    const out: Edge[] = []
    for (let i = 0; i < nodes.length; i++) {
      const candidates: { j: number; d: number }[] = []
      for (let j = 0; j < nodes.length; j++) {
        if (i === j) continue
        const dx = nodes[i].x - nodes[j].x
        const dy = nodes[i].y - nodes[j].y
        const d = Math.hypot(dx, dy)
        if (d < MAX_DIST) candidates.push({ j, d })
      }
      candidates.sort((a, b) => a.d - b.d)
      for (let k = 0; k < Math.min(MAX_PER_NODE, candidates.length); k++) {
        const { j, d } = candidates[k]
        if (i < j) out.push({ i, j, strength: 1 - d / MAX_DIST })
      }
    }
    return out
  }, [nodes])

  useEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return undefined
    let last = performance.now()
    const tick = (now: number) => {
      const dt = (now - last) / 1000
      last = now
      tRef.current += dt
      const svg = svgRef.current
      if (svg) {
        const t = tRef.current

        svg.querySelectorAll<SVGCircleElement>('[data-pulse]').forEach((el, i) => {
          const n = nodes[i]
          if (!n) return
          const range = n.ceil - n.floor
          const v = n.floor + range * (0.5 + 0.5 * Math.sin(t * n.pulseRate + n.seed))
          el.setAttribute('opacity', v.toFixed(3))
          const dx = n.driftAmpX * Math.sin(t * n.driftRateX + n.driftSeedX)
          const dy = n.driftAmpY * Math.sin(t * n.driftRateY + n.driftSeedY)
          el.setAttribute('cx', (n.x + dx).toFixed(2))
          el.setAttribute('cy', (n.y + dy).toFixed(2))
        })

        svg.querySelectorAll<SVGCircleElement>('[data-ring]').forEach((el, i) => {
          const p = RING_ANIM[i]
          if (!p) return
          const range = p.ceil - p.floor
          const v = p.floor + range * (0.5 + 0.5 * Math.sin(t * p.rate + p.seed))
          el.setAttribute('stroke-opacity', v.toFixed(3))
        })

        const halo = svg.querySelector<SVGCircleElement>('[data-halo]')
        if (halo) {
          const range = HALO_ANIM.ceil - HALO_ANIM.floor
          const v =
            HALO_ANIM.floor +
            range * (0.5 + 0.5 * Math.sin(t * HALO_ANIM.rate + HALO_ANIM.seed))
          halo.setAttribute('opacity', v.toFixed(3))
        }

        const heroRing = svg.querySelector<SVGCircleElement>('[data-herohalo]')
        if (heroRing) {
          const range = HERO_RING_ANIM.ceil - HERO_RING_ANIM.floor
          const v =
            HERO_RING_ANIM.floor +
            range * (0.5 + 0.5 * Math.sin(t * HERO_RING_ANIM.rate + HERO_RING_ANIM.seed))
          heroRing.setAttribute('stroke-opacity', v.toFixed(3))
        }

        const outer = svg.querySelector<SVGGElement>('[data-rotate]')
        if (outer) outer.setAttribute('transform', `rotate(${(t * 1.6).toFixed(2)} 300 300)`)

        svg.querySelectorAll<SVGLineElement>('[data-edge]').forEach((el) => {
          const ni = nodes[Number(el.getAttribute('data-i'))]
          const nj = nodes[Number(el.getAttribute('data-j'))]
          if (!ni || !nj) return
          const dxi = ni.driftAmpX * Math.sin(t * ni.driftRateX + ni.driftSeedX)
          const dyi = ni.driftAmpY * Math.sin(t * ni.driftRateY + ni.driftSeedY)
          const dxj = nj.driftAmpX * Math.sin(t * nj.driftRateX + nj.driftSeedX)
          const dyj = nj.driftAmpY * Math.sin(t * nj.driftRateY + nj.driftSeedY)
          el.setAttribute('x1', (ni.x + dxi).toFixed(2))
          el.setAttribute('y1', (ni.y + dyi).toFixed(2))
          el.setAttribute('x2', (nj.x + dxj).toFixed(2))
          el.setAttribute('y2', (nj.y + dyj).toFixed(2))
        })
      }
      rafRef.current = requestAnimationFrame(tick)
    }
    rafRef.current = requestAnimationFrame(tick)
    return () => {
      cancelAnimationFrame(rafRef.current)
    }
  }, [nodes])

  return (
    <svg
      ref={svgRef}
      viewBox="0 0 600 600"
      className="block size-full"
      aria-hidden="true"
    >
      <defs>
        <radialGradient id="bg-glow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor={accent} stopOpacity="0.22" />
          <stop offset="55%" stopColor={accent} stopOpacity="0.04" />
          <stop offset="100%" stopColor={accent} stopOpacity="0" />
        </radialGradient>
        <radialGradient id="node-glow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor={accent} stopOpacity="1" />
          <stop offset="60%" stopColor={accent} stopOpacity="0.4" />
          <stop offset="100%" stopColor={accent} stopOpacity="0" />
        </radialGradient>
        <filter id="soft-blur" x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="0.6" />
        </filter>
      </defs>

      <circle cx="300" cy="300" r="290" fill="url(#bg-glow)" />

      <g stroke="var(--color-foreground)" fill="none" strokeWidth="0.5">
        {RINGS.map((r) => (
          <circle key={r} cx="300" cy="300" r={r} data-ring="" strokeOpacity="0.18" />
        ))}
      </g>

      <g data-rotate="" opacity="0.35" stroke={accentSoft} strokeWidth="0.6">
        {Array.from({ length: 48 }, (_, i) => {
          const a = (i / 48) * Math.PI * 2
          const r1 = 278
          const r2 = i % 6 === 0 ? 268 : 274
          return (
            <line
              key={i}
              x1={300 + Math.cos(a) * r1}
              y1={300 + Math.sin(a) * r1}
              x2={300 + Math.cos(a) * r2}
              y2={300 + Math.sin(a) * r2}
            />
          )
        })}
      </g>

      <g stroke={accent} strokeWidth="0.5" fill="none" filter="url(#soft-blur)">
        {edges.map((e, k) => (
          <line
            key={k}
            data-edge=""
            data-i={e.i}
            data-j={e.j}
            x1={nodes[e.i].x}
            y1={nodes[e.i].y}
            x2={nodes[e.j].x}
            y2={nodes[e.j].y}
            opacity={(0.08 + e.strength * 0.35).toFixed(3)}
          />
        ))}
      </g>

      <circle cx="300" cy="300" r="22" fill="url(#node-glow)" data-halo="" opacity="0.9" />

      <g>
        {nodes.map((n, i) => (
          <circle
            key={i}
            cx={n.x}
            cy={n.y}
            r={n.size}
            fill="var(--color-foreground)"
            data-pulse=""
            opacity={0.7}
          />
        ))}
      </g>

      <circle cx="300" cy="300" r="3.6" fill="var(--color-foreground)" />
      <circle
        cx="300"
        cy="300"
        r="6.5"
        fill="none"
        stroke="var(--color-foreground)"
        strokeWidth="0.5"
        data-herohalo=""
        strokeOpacity="0.6"
      />

      <g stroke="var(--color-foreground)" strokeWidth="0.4" opacity="0.4" fill="none">
        <path d="M300 60 L300 80 M300 540 L300 520 M60 300 L80 300 M540 300 L520 300" />
      </g>
    </svg>
  )
}
