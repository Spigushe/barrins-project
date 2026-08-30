import { type FormEvent, useEffect, useId, useState } from 'react'
import { IdentityError } from '../auth/client'
import { useResendVerification, useVerifyEmail } from '../auth/hooks'
import { AlertIcon, CheckIcon, MailIcon, ShieldMark, Spinner } from './icons'
import '../styles.css'

export interface VerifyEmailScreenProps {
  /** Pre-fill the email field (e.g. from the `?email=` deep-link param). */
  initialEmail?: string
  /** Pre-fill the code field (e.g. from the `?code=` deep-link param). */
  initialCode?: string
  /** Called after the code is accepted — the user is now signed in. */
  onAuthenticated?: () => void
  /** Render a "Back to sign in" link wired to this handler. */
  onBackToLogin?: () => void
  /** Wordmark heading. */
  title?: string
  /** Line under the wordmark. */
  subtitle?: string
}

const GENERIC_ERROR = 'Something went wrong. Please try again.'
// The service enforces this cooldown; the UI mirrors it so the button
// isn't offered while a request would be rejected.
const RESEND_COOLDOWN_SECONDS = 60

const onlyDigits = (value: string): string => value.replace(/\D/g, '').slice(0, 6)

export function VerifyEmailScreen({
  initialEmail = '',
  initialCode = '',
  onAuthenticated,
  onBackToLogin,
  title = "Barrin's Identity",
  subtitle = 'Verify your email',
}: VerifyEmailScreenProps) {
  const emailId = useId()
  const codeId = useId()
  const verify = useVerifyEmail()
  const resend = useResendVerification()
  const [email, setEmail] = useState(initialEmail)
  const [code, setCode] = useState(() => onlyDigits(initialCode))
  const [error, setError] = useState<string | null>(null)
  const [resendMessage, setResendMessage] = useState<string | null>(null)
  const [cooldown, setCooldown] = useState(0)

  const pending = verify.isPending

  useEffect(() => {
    if (cooldown <= 0) return
    const timer = setTimeout(() => {
      setCooldown((seconds) => seconds - 1)
    }, 1000)
    return () => {
      clearTimeout(timer)
    }
  }, [cooldown])

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)

    if (email === '' || !/^\d{6}$/.test(code)) {
      setError('Enter your email and the 6-digit code.')
      return
    }

    try {
      await verify.mutateAsync({ email, code })
      onAuthenticated?.()
    } catch (err) {
      setError(err instanceof IdentityError ? err.message : GENERIC_ERROR)
    }
  }

  async function handleResend() {
    setError(null)
    setResendMessage(null)

    if (email === '') {
      setError('Enter your email to get a new code.')
      return
    }

    try {
      const response = await resend.mutateAsync(email)
      // The response is deliberately generic — it never confirms whether an
      // account exists for this address.
      setResendMessage(response.detail)
      setCooldown(RESEND_COOLDOWN_SECONDS)
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
            <MailIcon style={{ stroke: 'var(--gg-warning)' }} />
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
              to activate your account.
            </span>
          </div>

          {resendMessage !== null && (
            <div className="gg-banner" data-tone="success" role="status">
              <CheckIcon style={{ stroke: 'var(--gg-success)' }} />
              <span>{resendMessage}</span>
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
              <label className="gg-label" htmlFor={codeId}>
                Verification code
              </label>
              <input
                id={codeId}
                className="gg-input gg-code"
                inputMode="numeric"
                autoComplete="one-time-code"
                maxLength={6}
                placeholder="000000"
                value={code}
                disabled={pending}
                aria-invalid={error !== null && !pending}
                onChange={(event) => {
                  setCode(onlyDigits(event.target.value))
                }}
              />
              <span className="gg-hint">The 6-digit code from your email.</span>
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
              {pending ? 'Verifying…' : 'Verify email'}
            </button>
          </form>

          <p className="gg-aux">
            {cooldown > 0 ? (
              <span className="gg-aux-muted">Resend available in {cooldown}s</span>
            ) : (
              <>
                Didn&rsquo;t get the code?{' '}
                <button
                  type="button"
                  className="gg-link"
                  disabled={resend.isPending}
                  onClick={() => {
                    void handleResend()
                  }}
                >
                  Resend code
                </button>
              </>
            )}
          </p>

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
