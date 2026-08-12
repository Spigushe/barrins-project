// pages.jsx — inner-page mockups for tolaria_news architecture preview.
// Uses the same design tokens as the landing banner. Med-fidelity layouts —
// real components, stub data, no live API.

const ACCENT = '#7BE0D6';
const INK = '#F0EAD6';
const MUTE = 'rgba(240,234,214,0.62)';
const DIM = 'rgba(240,234,214,0.38)';
const LINE = 'rgba(240,234,214,0.10)';
const BG = '#0B1220';
const BG2 = '#0E1830';

const SERIF = `'EB Garamond', Georgia, serif`;
const SANS  = `'Geist', ui-sans-serif, system-ui, sans-serif`;
const MONO  = `'JetBrains Mono', ui-monospace, monospace`;

// ── Shared chrome ──────────────────────────────────────────────────────────

function PageFrame({ id, label, children }) {
  return (
    <article id={id} data-screen-label={label} style={{
      position: 'relative',
      maxWidth: 1440,
      margin: '0 auto 96px',
      padding: '32px 56px 56px',
      background: BG,
      border: `0.5px solid ${LINE}`,
      borderRadius: 18,
      overflow: 'hidden',
    }}>
      <div style={{
        position: 'absolute', inset: 0, pointerEvents: 'none',
        background: `radial-gradient(700px 400px at 15% 25%, ${ACCENT}12, transparent 70%),
                     radial-gradient(500px 300px at 85% 75%, ${BG2}, transparent 65%)`,
      }} />
      <PageMarker label={label} />
      <div style={{ position: 'relative', zIndex: 1 }}>
        {children}
      </div>
    </article>
  );
}

function PageMarker({ label }) {
  return (
    <div style={{
      position: 'absolute', top: 20, right: 24, zIndex: 2,
      fontFamily: MONO, fontSize: 10.5,
      color: DIM, letterSpacing: '0.1em', textTransform: 'uppercase',
    }}>
      <span style={{ color: ACCENT }}>◆</span> {label}
    </div>
  );
}

function Nav({ active }) {
  const links = ['Metagame', 'Archetypes', 'Decklists', 'Tournaments', 'Trends'];
  return (
    <header style={{
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      paddingBottom: 22, borderBottom: `0.5px solid ${LINE}`, marginBottom: 36,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <Sigil />
        <span style={{ fontFamily: SERIF, fontSize: 19, fontStyle: 'italic',
                       letterSpacing: '-0.01em', color: INK }}>
          Barrin&apos;s Project
        </span>
      </div>
      <nav style={{ display: 'flex', gap: 28 }}>
        {links.map((l) => (
          <span key={l} style={{
            color: l === active ? INK : MUTE,
            fontSize: 13.5, fontFamily: SANS,
            position: 'relative',
            paddingBottom: 2,
            borderBottom: l === active ? `0.5px solid ${ACCENT}` : 'none',
          }}>
            {l}
          </span>
        ))}
      </nav>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <span style={{ fontFamily: MONO, fontSize: 11, color: MUTE }}>⌘K</span>
        <span style={{
          fontFamily: SANS, fontSize: 13, color: INK,
          border: `0.5px solid ${LINE}`, padding: '8px 14px', borderRadius: 8,
        }}>Sign in</span>
      </div>
    </header>
  );
}

function Sigil() {
  return (
    <svg width="28" height="28" viewBox="0 0 28 28">
      <circle cx="14" cy="14" r="12" fill="none" stroke={INK} strokeOpacity="0.4" strokeWidth="0.6" />
      <circle cx="14" cy="14" r="7"  fill="none" stroke={INK} strokeOpacity="0.6" strokeWidth="0.6" />
      <path d="M14 4 L24 14 L14 24 L4 14 Z" fill="none" stroke={ACCENT} strokeWidth="0.9" />
      <circle cx="14" cy="14" r="2.2" fill={ACCENT} />
    </svg>
  );
}

function Eyebrow({ children }) {
  return (
    <div style={{
      display: 'inline-flex', alignItems: 'center', gap: 10,
      padding: '6px 11px 6px 9px',
      border: `0.5px solid ${LINE}`,
      borderRadius: 999,
      background: 'rgba(255,255,255,0.03)',
      fontFamily: MONO, fontSize: 11,
      letterSpacing: '0.04em', color: MUTE,
    }}>
      <span style={{ width: 6, height: 6, borderRadius: '50%',
                     background: ACCENT, boxShadow: `0 0 8px ${ACCENT}` }} />
      {children}
    </div>
  );
}

function H1({ children, em }) {
  return (
    <h1 style={{
      fontFamily: SERIF, fontWeight: 400, margin: '24px 0 36px',
      fontSize: 40, lineHeight: 1.2, letterSpacing: '-0.02em', color: INK,
      textWrap: 'pretty',
    }}>
      {children}{em && <em style={{ color: ACCENT, fontStyle: 'italic', fontFamily: SERIF }}> {em}</em>}
    </h1>
  );
}

function Sub({ children }) {
  return (
    <p style={{ fontFamily: SANS, fontSize: 15.5, lineHeight: 1.55,
                color: MUTE, maxWidth: 640, margin: '0 0 32px',
                textWrap: 'pretty' }}>
      {children}
    </p>
  );
}

function Pip({ c }) {
  const map = { W: '#F4ECD6', U: '#7BC9E0', B: '#3A2F4A', R: '#E08A6A', G: '#7BB57A' };
  return <span style={{ display: 'inline-block', width: 8, height: 8,
                        borderRadius: '50%', background: map[c] || INK,
                        boxShadow: c === 'B' ? `0 0 0 0.5px ${MUTE}` : 'none' }} />;
}
function Pips({ colors }) {
  return (
    <span style={{ display: 'inline-flex', gap: 3 }}>
      {colors.split('').map((c, i) => <Pip key={i} c={c} />)}
    </span>
  );
}

function Stat({ n, l }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      <span style={{ fontFamily: SERIF, fontSize: 28, lineHeight: 1,
                     letterSpacing: '-0.02em', color: INK }}>{n}</span>
      <span style={{ fontFamily: MONO, fontSize: 10.5, color: MUTE,
                     textTransform: 'uppercase', letterSpacing: '0.12em' }}>{l}</span>
    </div>
  );
}

function Delta({ v }) {
  const pos = v > 0;
  return (
    <span style={{ fontFamily: MONO, fontSize: 12,
                   color: pos ? ACCENT : '#E08A6A',
                   fontVariantNumeric: 'tabular-nums' }}>
      {pos ? '+' : ''}{v.toFixed(1)}%
    </span>
  );
}

function Filter({ active, children }) {
  return (
    <span style={{
      fontFamily: SANS, fontSize: 12.5,
      padding: '6px 12px', borderRadius: 999,
      border: `0.5px solid ${active ? INK + '55' : LINE}`,
      color: active ? INK : MUTE,
      background: active ? 'rgba(240,234,214,0.05)' : 'transparent',
    }}>{children}</span>
  );
}

function Sparkline({ data, w = 80, h = 24, stroke = ACCENT }) {
  const max = Math.max(...data), min = Math.min(...data);
  const r = max - min || 1;
  const pts = data.map((v, i) => {
    const x = (i / (data.length - 1)) * w;
    const y = h - ((v - min) / r) * h;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(' ');
  return (
    <svg width={w} height={h} style={{ display: 'block' }}>
      <polyline points={pts} fill="none" stroke={stroke} strokeWidth="1.2"
                strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function Bar({ pct, color = ACCENT }) {
  return (
    <div style={{ width: '100%', height: 4, background: 'rgba(240,234,214,0.06)',
                  borderRadius: 999, overflow: 'hidden' }}>
      <div style={{ width: `${pct}%`, height: '100%', background: color,
                    boxShadow: `0 0 6px ${color}66` }} />
    </div>
  );
}

// ── 01 — METAGAME ──────────────────────────────────────────────────────────

const METAGAME_ROWS = [
  { name: 'Tymna / Thrasios — value', colors: 'WUBG', share: 11.4, delta: +1.2, wr: 56.3, n: 1842, spark: [3, 4, 4, 5, 6, 7, 8, 9] },
  { name: 'Rograkh / Silas — stax',   colors: 'WUBR', share: 8.1,  delta: -0.4, wr: 53.1, n: 1320, spark: [9, 8, 8, 7, 7, 7, 7, 8] },
  { name: 'Sisay, Weatherlight',      colors: 'WUBRG', share: 7.6,  delta: +2.1, wr: 54.8, n: 1244, spark: [4, 5, 5, 6, 6, 7, 8, 9] },
  { name: 'Korvold, Fae-Cursed King', colors: 'BRG',  share: 6.2,  delta: -1.8, wr: 51.0, n: 1014, spark: [8, 8, 7, 7, 6, 6, 5, 5] },
  { name: 'Najeela, the Blade-Blossom', colors: 'WUBRG', share: 5.5, delta: +0.9, wr: 55.2, n: 901,  spark: [5, 5, 5, 6, 6, 6, 7, 7] },
  { name: 'Krark / Sakashima — combo', colors: 'UBR',  share: 4.9,  delta: -0.6, wr: 50.4, n: 802,  spark: [6, 6, 5, 5, 5, 5, 5, 5] },
  { name: 'Yuriko, the Tiger\u2019s Shadow',     colors: 'UB',   share: 4.3,  delta: +0.3, wr: 52.7, n: 705,  spark: [4, 4, 4, 4, 5, 4, 4, 5] },
  { name: 'Kraum / Tymna — bant',     colors: 'WUBG', share: 3.9,  delta: -0.2, wr: 49.1, n: 638,  spark: [4, 4, 4, 4, 4, 4, 4, 4] },
];

function MetagamePage() {
  return (
    <PageFrame id="page-metagame" label="/metagame">
      <Nav active="Metagame" />
      <Eyebrow>Metagame · last 30 days</Eyebrow>
      <H1 em="now.">The format,</H1>
      <Sub>
        Snapshot of every sanctioned Duel Commander event in the last 30 days.
        Filter by time window or tournament tier to drill in.
      </Sub>

      {/* Filter row */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 28 }}>
        <Filter>Window · 7d</Filter>
        <Filter active>Window · 30d</Filter>
        <Filter>Window · 90d</Filter>
        <Filter>Window · season</Filter>
        <span style={{ width: 16 }} />
        <Filter active>All tiers</Filter>
        <Filter>Mid+ only</Filter>
        <Filter>Top 8 only</Filter>
      </div>

      {/* Hero stats */}
      <div style={{
        display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 24,
        padding: '28px 0', borderTop: `0.5px solid ${LINE}`,
        borderBottom: `0.5px solid ${LINE}`, marginBottom: 36,
      }}>
        <Stat n="284" l="tournaments" />
        <Stat n="14,820" l="decklists" />
        <Stat n="11.4%" l="top archetype share" />
        <Stat n="52.4%" l="meta winrate (top tier)" />
      </div>

      {/* Two-column main */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.7fr 1fr', gap: 48 }}>
        {/* Archetype table */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between',
                        alignItems: 'baseline', marginBottom: 14 }}>
            <h3 style={{ fontFamily: SERIF, fontWeight: 400, fontSize: 22,
                         margin: 0, color: INK }}>Archetype share</h3>
            <span style={{ fontFamily: MONO, fontSize: 10.5, color: MUTE,
                           letterSpacing: '0.08em', textTransform: 'uppercase' }}>
              sorted by share ↓
            </span>
          </div>
          <table style={{ width: '100%', borderCollapse: 'collapse',
                          fontFamily: SANS, fontSize: 13.5 }}>
            <thead>
              <tr style={{ color: MUTE, fontFamily: MONO, fontSize: 10.5,
                           textTransform: 'uppercase', letterSpacing: '0.1em' }}>
                <th style={{ textAlign: 'left', padding: '8px 0',
                             borderBottom: `0.5px solid ${LINE}` }}>Archetype</th>
                <th style={{ textAlign: 'right', padding: '8px 0',
                             borderBottom: `0.5px solid ${LINE}` }}>Share</th>
                <th style={{ textAlign: 'right', padding: '8px 0',
                             borderBottom: `0.5px solid ${LINE}` }}>Δ</th>
                <th style={{ textAlign: 'right', padding: '8px 0',
                             borderBottom: `0.5px solid ${LINE}` }}>WR</th>
                <th style={{ textAlign: 'right', padding: '8px 0',
                             borderBottom: `0.5px solid ${LINE}` }}>n</th>
                <th style={{ textAlign: 'right', padding: '8px 0',
                             borderBottom: `0.5px solid ${LINE}`, width: 100 }}>Trend</th>
              </tr>
            </thead>
            <tbody>
              {METAGAME_ROWS.map((r) => (
                <tr key={r.name} style={{ borderBottom: `0.5px solid ${LINE}` }}>
                  <td style={{ padding: '14px 0', color: INK }}>
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 10 }}>
                      <Pips colors={r.colors} />
                      <span style={{ fontFamily: SERIF, fontStyle: 'italic',
                                     fontSize: 16 }}>{r.name}</span>
                    </span>
                  </td>
                  <td style={{ textAlign: 'right', fontFamily: MONO,
                               fontVariantNumeric: 'tabular-nums', color: INK }}>
                    {r.share.toFixed(1)}%
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <Delta v={r.delta} />
                  </td>
                  <td style={{ textAlign: 'right', fontFamily: MONO,
                               fontVariantNumeric: 'tabular-nums', color: MUTE }}>
                    {r.wr.toFixed(1)}%
                  </td>
                  <td style={{ textAlign: 'right', fontFamily: MONO,
                               fontVariantNumeric: 'tabular-nums', color: MUTE }}>
                    {r.n.toLocaleString()}
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <div style={{ display: 'inline-block' }}>
                      <Sparkline data={r.spark}
                                 stroke={r.delta >= 0 ? ACCENT : '#E08A6A'} />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Color distribution */}
        <div>
          <h3 style={{ fontFamily: SERIF, fontWeight: 400, fontSize: 22,
                       margin: '0 0 14px', color: INK }}>Color identity</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {[
              { c: 'U', name: 'Blue',  pct: 71 },
              { c: 'W', name: 'White', pct: 64 },
              { c: 'B', name: 'Black', pct: 58 },
              { c: 'G', name: 'Green', pct: 42 },
              { c: 'R', name: 'Red',   pct: 38 },
            ].map((x) => (
              <div key={x.c}>
                <div style={{ display: 'flex', justifyContent: 'space-between',
                              alignItems: 'baseline', marginBottom: 6,
                              fontFamily: MONO, fontSize: 11 }}>
                  <span style={{ color: INK }}>
                    <Pip c={x.c} /> &nbsp;{x.name}
                  </span>
                  <span style={{ color: MUTE,
                                 fontVariantNumeric: 'tabular-nums' }}>{x.pct}%</span>
                </div>
                <Bar pct={x.pct} />
              </div>
            ))}
          </div>

          <h3 style={{ fontFamily: SERIF, fontWeight: 400, fontSize: 22,
                       margin: '32px 0 14px', color: INK }}>Top movers</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {[
              { name: 'Sisay, Weatherlight', d: +2.1 },
              { name: 'Tymna / Thrasios',    d: +1.2 },
              { name: 'Korvold, Fae-Cursed', d: -1.8 },
              { name: 'Rograkh / Silas',     d: -0.4 },
            ].map((m) => (
              <div key={m.name} style={{
                display: 'flex', justifyContent: 'space-between',
                alignItems: 'center', padding: '10px 12px',
                border: `0.5px solid ${LINE}`, borderRadius: 8,
                fontFamily: SANS, fontSize: 13.5, color: INK,
              }}>
                <span>{m.name}</span>
                <Delta v={m.d} />
              </div>
            ))}
          </div>
        </div>
      </div>
    </PageFrame>
  );
}

// ── 02 — ARCHETYPES ────────────────────────────────────────────────────────

const ARCHETYPE_CARDS = [
  { name: 'Tymna / Thrasios', strat: 'value · midrange', colors: 'WUBG',
    staples: ['Mystic Remora', 'Rhystic Study', 'Force of Will', 'Swords to Plowshares'],
    share: 11.4, wr: 56.3, n: 1842 },
  { name: 'Rograkh / Silas Renn', strat: 'stax · prison', colors: 'WUBR',
    staples: ['Trinisphere', 'Sphere of Resistance', 'Chrome Mox', 'Mox Diamond'],
    share: 8.1, wr: 53.1, n: 1320 },
  { name: 'Sisay, Weatherlight', strat: 'toolbox · combo', colors: 'WUBRG',
    staples: ['Bring to Light', 'Yisan, the Wanderer Bard', 'Karn, the Great Creator', 'Capsize'],
    share: 7.6, wr: 54.8, n: 1244 },
  { name: 'Najeela, the Blade-Blossom', strat: 'combo · creature', colors: 'WUBRG',
    staples: ['Derevi, Empyrial Tactician', 'Tana, the Bloodsower', 'Cryptolith Rite', 'Druids\u2019 Repository'],
    share: 5.5, wr: 55.2, n: 901 },
  { name: 'Yuriko, the Tiger\u2019s Shadow', strat: 'aggro · tempo', colors: 'UB',
    staples: ['Ninja of the Deep Hours', 'Fallen Shinobi', 'Bitterblossom', 'Force of Negation'],
    share: 4.3, wr: 52.7, n: 705 },
  { name: 'Krark / Sakashima', strat: 'combo · storm', colors: 'UBR',
    staples: ['Krark\u2019s Thumb', 'Sakashima of a Thousand Faces', 'Underworld Breach', 'Lion\u2019s Eye Diamond'],
    share: 4.9, wr: 50.4, n: 802 },
];

function ArchetypesPage() {
  return (
    <PageFrame id="page-archetypes" label="/archetypes">
      <Nav active="Archetypes" />
      <Eyebrow>412 archetypes mapped</Eyebrow>
      <H1 em="core.">Every archetype, traced to its</H1>
      <Sub>
        Decks clustered by commander, color identity, and shared card pool.
        Open any archetype to see its staples, representative lists, and meta history.
      </Sub>

      {/* Search bar */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 12,
        padding: '14px 18px', border: `0.5px solid ${LINE}`,
        borderRadius: 12, background: 'rgba(255,255,255,0.02)',
        marginBottom: 36, maxWidth: 720,
      }}>
        <span style={{ fontFamily: MONO, fontSize: 12, color: DIM }}>⌘K</span>
        <span style={{ fontFamily: SANS, fontSize: 14, color: MUTE }}>
          Search by commander, color, or strategy…
        </span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '220px 1fr', gap: 48 }}>
        {/* Filter rail */}
        <aside>
          <FilterGroup label="Color identity">
            {['W', 'U', 'B', 'R', 'G'].map((c) => (
              <div key={c} style={{ display: 'flex', alignItems: 'center', gap: 10,
                                    padding: '6px 0',
                                    fontFamily: SANS, fontSize: 13, color: MUTE }}>
                <span style={{ width: 14, height: 14, border: `0.5px solid ${LINE}`,
                               borderRadius: 3 }} />
                <Pip c={c} />
                {' '}{ {W:'White',U:'Blue',B:'Black',R:'Red',G:'Green'}[c] }
              </div>
            ))}
          </FilterGroup>
          <FilterGroup label="Strategy">
            {['Control', 'Aggro', 'Midrange', 'Combo', 'Stax', 'Tempo'].map((s) => (
              <div key={s} style={{ display: 'flex', alignItems: 'center', gap: 10,
                                    padding: '6px 0',
                                    fontFamily: SANS, fontSize: 13, color: MUTE }}>
                <span style={{ width: 14, height: 14, border: `0.5px solid ${LINE}`,
                               borderRadius: 3 }} />
                {s}
              </div>
            ))}
          </FilterGroup>
          <FilterGroup label="Commander">
            <div style={{ fontFamily: SANS, fontSize: 13, color: MUTE, padding: '6px 0' }}>
              ○ Solo
            </div>
            <div style={{ fontFamily: SANS, fontSize: 13, color: INK, padding: '6px 0' }}>
              ● Partner pair
            </div>
            <div style={{ fontFamily: SANS, fontSize: 13, color: MUTE, padding: '6px 0' }}>
              ○ Background
            </div>
          </FilterGroup>
          <FilterGroup label="Min. sample size">
            <div style={{ fontFamily: MONO, fontSize: 11, color: MUTE,
                          display: 'flex', justifyContent: 'space-between' }}>
              <span>0</span><span style={{ color: INK }}>250+</span><span>2000</span>
            </div>
            <div style={{ marginTop: 6 }}><Bar pct={32} /></div>
          </FilterGroup>
        </aside>

        {/* Card grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 18 }}>
          {ARCHETYPE_CARDS.map((a) => (
            <div key={a.name} style={{
              padding: '20px 22px',
              border: `0.5px solid ${LINE}`, borderRadius: 14,
              background: 'rgba(255,255,255,0.015)',
              display: 'flex', flexDirection: 'column', gap: 14,
            }}>
              <div style={{ display: 'flex', alignItems: 'flex-start',
                            justifyContent: 'space-between', gap: 12 }}>
                <div style={{ flex: 1 }}>
                  <Pips colors={a.colors} />
                  <h4 style={{ fontFamily: SERIF, fontWeight: 400, fontSize: 19,
                               margin: '6px 0 6px', color: INK,
                               letterSpacing: '-0.01em', lineHeight: 1.2 }}>
                    {a.name}
                  </h4>
                  <div style={{ fontFamily: MONO, fontSize: 10.5, color: MUTE,
                                 letterSpacing: '0.08em', textTransform: 'uppercase' }}>
                    {a.strat}
                  </div>
                </div>
                <Delta v={a.share} />
              </div>

              <div style={{ fontFamily: MONO, fontSize: 11.5, color: MUTE,
                            lineHeight: 1.7 }}>
                {a.staples.map((s, i) => (
                  <div key={i}>· {s}</div>
                ))}
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between',
                            borderTop: `0.5px solid ${LINE}`, paddingTop: 12 }}>
                <MiniStat label="share" v={`${a.share}%`} />
                <MiniStat label="winrate" v={`${a.wr}%`} />
                <MiniStat label="samples" v={a.n.toLocaleString()} />
              </div>
            </div>
          ))}
        </div>
      </div>
    </PageFrame>
  );
}

function FilterGroup({ label, children }) {
  return (
    <div style={{ marginBottom: 24 }}>
      <div style={{ fontFamily: MONO, fontSize: 10, color: DIM,
                    textTransform: 'uppercase', letterSpacing: '0.12em',
                    marginBottom: 8 }}>{label}</div>
      {children}
    </div>
  );
}

function MiniStat({ label, v }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      <span style={{ fontFamily: SERIF, fontSize: 16, color: INK }}>{v}</span>
      <span style={{ fontFamily: MONO, fontSize: 9.5, color: MUTE,
                     textTransform: 'uppercase', letterSpacing: '0.12em' }}>{label}</span>
    </div>
  );
}

// ── 03 — DECKLISTS ─────────────────────────────────────────────────────────

const DECKLISTS = [
  { pilot: 'Lucas Maréchal',  pair: 'Tymna / Thrasios',     archetype: 'WUBG · value',  tournament: 'DC Masters Paris',  date: '2026-05-04', place: '1st' },
  { pilot: 'Hiroshi Tanaka',  pair: 'Sisay, Weatherlight',  archetype: '5C · toolbox',   tournament: 'Tokyo Open',        date: '2026-05-03', place: '2nd' },
  { pilot: 'Anna Schneider',  pair: 'Rograkh / Silas',      archetype: 'WUBR · stax',    tournament: 'Berlin Invitational', date: '2026-04-28', place: '1st' },
  { pilot: 'Marc Dubois',     pair: 'Najeela, Blade-Blossom', archetype: '5C · combo',  tournament: 'Lyon Cup',          date: '2026-04-27', place: '3rd' },
  { pilot: 'Sofia Ricci',     pair: 'Yuriko, Tiger\u2019s Shadow', archetype: 'UB · ninjas', tournament: 'Milan Classic',   date: '2026-04-26', place: 'Top 4' },
  { pilot: 'Thomas Allard',   pair: 'Krark / Sakashima',    archetype: 'UBR · storm',    tournament: 'DC Masters Paris',  date: '2026-05-04', place: '4th' },
  { pilot: 'Klara Novak',     pair: 'Korvold, Fae-Cursed',  archetype: 'BRG · sacrifice', tournament: 'Prague Open',     date: '2026-04-21', place: '1st' },
  { pilot: 'Olivier Béland',  pair: 'Kraum / Tymna',        archetype: 'WUBG · control', tournament: 'Montréal Series',   date: '2026-04-19', place: '2nd' },
];

function DecklistsPage() {
  return (
    <PageFrame id="page-decklists" label="/decklists">
      <Nav active="Decklists" />
      <Eyebrow>96,231 decklists indexed</Eyebrow>
      <H1 em="result.">Every list. Every</H1>
      <Sub>
        The full searchable corpus of indexed Duel Commander decklists.
        Drill in by pilot, commander, or tournament — every list keeps its full event context.
      </Sub>

      {/* Search */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 12,
        padding: '14px 18px', border: `0.5px solid ${LINE}`,
        borderRadius: 12, background: 'rgba(255,255,255,0.02)',
        marginBottom: 20, maxWidth: 820,
      }}>
        <span style={{ fontFamily: MONO, fontSize: 12, color: DIM }}>⌘K</span>
        <span style={{ fontFamily: MONO, fontSize: 13, color: INK }}>
          commander:tymna
        </span>
        <span style={{ fontFamily: MONO, fontSize: 13, color: MUTE }}>
          color:WUBG&nbsp;&nbsp;tournament:paris
        </span>
        <span style={{ flex: 1 }} />
        <span style={{ fontFamily: MONO, fontSize: 10.5, color: DIM,
                       letterSpacing: '0.08em', textTransform: 'uppercase' }}>
          1,284 results
        </span>
      </div>

      {/* Filter pills */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 28 }}>
        <Filter active>Last 30 days</Filter>
        <Filter>Last 90 days</Filter>
        <Filter>All time</Filter>
        <span style={{ width: 12 }} />
        <Filter active>Top 8 only</Filter>
        <Filter>Top 16</Filter>
        <Filter>All placements</Filter>
        <span style={{ width: 12 }} />
        <Filter>Color: WUBG</Filter>
        <Filter>+ Add filter</Filter>
      </div>

      {/* Table */}
      <table style={{ width: '100%', borderCollapse: 'collapse',
                      fontFamily: SANS, fontSize: 13.5 }}>
        <thead>
          <tr style={{ color: MUTE, fontFamily: MONO, fontSize: 10.5,
                       textTransform: 'uppercase', letterSpacing: '0.1em' }}>
            <th style={{ textAlign: 'left', padding: '10px 0',
                         borderBottom: `0.5px solid ${LINE}` }}>Pilot</th>
            <th style={{ textAlign: 'left', padding: '10px 0',
                         borderBottom: `0.5px solid ${LINE}` }}>Commander</th>
            <th style={{ textAlign: 'left', padding: '10px 0',
                         borderBottom: `0.5px solid ${LINE}` }}>Archetype</th>
            <th style={{ textAlign: 'left', padding: '10px 0',
                         borderBottom: `0.5px solid ${LINE}` }}>Tournament</th>
            <th style={{ textAlign: 'right', padding: '10px 0',
                         borderBottom: `0.5px solid ${LINE}` }}>Date</th>
            <th style={{ textAlign: 'right', padding: '10px 0',
                         borderBottom: `0.5px solid ${LINE}` }}>Place</th>
          </tr>
        </thead>
        <tbody>
          {DECKLISTS.map((d, i) => (
            <tr key={i} style={{ borderBottom: `0.5px solid ${LINE}` }}>
              <td style={{ padding: '14px 0', color: INK }}>{d.pilot}</td>
              <td style={{ color: INK, fontFamily: SERIF, fontStyle: 'italic',
                           fontSize: 15 }}>{d.pair}</td>
              <td style={{ color: MUTE }}>{d.archetype}</td>
              <td style={{ color: MUTE }}>{d.tournament}</td>
              <td style={{ textAlign: 'right', fontFamily: MONO,
                           color: MUTE, fontVariantNumeric: 'tabular-nums' }}>
                {d.date}
              </td>
              <td style={{ textAlign: 'right' }}>
                <span style={{
                  fontFamily: MONO, fontSize: 11.5,
                  padding: '3px 8px', borderRadius: 4,
                  background: d.place === '1st' ? ACCENT : 'transparent',
                  color: d.place === '1st' ? '#0B1220' : MUTE,
                  border: d.place === '1st' ? 'none' : `0.5px solid ${LINE}`,
                  letterSpacing: '0.04em',
                }}>{d.place}</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div style={{ display: 'flex', justifyContent: 'space-between',
                    alignItems: 'center', marginTop: 24,
                    fontFamily: MONO, fontSize: 11, color: MUTE,
                    letterSpacing: '0.08em', textTransform: 'uppercase' }}>
        <span>Page 1 of 161</span>
        <span style={{ display: 'flex', gap: 8 }}>
          <span style={{ padding: '6px 12px', border: `0.5px solid ${LINE}`,
                         borderRadius: 6, color: DIM }}>← prev</span>
          <span style={{ padding: '6px 12px', border: `0.5px solid ${LINE}`,
                         borderRadius: 6, color: INK }}>next →</span>
        </span>
      </div>
    </PageFrame>
  );
}

// ── 04 — TOURNAMENTS ───────────────────────────────────────────────────────

const TOURNAMENTS = [
  { name: 'DC Masters Paris',   date: 'May 4, 2026',  loc: 'Paris, FR',    players: 248, status: 'past',     winner: 'Tymna / Thrasios' },
  { name: 'Tokyo Open',         date: 'May 3, 2026',  loc: 'Tokyo, JP',    players: 192, status: 'past',     winner: 'Sisay, Weatherlight' },
  { name: 'Berlin Invitational', date: 'Apr 28, 2026', loc: 'Berlin, DE', players: 156, status: 'past',     winner: 'Rograkh / Silas' },
  { name: 'Lyon Cup',           date: 'Apr 27, 2026', loc: 'Lyon, FR',     players: 128, status: 'past',     winner: 'Najeela' },
  { name: 'Madrid Championship', date: 'May 23, 2026', loc: 'Madrid, ES', players: null, status: 'upcoming', winner: null },
  { name: 'DC World Series',    date: 'Jun 12, 2026', loc: 'Amsterdam, NL', players: null, status: 'upcoming', winner: null },
];

function TournamentsPage() {
  return (
    <PageFrame id="page-tournaments" label="/tournaments">
      <Nav active="Tournaments" />
      <Eyebrow>Duel Commander · Tournaments</Eyebrow>
      <H1 em="decided.">Where the format gets</H1>
      <Sub>
        Past events with full standings and meta breakdowns, plus a calendar
        of upcoming sanctioned Duel Commander tournaments worldwide.
      </Sub>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 24, borderBottom: `0.5px solid ${LINE}`,
                    marginBottom: 32 }}>
        <TabHead active>Recent</TabHead>
        <TabHead>Upcoming</TabHead>
        <TabHead>By region</TabHead>
        <TabHead>Calendar</TabHead>
      </div>

      {/* Featured */}
      <div style={{
        padding: 28, border: `0.5px solid ${LINE}`, borderRadius: 14,
        background: `linear-gradient(135deg, rgba(123,224,214,0.04), transparent 60%)`,
        marginBottom: 32,
        display: 'grid', gridTemplateColumns: '1.5fr 1fr', gap: 32,
      }}>
        <div>
          <span style={{ fontFamily: MONO, fontSize: 10.5, color: ACCENT,
                         letterSpacing: '0.12em', textTransform: 'uppercase' }}>
            ◆ Featured · most recent major
          </span>
          <h2 style={{ fontFamily: SERIF, fontWeight: 400, fontSize: 38,
                       margin: '10px 0 6px', color: INK,
                       letterSpacing: '-0.02em' }}>
            DC Masters Paris
          </h2>
          <div style={{ fontFamily: MONO, fontSize: 11.5, color: MUTE,
                        letterSpacing: '0.06em' }}>
            May 4, 2026 · Paris, FR · 248 players · 9 rounds + top 8
          </div>
          <div style={{ marginTop: 24, display: 'flex', gap: 32 }}>
            <Stat n="11.4%" l="winning archetype" />
            <Stat n="32" l="distinct archetypes" />
            <Stat n="73%" l="conversion top 8" />
          </div>
        </div>
        <div>
          <span style={{ fontFamily: MONO, fontSize: 10, color: DIM,
                         letterSpacing: '0.12em', textTransform: 'uppercase' }}>
            Top 4
          </span>
          <ol style={{ margin: '12px 0 0', padding: 0, listStyle: 'none',
                       display: 'flex', flexDirection: 'column', gap: 10 }}>
            {[
              { p: '1', name: 'L. Maréchal', deck: 'Tymna / Thrasios' },
              { p: '2', name: 'C. Bernard',  deck: 'Sisay, Weatherlight' },
              { p: '3', name: 'M. Dubois',   deck: 'Najeela' },
              { p: '4', name: 'T. Allard',   deck: 'Krark / Sakashima' },
            ].map((r) => (
              <li key={r.p} style={{ display: 'flex', alignItems: 'baseline', gap: 14,
                                     fontFamily: SANS, fontSize: 14, color: INK }}>
                <span style={{ fontFamily: MONO, fontSize: 11, color: ACCENT,
                               width: 18 }}>{r.p}.</span>
                <span style={{ flex: 1 }}>{r.name}</span>
                <span style={{ fontFamily: SERIF, fontStyle: 'italic', color: MUTE,
                               fontSize: 14 }}>{r.deck}</span>
              </li>
            ))}
          </ol>
        </div>
      </div>

      {/* Grid of cards */}
      <h3 style={{ fontFamily: SERIF, fontWeight: 400, fontSize: 22,
                   margin: '0 0 14px', color: INK }}>All events</h3>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
        {TOURNAMENTS.map((t) => (
          <div key={t.name} style={{
            padding: 18, border: `0.5px solid ${LINE}`, borderRadius: 12,
            display: 'flex', flexDirection: 'column', gap: 8,
            opacity: t.status === 'upcoming' ? 0.85 : 1,
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between',
                          alignItems: 'baseline' }}>
              <h4 style={{ fontFamily: SERIF, fontWeight: 400, fontSize: 19,
                           margin: 0, color: INK }}>{t.name}</h4>
              <span style={{
                fontFamily: MONO, fontSize: 9.5,
                color: t.status === 'upcoming' ? ACCENT : MUTE,
                padding: '2px 7px',
                border: `0.5px solid ${t.status === 'upcoming' ? ACCENT + '88' : LINE}`,
                borderRadius: 4, textTransform: 'uppercase', letterSpacing: '0.1em',
              }}>{t.status}</span>
            </div>
            <div style={{ fontFamily: MONO, fontSize: 11, color: MUTE,
                          letterSpacing: '0.04em' }}>
              {t.date} · {t.loc}{t.players ? ` · ${t.players} players` : ''}
            </div>
            {t.winner && (
              <div style={{ marginTop: 4, paddingTop: 10,
                            borderTop: `0.5px solid ${LINE}`,
                            fontSize: 12.5, color: INK }}>
                <span style={{ color: MUTE }}>Winner: </span>
                <span style={{ fontFamily: SERIF, fontStyle: 'italic' }}>{t.winner}</span>
              </div>
            )}
          </div>
        ))}
      </div>
    </PageFrame>
  );
}

function TabHead({ active, children }) {
  return (
    <span style={{
      fontFamily: SANS, fontSize: 14, padding: '0 0 12px',
      color: active ? INK : MUTE,
      borderBottom: active ? `1px solid ${ACCENT}` : 'none',
      marginBottom: -0.5,
    }}>{children}</span>
  );
}

// ── 05 — TRENDS ────────────────────────────────────────────────────────────

function TrendsPage() {
  // Generate a fake stacked-area dataset
  const months = ['Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar', 'Apr', 'May'];
  const series = [
    { name: 'Tymna / Thrasios',     color: '#7BE0D6', data: [9.1, 9.4, 9.8, 10.2, 10.5, 10.4, 10.6, 10.9, 11.1, 10.8, 11.2, 11.4] },
    { name: 'Sisay, Weatherlight',  color: '#C7A455', data: [3.0, 3.2, 3.6, 4.2, 4.8, 5.4, 5.9, 6.3, 6.9, 7.1, 7.4, 7.6] },
    { name: 'Rograkh / Silas',      color: '#8FA8FF', data: [8.8, 8.7, 8.6, 8.5, 8.4, 8.3, 8.4, 8.3, 8.2, 8.2, 8.1, 8.1] },
    { name: 'Korvold',              color: '#E08A6A', data: [4.6, 4.8, 5.1, 5.6, 6.4, 7.1, 7.5, 7.8, 7.4, 7.0, 6.5, 6.2] },
    { name: 'Najeela',              color: '#A78BFA', data: [3.8, 4.0, 4.3, 4.5, 4.6, 4.8, 5.0, 5.1, 5.3, 5.4, 5.5, 5.5] },
  ];

  return (
    <PageFrame id="page-trends" label="/trends">
      <Nav active="Trends" />
      <Eyebrow>Research · Trends · forecasts</Eyebrow>
      <H1 em="time.">The metagame, over</H1>
      <Sub>
        Twelve-month time-series of archetype share, card inclusion rates,
        and four-week projections sourced from the ML models powering Barrin&apos;s Project.
      </Sub>

      {/* Controls */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 24 }}>
        <Filter>90 days</Filter>
        <Filter>6 months</Filter>
        <Filter active>12 months</Filter>
        <Filter>All time</Filter>
        <span style={{ width: 16 }} />
        <Filter>Weekly</Filter>
        <Filter active>Monthly</Filter>
      </div>

      {/* Chart 1 — stacked area */}
      <div style={{
        padding: '24px 28px 20px',
        border: `0.5px solid ${LINE}`, borderRadius: 14, marginBottom: 28,
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between',
                      alignItems: 'baseline', marginBottom: 14 }}>
          <h3 style={{ fontFamily: SERIF, fontWeight: 400, fontSize: 22,
                       margin: 0, color: INK }}>Archetype share over time</h3>
          <span style={{ fontFamily: MONO, fontSize: 10.5, color: MUTE,
                         letterSpacing: '0.08em', textTransform: 'uppercase' }}>
            top 5 · monthly
          </span>
        </div>

        <StackedAreaChart months={months} series={series} />

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 18, marginTop: 18 }}>
          {series.map((s) => (
            <div key={s.name} style={{ display: 'flex', alignItems: 'center', gap: 8,
                                       fontFamily: SANS, fontSize: 12.5, color: INK }}>
              <span style={{ width: 10, height: 10, borderRadius: 2, background: s.color }} />
              {s.name}
              <span style={{ color: MUTE, fontFamily: MONO, fontSize: 11 }}>
                {s.data[s.data.length - 1].toFixed(1)}%
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Card inclusion trends */}
      <div style={{
        padding: '24px 28px',
        border: `0.5px solid ${LINE}`, borderRadius: 14, marginBottom: 28,
      }}>
        <h3 style={{ fontFamily: SERIF, fontWeight: 400, fontSize: 22,
                     margin: '0 0 14px', color: INK }}>Card inclusion trends</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 24 }}>
          {[
            { name: 'Mystic Remora',    pct: 78, trend: [70, 72, 73, 75, 76, 78], dir: +8 },
            { name: 'Rhystic Study',    pct: 71, trend: [68, 69, 70, 71, 71, 71], dir: +3 },
            { name: 'Force of Will',    pct: 64, trend: [66, 65, 65, 64, 64, 64], dir: -2 },
            { name: 'Swords to Plowshares', pct: 58, trend: [55, 56, 57, 57, 58, 58], dir: +3 },
            { name: 'Toxic Deluge',     pct: 41, trend: [48, 46, 45, 43, 42, 41], dir: -7 },
            { name: 'Mox Diamond',      pct: 39, trend: [35, 36, 37, 38, 38, 39], dir: +4 },
          ].map((c) => (
            <div key={c.name} style={{
              padding: '14px 16px', border: `0.5px solid ${LINE}`, borderRadius: 10,
              display: 'flex', flexDirection: 'column', gap: 6,
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between',
                            alignItems: 'baseline' }}>
                <span style={{ fontFamily: SERIF, fontStyle: 'italic',
                               fontSize: 15, color: INK }}>{c.name}</span>
                <Delta v={c.dir} />
              </div>
              <div style={{ fontFamily: MONO, fontSize: 22, color: INK,
                            fontVariantNumeric: 'tabular-nums' }}>
                {c.pct}<span style={{ fontSize: 13, color: MUTE }}>%</span>
              </div>
              <Sparkline data={c.trend} w={180} h={28}
                         stroke={c.dir >= 0 ? ACCENT : '#E08A6A'} />
            </div>
          ))}
        </div>
      </div>

      {/* Forecasts */}
      <h3 style={{ fontFamily: SERIF, fontWeight: 400, fontSize: 22,
                   margin: '0 0 6px', color: INK }}>
        4-week forecasts <em style={{ color: ACCENT, fontStyle: 'italic' }}>· beta</em>
      </h3>
      <p style={{ fontFamily: SANS, fontSize: 13.5, color: MUTE,
                  maxWidth: 600, margin: '0 0 18px' }}>
        Projected share shift using the Barrin&apos;s Project meta model.
        Bands show 80% confidence intervals.
      </p>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
        <ForecastCard title="Rising" tone="up"
                      items={[['Sisay, Weatherlight', +1.4],
                              ['Najeela',              +0.8],
                              ['Korvold',              +0.4]]} />
        <ForecastCard title="Falling" tone="down"
                      items={[['Rograkh / Silas',     -0.7],
                              ['Krark / Sakashima',    -0.5],
                              ['Yuriko',               -0.3]]} />
        <ForecastCard title="Stable"  tone="flat"
                      items={[['Tymna / Thrasios',    +0.1],
                              ['Kraum / Tymna',        0.0],
                              ['Edric, Spymaster',    +0.1]]} />
      </div>
    </PageFrame>
  );
}

function ForecastCard({ title, tone, items }) {
  const color = tone === 'up' ? ACCENT : tone === 'down' ? '#E08A6A' : MUTE;
  return (
    <div style={{ padding: '18px 20px', border: `0.5px solid ${LINE}`,
                  borderRadius: 12 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8,
                    marginBottom: 14 }}>
        <span style={{ width: 6, height: 6, borderRadius: '50%',
                       background: color, boxShadow: `0 0 8px ${color}` }} />
        <span style={{ fontFamily: MONO, fontSize: 11, color: INK,
                       textTransform: 'uppercase', letterSpacing: '0.12em' }}>
          {title}
        </span>
      </div>
      <ul style={{ margin: 0, padding: 0, listStyle: 'none',
                   display: 'flex', flexDirection: 'column', gap: 10 }}>
        {items.map(([n, d]) => (
          <li key={n} style={{ display: 'flex', justifyContent: 'space-between',
                               alignItems: 'baseline',
                               fontFamily: SANS, fontSize: 13.5, color: INK }}>
            <span>{n}</span>
            <Delta v={d} />
          </li>
        ))}
      </ul>
    </div>
  );
}

function StackedAreaChart({ months, series }) {
  const W = 1120, H = 280, padL = 36, padR = 0, padT = 8, padB = 28;
  const innerW = W - padL - padR, innerH = H - padT - padB;
  const n = months.length;
  const totals = months.map((_, i) => series.reduce((s, sr) => s + sr.data[i], 0));
  const maxTotal = Math.max(...totals);
  const x = (i) => padL + (i / (n - 1)) * innerW;
  const y = (v) => padT + innerH - (v / maxTotal) * innerH;

  let cumulative = months.map(() => 0);
  const areas = series.map((s) => {
    const top = s.data.map((v, i) => cumulative[i] + v);
    const bot = [...cumulative];
    const d = [
      `M ${x(0)} ${y(top[0])}`,
      ...top.slice(1).map((v, i) => `L ${x(i + 1)} ${y(v)}`),
      ...bot.map((v, i) => `L ${x(n - 1 - i)} ${y(bot[n - 1 - i])}`).reverse(),
      'Z',
    ].join(' ');
    cumulative = top;
    return { d, color: s.color, name: s.name };
  });

  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', display: 'block' }}>
      {/* Y gridlines */}
      {[0, 0.25, 0.5, 0.75, 1].map((p) => (
        <g key={p}>
          <line x1={padL} x2={W - padR}
                y1={padT + innerH * (1 - p)} y2={padT + innerH * (1 - p)}
                stroke={LINE} strokeWidth="0.5" />
          <text x={padL - 8} y={padT + innerH * (1 - p) + 3}
                fill={MUTE} fontSize="10" fontFamily={MONO}
                textAnchor="end">
            {(maxTotal * p).toFixed(0)}%
          </text>
        </g>
      ))}
      {/* Areas */}
      {areas.map((a) => (
        <path key={a.name} d={a.d} fill={a.color} fillOpacity="0.5"
              stroke={a.color} strokeWidth="0.8" />
      ))}
      {/* X labels */}
      {months.map((m, i) => (
        <text key={i} x={x(i)} y={H - 8} fill={MUTE} fontSize="10"
              fontFamily={MONO} textAnchor="middle">{m}</text>
      ))}
    </svg>
  );
}

// ── Site map (top of architecture page) ────────────────────────────────────

function SiteMap() {
  const nodes = [
    { id: '/',             label: 'Landing',          x: 50, y: 5,  desc: 'Hero · CTAs · embedding viz' },
    { id: '/metagame',     label: 'Metagame',         x: 10, y: 35, desc: 'Snapshot · share · winrate' },
    { id: '/archetypes',   label: 'Archetypes',       x: 30, y: 35, desc: 'Cluster cards · filters · search' },
    { id: '/decklists',    label: 'Decklists',        x: 50, y: 35, desc: 'Searchable table · per-deck detail' },
    { id: '/tournaments',  label: 'Tournaments',      x: 70, y: 35, desc: 'Past · upcoming · standings' },
    { id: '/trends',       label: 'Trends',           x: 90, y: 35, desc: 'Time-series · forecasts' },

    { id: '/archetypes/:id',  label: 'Archetype detail', x: 30, y: 70, desc: 'Decklists · cards · trends' },
    { id: '/decklists/:id',   label: 'Decklist detail',  x: 50, y: 70, desc: 'Full list · mana curve · context' },
    { id: '/tournaments/:id', label: 'Tournament page',  x: 70, y: 70, desc: 'Standings · meta breakdown' },
  ];

  const edges = [
    ['/', '/metagame'], ['/', '/archetypes'], ['/', '/decklists'],
    ['/', '/tournaments'], ['/', '/trends'],
    ['/archetypes', '/archetypes/:id'],
    ['/decklists', '/decklists/:id'],
    ['/tournaments', '/tournaments/:id'],
    ['/metagame', '/archetypes/:id'],
    ['/archetypes/:id', '/decklists/:id'],
    ['/tournaments/:id', '/decklists/:id'],
  ];

  const W = 1200, H = 480;
  const px = (n) => (n.x / 100) * W;
  const py = (n) => 40 + (n.y / 100) * (H - 80);
  const find = (id) => nodes.find((n) => n.id === id);

  return (
    <section style={{
      maxWidth: 1440, margin: '0 auto 64px',
      padding: '40px 56px',
      borderTop: `0.5px solid ${LINE}`, borderBottom: `0.5px solid ${LINE}`,
    }}>
      <Eyebrow>Site architecture</Eyebrow>
      <h2 style={{ fontFamily: SERIF, fontWeight: 400, fontSize: 38,
                   letterSpacing: '-0.02em', color: INK,
                   margin: '20px 0 14px' }}>
        Six routes, one shared
        <em style={{ color: ACCENT, fontStyle: 'italic' }}> shell.</em>
      </h2>
      <p style={{ fontFamily: SANS, fontSize: 15.5, color: MUTE,
                  maxWidth: 720, margin: '0 0 40px', textWrap: 'pretty' }}>
        The landing page is the entry point; the five top-level routes share a Nav,
        background field, and design-token system. Three of them open into detail views.
      </p>

      <div style={{ position: 'relative' }}>
        <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', display: 'block' }}>
          {/* edges */}
          {edges.map(([a, b], i) => {
            const na = find(a), nb = find(b);
            return (
              <line key={i} x1={px(na)} y1={py(na)} x2={px(nb)} y2={py(nb)}
                    stroke={LINE} strokeWidth="0.8"
                    strokeDasharray={a === '/' ? '0' : '3 4'} />
            );
          })}
          {/* nodes */}
          {nodes.map((n) => (
            <g key={n.id}>
              <circle cx={px(n)} cy={py(n)} r="6" fill={ACCENT} />
              <circle cx={px(n)} cy={py(n)} r="12" fill="none"
                      stroke={ACCENT} strokeOpacity="0.3" strokeWidth="0.8" />
              <text x={px(n)} y={py(n) - 22} fill={INK} fontSize="14"
                    fontFamily={SERIF} fontStyle="italic" textAnchor="middle"
                    letterSpacing="-0.01em">
                {n.label}
              </text>
              <text x={px(n)} y={py(n) + 28} fill={MUTE} fontSize="10.5"
                    fontFamily={MONO} textAnchor="middle"
                    letterSpacing="0.05em">
                {n.id}
              </text>
              <text x={px(n)} y={py(n) + 44} fill={DIM} fontSize="10"
                    fontFamily={SANS} textAnchor="middle">
                {n.desc}
              </text>
            </g>
          ))}
        </svg>
      </div>
    </section>
  );
}

// ── App: renders the whole architecture preview ────────────────────────────

function App() {
  return (
    <div style={{ background: BG, color: INK, fontFamily: SANS,
                  paddingBottom: 80, minHeight: '100vh' }}>
      <PageHero />
      <SiteMap />
      <MetagamePage />
      <ArchetypesPage />
      <DecklistsPage />
      <TournamentsPage />
      <TrendsPage />
      <Footer />
    </div>
  );
}

function PageHero() {
  return (
    <section style={{ maxWidth: 1440, margin: '0 auto', padding: '64px 56px 32px' }}>
      <Eyebrow>Handoff · pages architecture</Eyebrow>
      <h1 style={{ fontFamily: SERIF, fontWeight: 400, fontSize: 52,
                   lineHeight: 1.2, letterSpacing: '-0.02em', color: INK,
                   margin: '24px 0 28px', textWrap: 'pretty', maxWidth: 1000 }}>
        All of tolaria_news,
        <em style={{ color: ACCENT, fontStyle: 'italic', fontFamily: SERIF }}> mapped.</em>
      </h1>
      <p style={{ fontFamily: SANS, fontSize: 17, lineHeight: 1.55,
                  color: MUTE, maxWidth: 720, margin: 0, textWrap: 'pretty' }}>
        Visual reference for the five inner routes. Use these alongside
        <code style={{ fontFamily: MONO, fontSize: 14, color: ACCENT,
                       padding: '0 4px' }}>PAGES.md</code> when implementing.
        Layouts, components, copy, and data placeholders all reflect the design system.
      </p>
    </section>
  );
}

function Footer() {
  return (
    <footer style={{ maxWidth: 1440, margin: '0 auto', padding: '32px 56px',
                     borderTop: `0.5px solid ${LINE}`,
                     fontFamily: MONO, fontSize: 10.5, color: MUTE,
                     letterSpacing: '0.1em', textTransform: 'uppercase',
                     display: 'flex', justifyContent: 'space-between' }}>
      <span>Barrin&apos;s Project · pages architecture</span>
      <span>v1 · 2026.1</span>
    </footer>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
