import { type CSSProperties, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useCurrentUser, useLogout } from '@barrins/goblin-guide'

const page: CSSProperties = {
  minHeight: '100svh',
  display: 'flex',
  flexDirection: 'column',
  background: 'var(--color-background)',
  color: 'var(--color-foreground)',
}

const row: CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  gap: 16,
  padding: '11px 16px',
  borderBottom: '1px solid var(--color-border)',
  fontSize: 12.5,
}

export function Shell() {
  const navigate = useNavigate()
  const { data: user, isLoading, isError } = useCurrentUser()
  const logout = useLogout()

  useEffect(() => {
    if (isError) navigate('/login?expired=1', { replace: true })
  }, [isError, navigate])

  if (isLoading || user === undefined) {
    return (
      <div style={{ ...page, alignItems: 'center', justifyContent: 'center' }}>
        <p style={{ color: 'var(--color-muted-foreground)', fontSize: 13 }}>
          Loading your account…
        </p>
      </div>
    )
  }

  return (
    <div style={page}>
      <header
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '16px 28px',
          borderBottom: '1px solid var(--color-border)',
        }}
      >
        <span style={{ fontSize: 14, fontWeight: 700 }}>Barrin&rsquo;s Identity</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <div
            style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end' }}
          >
            <span style={{ fontSize: 12.5, fontWeight: 600 }}>
              {user.display_name ?? user.username}
            </span>
            <span style={{ fontSize: 11, color: 'var(--color-muted-foreground)' }}>
              {user.email}
            </span>
          </div>
          <span
            style={{
              fontSize: 10.5,
              fontWeight: 600,
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              color: 'var(--color-muted-foreground)',
              border: '1px solid var(--color-border)',
              borderRadius: 999,
              padding: '3px 9px',
            }}
          >
            {user.role}
          </span>
          <button
            type="button"
            disabled={logout.isPending}
            onClick={() => {
              logout.mutate()
            }}
            style={{
              border: '1px solid var(--color-border)',
              background: 'transparent',
              color: 'var(--color-foreground)',
              borderRadius: 'var(--radius-button, 8px)',
              padding: '7px 14px',
              fontSize: 12.5,
              fontWeight: 600,
              cursor: 'pointer',
              fontFamily: 'inherit',
            }}
          >
            Log out
          </button>
        </div>
      </header>

      <main
        style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          padding: '56px 24px',
        }}
      >
        <div style={{ width: '100%', maxWidth: 520 }}>
          <h2 style={{ margin: 0, fontSize: 20, fontWeight: 800 }}>
            You&rsquo;re signed in
          </h2>
          <p
            style={{
              margin: '8px 0 0',
              fontSize: 13,
              color: 'var(--color-muted-foreground)',
              lineHeight: 1.5,
            }}
          >
            This is your Barrin&rsquo;s account home. It also serves the sign-in page that
            the Karn Tablets Jupyter workbench redirects to.
          </p>

          <div
            style={{
              marginTop: 24,
              border: '1px solid var(--color-border)',
              background: 'var(--color-card)',
              borderRadius: 'var(--radius-card, 12px)',
              overflow: 'hidden',
            }}
          >
            <div
              style={{
                ...row,
                fontWeight: 600,
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
                fontSize: 11,
                color: 'var(--color-subtle-foreground, var(--color-muted-foreground))',
              }}
            >
              Account
            </div>
            <div style={row}>
              <span style={{ color: 'var(--color-muted-foreground)' }}>Username</span>
              <span>{user.username}</span>
            </div>
            <div style={row}>
              <span style={{ color: 'var(--color-muted-foreground)' }}>Display name</span>
              <span>{user.display_name ?? '—'}</span>
            </div>
            <div style={row}>
              <span style={{ color: 'var(--color-muted-foreground)' }}>Email</span>
              <span>
                {user.email}
                {user.is_verified ? ' ✓' : ' (unverified)'}
              </span>
            </div>
            <div style={{ ...row, borderBottom: 'none' }}>
              <span style={{ color: 'var(--color-muted-foreground)' }}>Role</span>
              <span>{user.role}</span>
            </div>
          </div>

          <p
            style={{
              margin: '16px 0 0',
              fontSize: 11.5,
              color: 'var(--color-subtle-foreground, var(--color-muted-foreground))',
              lineHeight: 1.5,
            }}
          >
            Changing your email or password, and deleting your account, arrive in a later
            release.
          </p>
        </div>
      </main>
    </div>
  )
}
