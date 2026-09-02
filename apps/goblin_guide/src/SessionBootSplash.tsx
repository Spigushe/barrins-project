import type { CSSProperties } from 'react'

const splash: CSSProperties = {
  minHeight: '100svh',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  background: 'var(--color-background)',
  color: 'var(--color-muted-foreground)',
}

/**
 * Shown while the identity provider makes its one-shot cookie-mode session
 * restore on page load (ADR-18). Without it, a reload with a valid refresh
 * cookie would briefly flash the login screen before the session comes back.
 */
export function SessionBootSplash() {
  return (
    <div style={splash}>
      <p style={{ fontSize: 13 }}>Restoring your session…</p>
    </div>
  )
}
