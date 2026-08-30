import { type FormEvent, useId, useState } from 'react'
import { IdentityError } from '../auth/client'
import { useSignup } from '../auth/hooks'
import { AlertIcon, CheckIcon, DotIcon, ShieldMark, Spinner } from './icons'
import '../styles.css'

export interface SignupScreenProps {
  /**
   * Called when the account was created but needs email verification
   * (`verification_required`). The host routes to the verification screen,
   * passing the email through.
   */
  onVerificationRequired?: (email: string) => void
  /**
   * Called when signup returned tokens directly (email verification disabled
   * server-side) — the user is already signed in.
   */
  onAuthenticated?: () => void
  /** Render a "Back to sign in" link wired to this handler. */
  onBackToLogin?: () => void
  /** Wordmark heading. */
  title?: string
  /** Line under the wordmark. */
  subtitle?: string
}

const GENERIC_ERROR = 'Something went wrong. Please try again.'

// Mirrors `USERNAME_PATTERN` in `apps/barrins_identity/app/schemas/auth.py`.
// Client-side feedback only — the backend is the source of truth on submit.
const USERNAME_PATTERN = /^[A-Za-z0-9_-]{3,32}$/

// Mirrors `PASSWORD_PATTERN` in `apps/barrins_identity/app/schemas/auth.py`.
// Client-side feedback only — the backend is the source of truth on submit.
const PASSWORD_RULES: { label: string; test: (value: string) => boolean }[] = [
  { label: 'At least 12 characters', test: (value) => value.length >= 12 },
  { label: 'One uppercase letter', test: (value) => /[A-Z]/.test(value) },
  { label: 'One lowercase letter', test: (value) => /[a-z]/.test(value) },
  { label: 'One digit', test: (value) => /\d/.test(value) },
  { label: 'One symbol', test: (value) => /[^\w\s]/.test(value) },
]

export function SignupScreen({
  onVerificationRequired,
  onAuthenticated,
  onBackToLogin,
  title = "Barrin's Identity",
  subtitle = "Create your Barrin's account",
}: SignupScreenProps) {
  const emailId = useId()
  const usernameId = useId()
  const displayNameId = useId()
  const passwordId = useId()
  const signup = useSignup()
  const [email, setEmail] = useState('')
  const [username, setUsername] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)

  const pending = signup.isPending
  const usernameInvalid = username !== '' && !USERNAME_PATTERN.test(username)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)

    if (email === '' || username === '' || password === '') {
      setError('Email, username, and password are required.')
      return
    }

    try {
      const result = await signup.mutateAsync({
        email,
        username,
        password,
        displayName: displayName === '' ? undefined : displayName,
      })
      if (result.tokens !== null) {
        onAuthenticated?.()
      } else {
        onVerificationRequired?.(email)
      }
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
              <label className="gg-label" htmlFor={usernameId}>
                Username
              </label>
              <input
                id={usernameId}
                className="gg-input"
                type="text"
                autoComplete="username"
                value={username}
                disabled={pending}
                aria-invalid={usernameInvalid}
                onChange={(event) => {
                  setUsername(event.target.value)
                }}
              />
              <span className="gg-hint">
                3&ndash;32 characters &mdash; letters, digits, underscore or hyphen.
              </span>
            </div>

            <div className="gg-field">
              <div className="gg-field-header">
                <label className="gg-label" htmlFor={displayNameId}>
                  Display name
                </label>
                <span className="gg-hint">optional</span>
              </div>
              <input
                id={displayNameId}
                className="gg-input"
                type="text"
                autoComplete="nickname"
                value={displayName}
                disabled={pending}
                onChange={(event) => {
                  setDisplayName(event.target.value)
                }}
              />
            </div>

            <div className="gg-field">
              <label className="gg-label" htmlFor={passwordId}>
                Password
              </label>
              <input
                id={passwordId}
                className="gg-input"
                type="password"
                autoComplete="new-password"
                value={password}
                disabled={pending}
                onChange={(event) => {
                  setPassword(event.target.value)
                }}
              />
              <ul className="gg-rules">
                {PASSWORD_RULES.map((rule) => {
                  const met = rule.test(password)
                  return (
                    <li key={rule.label} className="gg-rule" data-met={met}>
                      {met ? <CheckIcon /> : <DotIcon />}
                      <span>{rule.label}</span>
                    </li>
                  )
                })}
              </ul>
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
              {pending ? 'Creating account…' : 'Create account'}
            </button>
          </form>

          {onBackToLogin && (
            <p className="gg-aux">
              Already have an account?{' '}
              <button type="button" className="gg-link" onClick={onBackToLogin}>
                Sign in
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
