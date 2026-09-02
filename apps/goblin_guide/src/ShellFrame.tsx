import { type CSSProperties, type ReactNode, useEffect } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useCurrentUser, useLogout } from '@barrins/goblin-guide'

const page: CSSProperties = {
  minHeight: '100svh',
  display: 'flex',
  flexDirection: 'column',
  background: 'var(--color-background)',
  color: 'var(--color-foreground)',
}

const navButton: CSSProperties = {
  border: '1px solid var(--color-border)',
  background: 'transparent',
  color: 'var(--color-foreground)',
  borderRadius: 'var(--radius-button, 8px)',
  padding: '7px 14px',
  fontSize: 12.5,
  fontWeight: 600,
  cursor: 'pointer',
  fontFamily: 'inherit',
  textDecoration: 'none',
}

/**
 * The authenticated app frame — header (user chip, role, admin nav, log
 * out) plus a centered `<main>`. Both the account screen (`Shell`) and the
 * service-accounts screen mount inside it.
 */
export function ShellFrame({ children }: { children: ReactNode }) {
  const navigate = useNavigate()
  const location = useLocation()
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

  const onServiceAccounts = location.pathname === '/service-accounts'

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
          {user.role === 'admin' && (
            <Link to={onServiceAccounts ? '/' : '/service-accounts'} style={navButton}>
              {onServiceAccounts ? 'Account' : 'Service accounts'}
            </Link>
          )}
          <button
            type="button"
            disabled={logout.isPending}
            onClick={() => {
              logout.mutate()
            }}
            style={{ ...navButton, cursor: logout.isPending ? 'default' : 'pointer' }}
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
        {children}
      </main>
    </div>
  )
}
