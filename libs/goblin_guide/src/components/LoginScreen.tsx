import { type FormEvent, useId, useState } from 'react'
import { IdentityError } from '../auth/client'
import { useLogin } from '../auth/hooks'
import { AlertIcon, ShieldMark, Spinner } from './icons'
import '../styles.css'

export interface LoginScreenProps {
  /** Called after a successful login (the host handles navigation). */
  onAuthenticated?: () => void
  /** Show the "your session has ended" banner above the form. */
  sessionExpired?: boolean
  /** Wordmark heading. */
  title?: string
  /** Line under the wordmark. */
  subtitle?: string
  /** Render a "Forgot password?" link wired to this handler. */
  onForgotPassword?: () => void
  /** Render a "Create an account" link wired to this handler. */
  onCreateAccount?: () => void
}

const GENERIC_ERROR = 'Something went wrong. Please try again.'

export function LoginScreen({
  onAuthenticated,
  sessionExpired = false,
  title = "Barrin's Identity",
  subtitle = "Sign in to your Barrin's account",
  onForgotPassword,
  onCreateAccount,
}: LoginScreenProps) {
  const emailId = useId()
  const passwordId = useId()
  const login = useLogin()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)

  const pending = login.isPending

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)

    if (email === '' || password === '') {
      setError('Email and password are required.')
      return
    }

    try {
      await login.mutateAsync({ email, password })
      onAuthenticated?.()
    } catch (err) {
      setError(err instanceof IdentityError ? err.message : GENERIC_ERROR)
    }
  }

  return (
    <div className="gg-scope">
      <div className="gg-centered">
        <div className="gg-card">
          <div className="gg-brand">
            <ShieldMark />
            <h1 className="gg-title">{title}</h1>
            <p className="gg-subtitle">{subtitle}</p>
          </div>

          {sessionExpired && (
            <div className="gg-banner" role="status">
              <AlertIcon style={{ stroke: 'var(--gg-warning)' }} />
              <span>Your session has ended. Please sign in again to continue.</span>
            </div>
          )}

          <form className="gg-form" onSubmit={handleSubmit} noValidate>
            <div className="gg-field">
              <label className="gg-label" htmlFor={emailId}>
                Email
              </label>
              <input
                id={emailId}
                className="gg-input"
                type="email"
                autoComplete="email"
                value={email}
                disabled={pending}
                onChange={(event) => {
                  setEmail(event.target.value)
                }}
              />
            </div>

            <div className="gg-field">
              <div className="gg-field-header">
                <label className="gg-label" htmlFor={passwordId}>
                  Password
                </label>
                {onForgotPassword && (
                  <button
                    type="button"
                    className="gg-link"
                    style={{ fontSize: '11.5px' }}
                    onClick={onForgotPassword}
                  >
                    Forgot password?
                  </button>
                )}
              </div>
              <input
                id={passwordId}
                className="gg-input"
                type="password"
                autoComplete="current-password"
                value={password}
                disabled={pending}
                aria-invalid={error !== null && !pending}
                onChange={(event) => {
                  setPassword(event.target.value)
                }}
              />
            </div>

            {error !== null && (
              <p className="gg-error" role="alert">
                <AlertIcon />
                <span>{error}</span>
              </p>
            )}

            <button type="submit" className="gg-button" disabled={pending}>
              {pending && (
                <Spinner
                  className="gg-spinner"
                  style={{ stroke: 'var(--gg-accent-fg)' }}
                />
              )}
              {pending ? 'Signing in…' : 'Log in'}
            </button>
          </form>

          {onCreateAccount && (
            <p className="gg-aux">
              Don&rsquo;t have an account yet?{' '}
              <button type="button" className="gg-link" onClick={onCreateAccount}>
                Create an account
              </button>
            </p>
          )}

          <p className="gg-footer">
            Barrin&rsquo;s Identity &middot; one account across the ecosystem
          </p>
        </div>
      </div>
    </div>
  )
}
