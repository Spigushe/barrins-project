import { useEffect, useMemo, useRef, useState } from 'react'

/**
 * Full-screen ambient twinkle layer behind the landing page. Ported from the
 * design handoff's `design_files/app.jsx` `<Starfield>` per
 * `ANIMATING_STARS.md` — decorative only, no backend data. Density scales
 * with viewport area (~1 per 9,000px², capped at 200); each star gets its
 * own seeded twinkle + drift so the layer doesn't read as a uniform
 * heartbeat (ANIMATING_STARS.md § "Don't sync the twinkle rates").
 */

interface Star {
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

function makeRng(seed: number) {
  let s = seed >>> 0
  return () => {
    s = (Math.imul(s, 1664525) + 1013904223) >>> 0
    return s / 0xffffffff
  }
}

export function Starfield() {
  const svgRef = useRef<SVGSVGElement>(null)
  const rafRef = useRef(0)
  const tRef = useRef(0)
  const [size, setSize] = useState(() =>
    typeof window === 'undefined'
      ? { w: 1440, h: 900 }
      : { w: window.innerWidth, h: window.innerHeight },
  )

  useEffect(() => {
    const onResize = () => {
      setSize({ w: window.innerWidth, h: window.innerHeight })
    }
    window.addEventListener('resize', onResize)
    return () => {
      window.removeEventListener('resize', onResize)
    }
  }, [])

  const stars = useMemo<Star[]>(() => {
    const count = Math.min(200, Math.round((size.w * size.h) / 9000))
    const r = makeRng(0xc0defeed)
    const arr: Star[] = []
    for (let i = 0; i < count; i++) {
      arr.push({
        x: r() * size.w,
        y: r() * size.h,
        size: 0.4 + r() * 1.1,
        pulseRate: 0.8 + r() * 2.4,
        seed: r() * 1000,
        floor: 0.05 + r() * 0.18,
        ceil: 0.45 + r() * 0.45,
        driftAmpX: 3 + r() * 9,
        driftAmpY: 3 + r() * 9,
        driftRateX: 0.05 + r() * 0.07,
        driftRateY: 0.05 + r() * 0.07,
        driftSeedX: r() * 1000,
        driftSeedY: r() * 1000,
      })
    }
    return arr
  }, [size.w, size.h])

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
        const els = svg.querySelectorAll<SVGCircleElement>('[data-twinkle]')
        els.forEach((el, i) => {
          const s = stars[i]
          if (!s) return
          const range = s.ceil - s.floor
          const v = s.floor + range * (0.5 + 0.5 * Math.sin(t * s.pulseRate + s.seed))
          el.setAttribute('opacity', v.toFixed(3))
          const dx = s.driftAmpX * Math.sin(t * s.driftRateX + s.driftSeedX)
          const dy = s.driftAmpY * Math.sin(t * s.driftRateY + s.driftSeedY)
          el.setAttribute('cx', (s.x + dx).toFixed(2))
          el.setAttribute('cy', (s.y + dy).toFixed(2))
        })
      }
      rafRef.current = requestAnimationFrame(tick)
    }
    rafRef.current = requestAnimationFrame(tick)
    return () => {
      cancelAnimationFrame(rafRef.current)
    }
  }, [stars])

  return (
    <svg
      ref={svgRef}
      width={size.w}
      height={size.h}
      viewBox={`0 0 ${String(size.w)} ${String(size.h)}`}
      className="pointer-events-none fixed inset-0 z-0"
      aria-hidden="true"
    >
      {stars.map((s, i) => (
        <circle
          key={i}
          cx={s.x}
          cy={s.y}
          r={s.size}
          fill="var(--color-foreground)"
          data-twinkle=""
          opacity={(s.floor + s.ceil) / 2}
        />
      ))}
    </svg>
  )
}
