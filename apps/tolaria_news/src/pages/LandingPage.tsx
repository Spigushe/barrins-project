import { Link } from 'react-router-dom'
import { Eyebrow } from '@/components/ui/eyebrow'
import { BackgroundField } from '@/components/landing/BackgroundField'
import { VizPanel } from '@/components/landing/VizPanel'
import { karnTabletsEnabled } from '@/lib/featureFlags'

// Copy matches the design handoff's prototype defaults
// (handoff/design_handoff_tolaria_news/design_files/app.jsx TWEAK_DEFAULTS)
// pixel-for-copy, restyled into this app's real component system.
const EYEBROW = 'Duel Commander · v0.4 Tolarian Release'
const SUBHEAD =
  "Barrin's Project is a suite of machine learning tools for competitive Magic: the Gathering: deck synthesis, surfacing trends, and meta forecast for Duel Commander pilots."

// The prototype's stats row ships static example numbers — it never calls a
// real API either. Kept as-is for tournaments/decklists (placeholder,
// pending a future barrins_api aggregate endpoint — not a T6 dependency).
// "Archetypes mapped" specifically needs T6 (Karn Tablets, not started), so
// it's the one gated behind the flag rather than shown as invented data.
const TOURNAMENTS_PARSED_PLACEHOLDER = '3,184'
const DECKLISTS_INDEXED_PLACEHOLDER = '96k'
const ARCHETYPES_MAPPED_PLACEHOLDER = '412'

function StatBlock({ n, l }: { n: string; l: string }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="font-serif text-[28px] leading-none tracking-[-0.02em] text-foreground">
        {n}
      </span>
      <span className="text-[11px] tracking-[0.12em] text-muted-foreground uppercase">
        {l}
      </span>
    </div>
  )
}

function Arrow() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
      <path
        d="M3 7h8M7 3l4 4-4 4"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

export function LandingPage() {
  const primaryCta = karnTabletsEnabled
    ? { to: '/metagame', label: 'Explore the metagame' }
    : { to: '/tournaments', label: 'Browse tournaments' }

  return (
    <div className="relative">
      <BackgroundField />

      <div className="relative z-[2] grid min-h-[calc(100svh-220px)] items-center gap-12 md:grid-cols-[1.1fr_1fr]">
        <div className="max-w-[640px]">
          <Eyebrow className="mb-7">{EYEBROW}</Eyebrow>

          <h1 className="m-0 font-serif text-[clamp(44px,6.2vw,88px)] leading-[0.98] font-normal tracking-[-0.02em] text-pretty">
            <span className="block">Duel Commander,</span>
            <span className="block">
              metagame <em className="font-serif text-accent italic">decoded.</em>
            </span>
          </h1>

          <p className="mt-7 mb-9 max-w-[560px] text-[17px] leading-[1.55] text-pretty text-muted-foreground">
            {SUBHEAD}
          </p>

          <div className="flex flex-wrap gap-3">
            <Link
              to={primaryCta.to}
              className="inline-flex items-center gap-2.5 rounded-(--radius-button) bg-accent px-[22px] py-3.5 text-[14.5px] font-medium text-accent-foreground transition-transform duration-150 hover:-translate-y-px"
              style={{ boxShadow: '0 6px 20px #7be0d633, 0 0 0 0.5px #7be0d6' }}
            >
              {primaryCta.label}
              <Arrow />
            </Link>
            <Link
              to="/methodology"
              className="inline-flex items-center gap-2.5 rounded-(--radius-button) border border-border px-[22px] py-3.5 text-[14.5px] font-medium text-foreground transition-colors duration-150 hover:bg-input"
            >
              Read the methodology
            </Link>
          </div>

          <div className="mt-14 flex flex-wrap gap-10">
            <StatBlock n={TOURNAMENTS_PARSED_PLACEHOLDER} l="tournaments parsed" />
            {karnTabletsEnabled && (
              <StatBlock n={ARCHETYPES_MAPPED_PLACEHOLDER} l="archetypes mapped" />
            )}
            <StatBlock n={DECKLISTS_INDEXED_PLACEHOLDER} l="decklists indexed" />
          </div>
        </div>

        <div className="hidden md:block">
          <VizPanel />
        </div>
      </div>
    </div>
  )
}
