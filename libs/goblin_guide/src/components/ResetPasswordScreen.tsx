import { type FormEvent, useId, useState } from 'react'
import { IdentityError } from '../auth/client'
import { usePasswordResetConfirm } from '../auth/hooks'
import { CodeField } from './CodeField'
import { onlyDigits } from './codeMask'
import { AlertIcon, KeyIcon, ShieldMark, Spinner } from './icons'
import { PasswordRules } from './PasswordRules'
import '../styles.css'

export interface ResetPasswordScreenProps {
  /** Pre-fill the email field (e.g. from the `?email=` deep-link param). */
  initialEmail?: string
  /** Pre-fill the code field (e.g. from the `?code=` deep-link param). */
  initialCode?: string
  /** Called after the password is reset — the user is now signed in. */
  onAuthenticated?: () => void
  /** Render a "Back to sign in" link wired to this handler. */
  onBackToLogin?: () => void
  /** Wordmark heading. */
  title?: string
  /** Line under the wordmark. */
  subtitle?: string
}

const GENERIC_ERROR = 'Something went wrong. Please try again.'

export function ResetPasswordScreen({
  initialEmail = '',
  initialCode = '',
  onAuthenticated,
  onBackToLogin,
  title = "Barrin's Identity",
  subtitle = 'Set a new password',
}: ResetPasswordScreenProps) {
  const emailId = useId()
  const codeId = useId()
  const passwordId = useId()
  const confirm = usePasswordResetConfirm()
  const [email, setEmail] = useState(initialEmail)
  const [code, setCode] = useState(() => onlyDigits(initialCode))
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)

  const pending = confirm.isPending

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)

    if (email === '' || !/^\d{6}$/.test(code) || password === '') {
      setError('Enter your email, the 6-digit code, and a new password.')
      return
    }

    try {
      await confirm.mutateAsync({ email, code, newPassword: password })
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

          <div className="gg-banner" role="status">
            <KeyIcon style={{ stroke: 'var(--gg-warning)' }} />
            <span>
              Enter the 6-digit code we sent
              {email !== '' ? (
                <>
                  {' to '}
                  <strong style={{ color: 'var(--gg-fg)', fontWeight: 600 }}>
                    {email}
                  </strong>
                </>
              ) : (
                ' to your email address'
              )}{' '}
              and choose a new password.
            </span>
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

            <CodeField
              id={codeId}
              label="Reset code"
              value={code}
              onChange={setCode}
              disabled={pending}
              invalid={error !== null && !pending}
            />

            <div className="gg-field">
              <label className="gg-label" htmlFor={passwordId}>
                New password
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
              <PasswordRules value={password} />
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
              {pending ? 'Resetting…' : 'Reset password'}
            </button>
          </form>

          {onBackToLogin && (
            <p className="gg-aux">
              <button type="button" className="gg-link" onClick={onBackToLogin}>
                Back to sign in
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
