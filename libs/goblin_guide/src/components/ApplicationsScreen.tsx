import type { CSSProperties, ReactElement } from 'react'
import { IdentityError } from '../auth/client'
import { useApplications } from '../auth/hooks'
import type { Application, ApplicationAccess } from '../auth/schemas'
import { AlertIcon } from './icons'
import '../styles.css'

export interface ApplicationsScreenProps {
  /**
   * The `key` of the app this launcher is embedded in — its card is dropped
   * from the list (a host app doesn't advertise itself). Server never
   * filters it (ADR-19); the SPA does.
   */
  currentAppKey?: string
  /** Heading. */
  title?: string
  /** Line under the heading. */
  subtitle?: string
}

const GENERIC_ERROR = 'Something went wrong. Please try again.'

function messageOf(err: unknown): string {
  return err instanceof IdentityError ? err.message : GENERIC_ERROR
}

/** Inline SVG → `<img>` source. An `<img>`-loaded SVG can't run scripts. */
function logoSrc(svg: string): string {
  return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`
}

const GROUPS: { access: ApplicationAccess; heading: string; note?: string }[] = [
  { access: 'open', heading: 'Available' },
  {
    access: 'login_required',
    heading: 'Sign in to open',
    note: 'Sign in to your Barrin’s account to open these.',
  },
  {
    access: 'role_denied',
    heading: 'Restricted',
    note: 'These need a higher account role than yours.',
  },
]

/**
 * The role-aware cross-app launcher (ADR-19). "Which apps can this user
 * open" is a backend decision — this screen only renders the `access`
 * state identity returns, grouped, with the current app filtered out.
 */
export function ApplicationsScreen({
  currentAppKey,
  title = 'Barrin’s applications',
  subtitle = 'Everything your account can reach in one place.',
}: ApplicationsScreenProps): ReactElement {
  const { data, isLoading, isError, error } = useApplications()

  const apps = (data ?? []).filter((app) => app.key !== currentAppKey)

  return (
    <div className="gg-scope gg-account">
      <h1 className="gg-account-title">{title}</h1>
      <p className="gg-account-lede">{subtitle}</p>

      {isLoading && <p className="gg-note">Loading applications…</p>}

      {isError && (
        <p className="gg-error" role="alert">
          <AlertIcon />
          <span>{messageOf(error)}</span>
        </p>
      )}

      {data !== undefined &&
        GROUPS.map(({ access, heading, note }) => {
          const inGroup = apps.filter((app) => app.access === access)
          if (inGroup.length === 0) return null
          return (
            <section className="gg-section" key={access}>
              <h2 className="gg-section-title">{heading}</h2>
              {note && <p className="gg-note">{note}</p>}
              <div style={gridStyle}>
                {inGroup.map((app) => (
                  <ApplicationCard key={app.key} app={app} />
                ))}
              </div>
            </section>
          )
        })}

      {data !== undefined && apps.length === 0 && (
        <p className="gg-note">No other applications are available yet.</p>
      )}
    </div>
  )
}

const gridStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))',
  gap: 14,
  marginTop: 12,
}

const cardStyle: CSSProperties = {
  display: 'flex',
  gap: 12,
  padding: 14,
  border: '1px solid var(--gg-border)',
  borderRadius: 12,
  background: 'var(--gg-bg)',
  color: 'var(--gg-fg)',
  textDecoration: 'none',
  alignItems: 'flex-start',
}

function ApplicationCard({ app }: { app: Application }): ReactElement {
  const openable = app.access === 'open'
  const body = (
    <>
      <img
        src={logoSrc(app.logo_svg)}
        alt=""
        width={40}
        height={40}
        style={{ flexShrink: 0, borderRadius: 8 }}
      />
      <div style={{ minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 13.5, fontWeight: 600 }}>{app.name}</span>
          <AccessBadge access={app.access} minRole={app.min_role} />
        </div>
        <p
          style={{
            margin: '4px 0 0',
            fontSize: 12,
            lineHeight: 1.45,
            color: 'var(--gg-muted)',
          }}
        >
          {app.description}
        </p>
      </div>
    </>
  )

  if (openable) {
    return (
      <a href={app.url} style={cardStyle} rel="noreferrer">
        {body}
      </a>
    )
  }
  return (
    <div style={{ ...cardStyle, opacity: 0.72 }} aria-disabled="true">
      {body}
    </div>
  )
}

function AccessBadge({
  access,
  minRole,
}: {
  access: ApplicationAccess
  minRole: Application['min_role']
}): ReactElement | null {
  if (access === 'open') return null
  const label = access === 'login_required' ? 'Sign in' : `Needs ${minRole ?? 'a role'}`
  return (
    <span
      style={{
        fontSize: 10,
        fontWeight: 600,
        textTransform: 'uppercase',
        letterSpacing: '0.04em',
        color: 'var(--gg-muted)',
        border: '1px solid var(--gg-border)',
        borderRadius: 999,
        padding: '2px 7px',
        whiteSpace: 'nowrap',
      }}
    >
      {label}
    </span>
  )
}
