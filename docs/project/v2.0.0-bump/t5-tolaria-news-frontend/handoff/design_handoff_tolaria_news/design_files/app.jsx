// app.jsx — Barrin's Project landing-page banner.
// Original design — does not copy MTG-branded UI, mana symbols, or card frames.

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "theme": "midnight",
  "accent": "#7BE0D6",
  "eyebrow": "Duel Commander · v0.4 Tolarian Release",
  "headline": "Duel Commander,\nmetagame decoded.",
  "subhead": "Barrin's Project is a suite of machine learning tools for competitive Magic: the Gathering — deck synthesis, surfacing trends, and meta forecast for Duel Commander pilots.",
  "primaryCta": "Explore the metagame",
  "secondaryCta": "Read the methodology",
  "vizDensity": 80,
  "vizStyle": "graph",
  "motion": true,
  "showStats": true,
  "layout": "split"
}/*EDITMODE-END*/;

const THEMES = {
  midnight:  { bg: '#0B1220', bg2: '#0E1830', ink: '#F0EAD6', mute: 'rgba(240,234,214,0.62)', line: 'rgba(240,234,214,0.10)' },
  twilight:  { bg: '#1A1230', bg2: '#241844', ink: '#F4ECDB', mute: 'rgba(244,236,219,0.62)', line: 'rgba(244,236,219,0.10)' },
  parchment: { bg: '#F2EBD8', bg2: '#E8DFC4', ink: '#1A1812', mute: 'rgba(26,24,18,0.62)',    line: 'rgba(26,24,18,0.10)' },
};

const ACCENTS = ['#7BE0D6', '#C7A455', '#8FA8FF', '#E08A6A'];

function App() {
  const [t, setTweak] = useTweaks(TWEAK_DEFAULTS);
  const theme = THEMES[t.theme] || THEMES.midnight;
  const isLight = t.theme === 'parchment';
  const accentSoft = isLight ? 'rgba(0,0,0,0.35)' : 'rgba(255,255,255,0.20)';

  // Type stack
  const serif = `'EB Garamond', 'Cormorant Garamond', Georgia, serif`;
  const sans  = `'Geist', ui-sans-serif, system-ui, -apple-system, 'Segoe UI', sans-serif`;
  const mono  = `'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, monospace`;

  // Split headline at \n for line breaks.
  const headlineLines = t.headline.split('\n');

  return (
    <div style={{
      minHeight: '100vh',
      background: theme.bg,
      color: theme.ink,
      fontFamily: sans,
      position: 'relative',
      overflow: 'hidden',
    }}>
      {/* Ambient background — soft radial + grain */}
      <BackgroundField theme={theme} accent={t.accent} />

      {/* NAV */}
      <Nav theme={theme} accent={t.accent} serif={serif} mono={mono} />

      {/* HERO */}
      <section style={{
        position: 'relative',
        zIndex: 2,
        maxWidth: 1440,
        margin: '0 auto',
        padding: '60px 56px 80px',
        display: 'grid',
        gridTemplateColumns: t.layout === 'split' ? '1.1fr 1fr' : '1fr',
        gap: 48,
        alignItems: 'center',
        minHeight: 'calc(100vh - 80px)',
      }}>
        <div style={{ maxWidth: t.layout === 'split' ? 640 : 820,
                      margin: t.layout === 'centered' ? '0 auto' : 0,
                      textAlign: t.layout === 'centered' ? 'center' : 'left' }}>
          {/* Eyebrow */}
          {t.eyebrow && (
            <div style={{
              display: 'inline-flex', alignItems: 'center', gap: 10,
              padding: '6px 11px 6px 9px',
              border: `0.5px solid ${theme.line}`,
              borderRadius: 999,
              background: isLight ? 'rgba(255,255,255,0.45)' : 'rgba(255,255,255,0.03)',
              fontFamily: mono,
              fontSize: 11,
              letterSpacing: '0.04em',
              color: theme.mute,
              marginBottom: 28,
            }}>
              <span style={{
                width: 6, height: 6, borderRadius: '50%',
                background: t.accent,
                boxShadow: `0 0 8px ${t.accent}`,
              }} />
              {t.eyebrow}
            </div>
          )}

          {/* Headline */}
          <h1 style={{
            fontFamily: serif,
            fontWeight: 400,
            fontSize: 'clamp(44px, 6.2vw, 88px)',
            lineHeight: 0.98,
            letterSpacing: '-0.02em',
            margin: 0,
            textWrap: 'pretty',
          }}>
            {headlineLines.map((ln, i) => {
              // Italicize the last line's last 2 words for a scholarly flourish.
              const isLast = i === headlineLines.length - 1;
              if (!isLast) return <span key={i} style={{ display: 'block' }}>{ln}</span>;
              const parts = ln.trim().split(' ');
              const tail = parts.slice(-1).join(' ');
              const head = parts.slice(0, -1).join(' ');
              return (
                <span key={i} style={{ display: 'block' }}>
                  {head}{head ? ' ' : ''}
                  <em style={{ fontStyle: 'italic', color: t.accent,
                               fontFamily: serif }}>{tail}</em>
                </span>
              );
            })}
          </h1>

          {/* Subhead */}
          <p style={{
            fontFamily: sans,
            fontSize: 17,
            lineHeight: 1.55,
            color: theme.mute,
            maxWidth: 560,
            marginTop: 28,
            marginBottom: 36,
            marginLeft: t.layout === 'centered' ? 'auto' : 0,
            marginRight: t.layout === 'centered' ? 'auto' : 0,
            textWrap: 'pretty',
          }}>
            {t.subhead}
          </p>

          {/* CTAs */}
          <div style={{
            display: 'flex', gap: 12, flexWrap: 'wrap',
            justifyContent: t.layout === 'centered' ? 'center' : 'flex-start',
          }}>
            <CtaButton primary accent={t.accent} ink={theme.ink} isLight={isLight}>
              {t.primaryCta}
              <Arrow />
            </CtaButton>
            <CtaButton accent={t.accent} ink={theme.ink} line={theme.line} isLight={isLight}>
              {t.secondaryCta}
            </CtaButton>
          </div>

          {/* Stats row */}
          {t.showStats && (
            <div style={{
              marginTop: 56,
              display: 'flex',
              gap: 40,
              flexWrap: 'wrap',
              justifyContent: t.layout === 'centered' ? 'center' : 'flex-start',
              fontFamily: mono,
            }}>
              <Stat n="3,184" l="tournaments parsed" accent={t.accent} mute={theme.mute} serif={serif} />
              <Stat n="412"   l="archetypes mapped"  accent={t.accent} mute={theme.mute} serif={serif} />
              <Stat n="96k"   l="decklists indexed"  accent={t.accent} mute={theme.mute} serif={serif} />
            </div>
          )}
        </div>

        {/* Right column: graph visualization */}
        {t.layout === 'split' && (
          <VizPanel theme={theme} accent={t.accent} accentSoft={accentSoft}
                    density={t.vizDensity} motion={t.motion} style={t.vizStyle}
                    mono={mono} serif={serif} />
        )}
      </section>

      {/* Bottom rail — scroll cue + corner mark */}
      <BottomRail theme={theme} mono={mono} />

      {/* Tweaks */}
      <TweaksPanel title="Tweaks">
        <TweakSection label="Theme">
          <TweakRadio label="Palette" value={t.theme}
                      options={[
                        { value: 'midnight', label: 'Midnight' },
                        { value: 'twilight', label: 'Twilight' },
                        { value: 'parchment', label: 'Parchment' },
                      ]}
                      onChange={(v) => setTweak('theme', v)} />
          <TweakColor label="Accent" value={t.accent}
                      options={ACCENTS}
                      onChange={(v) => setTweak('accent', v)} />
        </TweakSection>
        <TweakSection label="Layout">
          <TweakRadio label="Composition" value={t.layout}
                      options={['split', 'centered']}
                      onChange={(v) => setTweak('layout', v)} />
          <TweakToggle label="Show stats row" value={t.showStats}
                       onChange={(v) => setTweak('showStats', v)} />
        </TweakSection>
        <TweakSection label="Visualization">
          <TweakRadio label="Motif" value={t.vizStyle}
                      options={[
                        { value: 'graph', label: 'Graph' },
                        { value: 'constellation', label: 'Stars' },
                      ]}
                      onChange={(v) => setTweak('vizStyle', v)} />
          <TweakSlider label="Density" value={t.vizDensity}
                       min={20} max={160} step={4}
                       onChange={(v) => setTweak('vizDensity', v)} />
          <TweakToggle label="Motion" value={t.motion}
                       onChange={(v) => setTweak('motion', v)} />
        </TweakSection>
        <TweakSection label="Copy">
          <TweakText label="Eyebrow" value={t.eyebrow}
                     onChange={(v) => setTweak('eyebrow', v)} />
          <TweakText label="Headline" value={t.headline}
                     onChange={(v) => setTweak('headline', v)} />
          <TweakText label="Primary CTA" value={t.primaryCta}
                     onChange={(v) => setTweak('primaryCta', v)} />
          <TweakText label="Secondary CTA" value={t.secondaryCta}
                     onChange={(v) => setTweak('secondaryCta', v)} />
        </TweakSection>
      </TweaksPanel>
    </div>
  );
}

// ── Nav ────────────────────────────────────────────────────────────────────
function Nav({ theme, accent, serif, mono }) {
  const links = ['Metagame', 'Archetypes', 'Decklists', 'Tournaments', 'Trends'];
  return (
    <header style={{
      position: 'relative', zIndex: 3,
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      padding: '22px 56px',
      maxWidth: 1440, margin: '0 auto',
    }}>
      <a href="#" style={{ display: 'flex', alignItems: 'center', gap: 10,
                           textDecoration: 'none', color: theme.ink }}>
        <Sigil accent={accent} ink={theme.ink} />
        <span style={{ fontFamily: serif, fontSize: 19, fontStyle: 'italic',
                       letterSpacing: '-0.01em' }}>
          Barrin&apos;s Project
        </span>
      </a>

      <nav style={{ display: 'flex', gap: 28 }}>
        {links.map((l) => (
          <a key={l} href="#" style={{
            color: theme.mute, textDecoration: 'none',
            fontSize: 13.5, letterSpacing: '0.01em',
            transition: 'color .15s',
          }}
             onMouseEnter={(e) => (e.currentTarget.style.color = theme.ink)}
             onMouseLeave={(e) => (e.currentTarget.style.color = theme.mute)}>
            {l}
          </a>
        ))}
      </nav>

      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <span style={{ fontFamily: mono, fontSize: 11, color: theme.mute }}>
          ⌘K
        </span>
        <button style={{
          appearance: 'none', border: `0.5px solid ${theme.line}`,
          background: 'transparent', color: theme.ink,
          fontFamily: 'inherit', fontSize: 13,
          padding: '8px 14px', borderRadius: 8,
          cursor: 'pointer',
        }}>
          Sign in
        </button>
      </div>
    </header>
  );
}

// ── Sigil (original mark, not MTG branding) ───────────────────────────────
function Sigil({ accent, ink }) {
  return (
    <svg width="28" height="28" viewBox="0 0 28 28" xmlns="http://www.w3.org/2000/svg"
         aria-label="Barrin's Project sigil">
      <circle cx="14" cy="14" r="12" fill="none" stroke={ink} strokeOpacity="0.4" strokeWidth="0.6" />
      <circle cx="14" cy="14" r="7"  fill="none" stroke={ink} strokeOpacity="0.6" strokeWidth="0.6" />
      <path d="M14 4 L24 14 L14 24 L4 14 Z" fill="none" stroke={accent} strokeWidth="0.9" />
      <circle cx="14" cy="14" r="2.2" fill={accent} />
      <circle cx="14" cy="14" r="3.6" fill="none" stroke={accent} strokeOpacity="0.4" strokeWidth="0.6" />
    </svg>
  );
}

// ── Stat ──────────────────────────────────────────────────────────────────
function Stat({ n, l, accent, mute, serif }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      <span style={{ fontFamily: serif, fontSize: 28, lineHeight: 1,
                     letterSpacing: '-0.02em' }}>{n}</span>
      <span style={{ fontSize: 11, color: mute, textTransform: 'uppercase',
                     letterSpacing: '0.12em' }}>{l}</span>
    </div>
  );
}

// ── CTA ───────────────────────────────────────────────────────────────────
function CtaButton({ primary, accent, ink, line, isLight, children }) {
  const [hover, setHover] = React.useState(false);
  const base = {
    appearance: 'none', border: 0, cursor: 'pointer',
    fontFamily: 'inherit', fontSize: 14.5, fontWeight: 500,
    padding: '14px 22px', borderRadius: 10,
    display: 'inline-flex', alignItems: 'center', gap: 10,
    transition: 'transform .15s, background .15s, border-color .15s',
    transform: hover ? 'translateY(-1px)' : 'translateY(0)',
  };
  if (primary) {
    return (
      <button onMouseEnter={() => setHover(true)} onMouseLeave={() => setHover(false)}
              style={{
                ...base,
                background: accent,
                color: '#0B1220',
                boxShadow: hover
                  ? `0 12px 36px ${accent}55, 0 0 0 0.5px ${accent}`
                  : `0 6px 20px ${accent}33, 0 0 0 0.5px ${accent}`,
              }}>
        {children}
      </button>
    );
  }
  return (
    <button onMouseEnter={() => setHover(true)} onMouseLeave={() => setHover(false)}
            style={{
              ...base,
              background: 'transparent',
              color: ink,
              border: `0.5px solid ${hover ? (isLight ? 'rgba(0,0,0,0.4)' : 'rgba(255,255,255,0.35)') : line}`,
            }}>
      {children}
    </button>
  );
}

function Arrow() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
      <path d="M3 7h8M7 3l4 4-4 4" stroke="currentColor" strokeWidth="1.4"
            strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

// ── Viz panel (the right-hand showpiece) ───────────────────────────────────
function VizPanel({ theme, accent, accentSoft, density, motion, style, mono, serif }) {
  return (
    <div style={{ position: 'relative', aspectRatio: '1 / 1', width: '100%',
                  maxWidth: 620, justifySelf: 'end' }}>
      {/* Corner brackets — instrument-panel framing */}
      <Brackets ink={theme.ink} />

      {/* The graph itself */}
      <div style={{ position: 'absolute', inset: 18 }}>
        <NodeGraph density={density} accent={accent} accentSoft={accentSoft}
                   ink={theme.ink} motion={motion} style={style} />
      </div>

      {/* Floating callouts — telemetry annotations */}
      <Callout pos={{ top: '14%', right: '4%' }} mono={mono} serif={serif}
               accent={accent} mute={theme.mute} ink={theme.ink}
               eyebrow="cluster · tymna / thrasios"
               main="share 11.4%" />
      <Callout pos={{ bottom: '18%', left: '2%' }} mono={mono} serif={serif}
               accent={accent} mute={theme.mute} ink={theme.ink}
               eyebrow="archetype · midrange-value"
               main="n = 286" reverse />
      <Callout pos={{ bottom: '6%', right: '8%' }} mono={mono} serif={serif}
               accent={accent} mute={theme.mute} ink={theme.ink}
               eyebrow="format · duel commander"
               main="winrate ↑ 2.4%" />

      {/* Corner caption — what this thing is */}
      <div style={{ position: 'absolute', top: 0, left: 0,
                    fontFamily: mono, fontSize: 10.5, letterSpacing: '0.08em',
                    color: theme.mute, textTransform: 'uppercase' }}>
        <span style={{ color: accent }}>◆</span> meta-graph · dc.001
      </div>
      <div style={{ position: 'absolute', top: 0, right: 0,
                    fontFamily: mono, fontSize: 10.5, letterSpacing: '0.08em',
                    color: theme.mute, textTransform: 'uppercase' }}>
        live · {density} commanders
      </div>
    </div>
  );
}

function Brackets({ ink }) {
  const C = ({ style }) => (
    <span style={{
      position: 'absolute',
      width: 14, height: 14,
      borderColor: ink, borderStyle: 'solid', opacity: 0.4,
      ...style,
    }} />
  );
  return (
    <>
      <C style={{ top: 0,    left: 0,    borderWidth: '0.5px 0 0 0.5px' }} />
      <C style={{ top: 0,    right: 0,   borderWidth: '0.5px 0.5px 0 0' }} />
      <C style={{ bottom: 0, left: 0,    borderWidth: '0 0 0.5px 0.5px' }} />
      <C style={{ bottom: 0, right: 0,   borderWidth: '0 0.5px 0.5px 0' }} />
    </>
  );
}

function Callout({ pos, eyebrow, main, accent, mute, ink, mono, serif, reverse }) {
  return (
    <div style={{
      position: 'absolute', ...pos,
      display: 'flex', flexDirection: 'column',
      alignItems: reverse ? 'flex-start' : 'flex-end',
      gap: 4, pointerEvents: 'none',
    }}>
      <span style={{ fontFamily: mono, fontSize: 9.5, letterSpacing: '0.1em',
                     color: mute, textTransform: 'uppercase' }}>
        <span style={{ color: accent }}>—</span> {eyebrow}
      </span>
      <span style={{ fontFamily: serif, fontSize: 18, fontStyle: 'italic',
                     color: ink, letterSpacing: '-0.01em' }}>
        {main}
      </span>
    </div>
  );
}

// ── Background field ─────────────────────────────────────────────────────
function BackgroundField({ theme, accent }) {
  return (
    <>
      {/* Full-screen starfield — ambient twinkle covering the entire viewport */}
      <Starfield ink={theme.ink} />

      {/* Top-left radial — emanation behind the headline */}
      <div style={{
        position: 'absolute', inset: 0, pointerEvents: 'none',
        background: `radial-gradient(900px 600px at 18% 35%, ${accent}1F, transparent 70%),
                     radial-gradient(700px 500px at 85% 70%, ${theme.bg2}, transparent 65%)`,
      }} />
      {/* Grain */}
      <div style={{
        position: 'absolute', inset: 0, pointerEvents: 'none', opacity: 0.5,
        mixBlendMode: theme.ink === '#F0EAD6' ? 'overlay' : 'multiply',
        backgroundImage:
          `url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='160' height='160'>` +
          `<filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' seed='3'/>` +
          `<feColorMatrix values='0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 0.5 0'/></filter>` +
          `<rect width='100%' height='100%' filter='url(%23n)' opacity='0.25'/></svg>")`,
      }} />
      {/* Thin horizon line near top — establishes the band */}
      <div style={{
        position: 'absolute', top: 80, left: 0, right: 0, height: 0.5,
        background: theme.line,
      }} />
    </>
  );
}

// Full-screen starfield — ambient twinkle layer covering the whole viewport.
// Density scales with viewport area; per-star floor/ceiling for varied twinkle.
function Starfield({ ink }) {
  const svgRef = React.useRef(null);
  const rafRef = React.useRef(0);
  const tRef   = React.useRef(0);
  const [size, setSize] = React.useState(
    () => typeof window === 'undefined'
      ? { w: 1440, h: 900 }
      : { w: window.innerWidth, h: window.innerHeight },
  );

  React.useEffect(() => {
    const onResize = () => setSize({ w: window.innerWidth, h: window.innerHeight });
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  const stars = React.useMemo(() => {
    const count = Math.min(200, Math.round((size.w * size.h) / 9000));
    let s = 0xC0DEFEED;
    const r = () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 0xFFFFFFFF; };
    const arr = [];
    for (let i = 0; i < count; i++) {
      arr.push({
        x: r() * size.w,
        y: r() * size.h,
        size: 0.4 + r() * 1.1,
        pulseRate: 0.8 + r() * 2.4,
        seed: r() * 1000,
        floor: 0.05 + r() * 0.18,
        ceil:  0.45 + r() * 0.45,
        // Drift — starfield stars roam wider and slower than graph nodes.
        driftAmpX:  3 + r() * 9,            // 3–12 px amplitude
        driftAmpY:  3 + r() * 9,
        driftRateX: 0.05 + r() * 0.07,      // 0.05–0.12 Hz — very slow
        driftRateY: 0.05 + r() * 0.07,
        driftSeedX: r() * 1000,
        driftSeedY: r() * 1000,
      });
    }
    return arr;
  }, [size.w, size.h]);

  React.useEffect(() => {
    if (typeof window === 'undefined') return undefined;
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return undefined;
    let last = performance.now();
    const tick = (now) => {
      const dt = (now - last) / 1000;
      last = now;
      tRef.current += dt;
      const svg = svgRef.current;
      if (svg) {
        const t = tRef.current;
        const els = svg.querySelectorAll('[data-twinkle]');
        els.forEach((el, i) => {
          const s = stars[i];
          if (!s) return;
          const range = s.ceil - s.floor;
          const v = s.floor + range * (0.5 + 0.5 * Math.sin(t * s.pulseRate + s.seed));
          el.setAttribute('opacity', v.toFixed(3));
          const dx = s.driftAmpX * Math.sin(t * s.driftRateX + s.driftSeedX);
          const dy = s.driftAmpY * Math.sin(t * s.driftRateY + s.driftSeedY);
          el.setAttribute('cx', (s.x + dx).toFixed(2));
          el.setAttribute('cy', (s.y + dy).toFixed(2));
        });
      }
      rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafRef.current);
  }, [stars]);

  return (
    <svg ref={svgRef}
         width={size.w} height={size.h}
         viewBox={`0 0 ${size.w} ${size.h}`}
         style={{
           position: 'fixed', inset: 0, zIndex: 0,
           pointerEvents: 'none',
         }}
         aria-hidden="true">
      {stars.map((s, i) => (
        <circle key={i} cx={s.x} cy={s.y} r={s.size}
                fill={ink} data-twinkle=""
                opacity={(s.floor + s.ceil) / 2} />
      ))}
    </svg>
  );
}

// ── Bottom rail ──────────────────────────────────────────────────────────
function BottomRail({ theme, mono }) {
  return (
    <div style={{
      position: 'absolute', bottom: 24, left: 0, right: 0, zIndex: 2,
      maxWidth: 1440, margin: '0 auto',
      padding: '0 56px',
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      fontFamily: mono, fontSize: 10.5, color: theme.mute,
      letterSpacing: '0.1em', textTransform: 'uppercase',
      pointerEvents: 'none',
    }}>
      <span>Duel Commander · season 2026.1</span>
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
        Scroll
        <span style={{ display: 'inline-block', width: 24, height: 0.5,
                       background: theme.mute }} />
      </span>
      <span>last sync · 12 min ago</span>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
