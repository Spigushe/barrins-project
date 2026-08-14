import { Starfield } from './Starfield'

const GRAIN_SVG =
  "url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='160' height='160'>" +
  "<filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' seed='3'/>" +
  "<feColorMatrix values='0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 0.5 0'/></filter>" +
  "<rect width='100%25' height='100%25' filter='url(%23n)' opacity='0.25'/></svg>\")"

/**
 * Ambient page background — starfield + radial wash + grain + horizon
 * hairline, ported from the design handoff's `<BackgroundField>`
 * (`design_files/app.jsx`) and `DESIGN_SYSTEM.md` § Background field. Landing
 * page only for now (PAGES.md suggests it dimmed on every page; scoped here
 * per the current ask).
 */
export function BackgroundField() {
  return (
    <>
      <Starfield />
      <div
        className="pointer-events-none fixed inset-0 z-0"
        style={{
          background:
            'radial-gradient(900px 600px at 18% 35%, color-mix(in srgb, var(--color-accent) 12%, transparent), transparent 70%), radial-gradient(700px 500px at 85% 70%, var(--color-card), transparent 65%)',
        }}
      />
      <div
        className="pointer-events-none fixed inset-0 z-0 opacity-50 mix-blend-overlay"
        style={{ backgroundImage: GRAIN_SVG }}
      />
      <div className="pointer-events-none fixed inset-x-0 top-20 z-0 h-px bg-border" />
    </>
  )
}
