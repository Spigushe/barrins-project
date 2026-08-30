import { type FormEvent, useId, useState } from 'react'
import { IdentityError } from '../auth/client'
import { usePasswordResetRequest } from '../auth/hooks'
import { AlertIcon, CheckIcon, KeyIcon, ShieldMark, Spinner } from './icons'
import '../styles.css'

export interface ForgotPasswordScreenProps {
  /** Pre-fill the email field (e.g. from a `?email=` param). */
  initialEmail?: string
  /**
   * Called when the user chooses to enter the code they were sent — the host
   * routes to the reset screen, passing the email through.
   */
  onEnterCode?: (email: string) => void
  /** Render a "Back to sign in" link wired to this handler. */
  onBackToLogin?: () => void
  /** Wordmark heading. */
  title?: string
  /** Line under the wordmark. */
  subtitle?: string
}

const GENERIC_ERROR = 'Something went wrong. Please try again.'

export function ForgotPasswordScreen({
  initialEmail = '',
  onEnterCode,
  onBackToLogin,
  title = "Barrin's Identity",
  subtitle = 'Reset your password',
}: ForgotPasswordScreenProps) {
  const emailId = useId()
  const request = usePasswordResetRequest()
  const [email, setEmail] = useState(initialEmail)
  const [error, setError] = useState<string | null>(null)
  // The generic confirmation copy, shown once a request has gone through.
  const [confirmation, setConfirmation] = useState<string | null>(null)

  const pending = request.isPending

  async function submitRequest() {
    setError(null)

    if (email === '') {
      setError('Enter your email address.')
      return
    }

    try {
      const response = await request.mutateAsync(email)
      // Deliberately generic — it never confirms whether an account exists.
      setConfirmation(response.detail)
    } catch (err) {
      setError(err instanceof IdentityError ? err.message : GENERIC_ERROR)
    }
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    void submitRequest()
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

          {confirmation !== null ? (
            <>
              <div className="gg-banner" data-tone="success" role="status">
                <CheckIcon style={{ stroke: 'var(--gg-success)' }} />
                <span>{confirmation}</span>
              </div>

              {error !== null && (
                <p className="gg-error" role="alert">
                  <AlertIcon />
                  <span>{error}</span>
                </p>
              )}

              <button
                type="button"
                className="gg-button"
                style={{ marginTop: 20 }}
                onClick={() => onEnterCode?.(email)}
              >
                Enter reset code
              </button>

              <p className="gg-aux">
                Didn&rsquo;t get it?{' '}
                <button
                  type="button"
                  className="gg-link"
                  disabled={pending}
                  onClick={() => {
                    void submitRequest()
                  }}
                >
                  Send again
                </button>
              </p>
            </>
          ) : (
            <>
              <div className="gg-banner" role="status">
                <KeyIcon style={{ stroke: 'var(--gg-warning)' }} />
                <span>
                  Enter your account email and we&rsquo;ll send you a 6-digit code to set
                  a new password.
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
                    aria-invalid={error !== null && !pending}
                    onChange={(event) => {
                      setEmail(event.target.value)
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
                  {pending ? 'Sending…' : 'Send reset code'}
                </button>
              </form>

              <p className="gg-aux">
                Already have a code?{' '}
                <button
                  type="button"
                  className="gg-link"
                  onClick={() => onEnterCode?.(email)}
                >
                  Enter it here
                </button>
              </p>
            </>
          )}

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
