import { type FormEvent, useEffect, useId, useState } from 'react'
import { IdentityError } from '../auth/client'
import {
  useCurrentUser,
  useDeleteAccount,
  useResendEmailChange,
  useUpdateAccount,
  useVerifyEmailChange,
} from '../auth/hooks'
import type { Principal } from '../auth/schemas'
import { CodeField } from './CodeField'
import { onlyDigits } from './codeMask'
import { AlertIcon, CheckIcon, MailIcon, Spinner } from './icons'
import '../styles.css'

export interface AccountScreenProps {
  /**
   * Reveal the email-change confirmation step with this 6-digit code
   * pre-filled — from the `/confirm-email-change?code=` deep link.
   */
  initialEmailChangeCode?: string
  /**
   * The pending address the code was sent to (deep-link `?email=`), shown in
   * the confirmation banner.
   */
  initialPendingEmail?: string
  /** Called once the account has been deleted; local token state is already cleared. */
  onDeleted?: () => void
  /** Heading. */
  title?: string
  /** Line under the heading. */
  subtitle?: string
}

const GENERIC_ERROR = 'Something went wrong. Please try again.'
// The service enforces this cooldown on the email-change resend; the UI
// mirrors it so the button isn't offered while a request would be rejected.
const RESEND_COOLDOWN_SECONDS = 60

function messageOf(err: unknown): string {
  return err instanceof IdentityError ? err.message : GENERIC_ERROR
}

type EmailStep = 'idle' | 'editing' | 'pending'
type DeleteStep = 'idle' | 'confirming'

export function AccountScreen({
  title = 'Account',
  subtitle = "Manage your Barrin's account — the same sign-in across every app in the ecosystem.",
  initialEmailChangeCode = '',
  initialPendingEmail = '',
  onDeleted,
}: AccountScreenProps) {
  const { data: user } = useCurrentUser()

  if (user === undefined) {
    return (
      <div className="gg-scope gg-account">
        <h1 className="gg-account-title">{title}</h1>
        <p className="gg-account-lede">Loading your account…</p>
      </div>
    )
  }

  return (
    <AccountScreenForm
      user={user}
      title={title}
      subtitle={subtitle}
      initialEmailChangeCode={initialEmailChangeCode}
      initialPendingEmail={initialPendingEmail}
      onDeleted={onDeleted}
    />
  )
}

interface AccountScreenFormProps {
  user: Principal
  title: string
  subtitle: string
  initialEmailChangeCode: string
  initialPendingEmail: string
  onDeleted?: () => void
}

function AccountScreenForm({
  user,
  title,
  subtitle,
  initialEmailChangeCode,
  initialPendingEmail,
  onDeleted,
}: AccountScreenFormProps) {
  const displayNameId = useId()
  const newEmailId = useId()
  const codeId = useId()
  const passwordId = useId()

  const updateAccount = useUpdateAccount()
  const verifyChange = useVerifyEmailChange()
  const resendChange = useResendEmailChange()
  const deleteAccount = useDeleteAccount()

  // --- profile -------------------------------------------------------------
  const [displayName, setDisplayName] = useState(user.display_name ?? '')
  const [profileError, setProfileError] = useState<string | null>(null)
  const [profileSaved, setProfileSaved] = useState(false)

  // --- email change ------------------------------------------------------
  const [emailStep, setEmailStep] = useState<EmailStep>(
    initialEmailChangeCode !== '' ? 'pending' : 'idle',
  )
  const [newEmail, setNewEmail] = useState('')
  const [pendingEmail, setPendingEmail] = useState(initialPendingEmail)
  const [code, setCode] = useState(() => onlyDigits(initialEmailChangeCode))
  const [emailError, setEmailError] = useState<string | null>(null)
  const [emailNotice, setEmailNotice] = useState<string | null>(null)
  const [emailSaved, setEmailSaved] = useState(false)
  const [cooldown, setCooldown] = useState(0)

  useEffect(() => {
    if (cooldown <= 0) return
    const timer = setTimeout(() => {
      setCooldown((seconds) => seconds - 1)
    }, 1000)
    return () => {
      clearTimeout(timer)
    }
  }, [cooldown])

  // --- delete -----------------------------------------------------------
  const [deleteStep, setDeleteStep] = useState<DeleteStep>('idle')
  const [password, setPassword] = useState('')
  const [deleteError, setDeleteError] = useState<string | null>(null)

  // The store is cleared the moment deletion succeeds; render nothing while
  // the host navigates away.
  if (deleteAccount.isSuccess) return null

  const displayNameDirty = displayName !== (user.display_name ?? '')
  const savingProfile = updateAccount.isPending

  async function saveDisplayName() {
    setProfileError(null)
    setProfileSaved(false)
    const next = displayName.trim() === '' ? null : displayName
    try {
      await updateAccount.mutateAsync({ displayName: next })
      setProfileSaved(true)
    } catch (err) {
      setProfileError(messageOf(err))
    }
  }

  async function sendEmailCode(event: FormEvent) {
    event.preventDefault()
    setEmailError(null)
    setEmailNotice(null)
    if (!newEmail.includes('@')) {
      setEmailError('Enter a valid email address.')
      return
    }
    try {
      await updateAccount.mutateAsync({ email: newEmail })
      setPendingEmail(newEmail)
      setCode('')
      setEmailStep('pending')
      setCooldown(RESEND_COOLDOWN_SECONDS)
    } catch (err) {
      setEmailError(messageOf(err))
    }
  }

  async function confirmEmailCode(event: FormEvent) {
    event.preventDefault()
    setEmailError(null)
    setEmailNotice(null)
    if (!/^\d{6}$/.test(code)) {
      setEmailError('Enter the 6-digit code from your email.')
      return
    }
    try {
      await verifyChange.mutateAsync(code)
      setEmailStep('idle')
      setNewEmail('')
      setPendingEmail('')
      setCode('')
      setEmailSaved(true)
    } catch (err) {
      setEmailError(messageOf(err))
    }
  }

  async function resendCode() {
    setEmailError(null)
    setEmailNotice(null)
    try {
      const response = await resendChange.mutateAsync()
      setEmailNotice(response.detail)
      setCooldown(RESEND_COOLDOWN_SECONDS)
    } catch (err) {
      setEmailError(messageOf(err))
    }
  }

  async function confirmDelete(event: FormEvent) {
    event.preventDefault()
    setDeleteError(null)
    if (password === '') {
      setDeleteError('Enter your current password.')
      return
    }
    try {
      await deleteAccount.mutateAsync(password)
      onDeleted?.()
    } catch (err) {
      setDeleteError(messageOf(err))
    }
  }

  return (
    <div className="gg-scope gg-account">
      <h1 className="gg-account-title">{title}</h1>
      <p className="gg-account-lede">{subtitle}</p>

      {/* Profile ---------------------------------------------------------- */}
      <section className="gg-section">
        <h2 className="gg-section-title">Profile</h2>
        <div className="gg-row">
          <span className="gg-row-key">Username</span>
          <span>{user.username}</span>
        </div>
        <div className="gg-row">
          <span className="gg-row-key">Role</span>
          <span>{user.role}</span>
        </div>

        <div className="gg-field" style={{ marginTop: 16 }}>
          <label className="gg-label" htmlFor={displayNameId}>
            Display name
          </label>
          <div className="gg-inline-edit">
            <input
              id={displayNameId}
              className="gg-input"
              type="text"
              value={displayName}
              disabled={savingProfile}
              aria-invalid={profileError !== null}
              onChange={(event) => {
                setDisplayName(event.target.value)
                setProfileSaved(false)
              }}
            />
            <button
              type="button"
              className="gg-icon-btn"
              aria-label="Save display name"
              disabled={!displayNameDirty || savingProfile}
              onClick={() => {
                void saveDisplayName()
              }}
            >
              {savingProfile ? (
                <Spinner className="gg-spinner" style={{ stroke: 'var(--gg-accent)' }} />
              ) : (
                <CheckIcon width={16} height={16} />
              )}
            </button>
          </div>
          <span className="gg-hint">Shown across the ecosystem.</span>
          {profileError !== null && (
            <p className="gg-error" role="alert">
              <AlertIcon />
              <span>{profileError}</span>
            </p>
          )}
          {profileSaved && !displayNameDirty && (
            <p className="gg-success-text" role="status">
              <CheckIcon style={{ stroke: 'var(--gg-success)' }} />
              <span>Display name updated.</span>
            </p>
          )}
        </div>
      </section>

      {/* Email --------------------------------------------------------- */}
      <section className="gg-section">
        <h2 className="gg-section-title">Email</h2>
        <div className="gg-row">
          <span className="gg-row-key">Current address</span>
          <span>
            {user.email}{' '}
            {user.is_verified ? (
              <span className="gg-chip-ok">
                <CheckIcon width={13} height={13} /> Verified
              </span>
            ) : (
              <span className="gg-aux-muted">(unverified)</span>
            )}
          </span>
        </div>

        {emailStep === 'idle' && (
          <>
            <p className="gg-note">
              Used for signing in and for account &amp; security notices.
            </p>
            {emailSaved && (
              <p className="gg-success-text" role="status">
                <CheckIcon style={{ stroke: 'var(--gg-success)' }} />
                <span>Email updated.</span>
              </p>
            )}
            <button
              type="button"
              className="gg-button gg-button--secondary"
              onClick={() => {
                setEmailSaved(false)
                setEmailError(null)
                setEmailStep('editing')
              }}
            >
              Change email
            </button>
          </>
        )}

        {emailStep === 'editing' && (
          <form className="gg-form" onSubmit={sendEmailCode} noValidate>
            <div className="gg-field">
              <label className="gg-label" htmlFor={newEmailId}>
                New email
              </label>
              <input
                id={newEmailId}
                className="gg-input"
                type="email"
                autoComplete="email"
                value={newEmail}
                disabled={updateAccount.isPending}
                aria-invalid={emailError !== null}
                onChange={(event) => {
                  setNewEmail(event.target.value)
                }}
              />
              <span className="gg-hint">
                We&rsquo;ll email a 6-digit code to the new address; your current one
                stays active until you confirm.
              </span>
            </div>
            {emailError !== null && (
              <p className="gg-error" role="alert">
                <AlertIcon />
                <span>{emailError}</span>
              </p>
            )}
            <button
              type="submit"
              className="gg-button"
              disabled={updateAccount.isPending}
            >
              {updateAccount.isPending && (
                <Spinner
                  className="gg-spinner"
                  style={{ stroke: 'var(--gg-accent-fg)' }}
                />
              )}
              {updateAccount.isPending ? 'Sending…' : 'Send confirmation code'}
            </button>
            <p className="gg-aux">
              <button
                type="button"
                className="gg-link"
                onClick={() => {
                  setEmailStep('idle')
                  setNewEmail('')
                  setEmailError(null)
                }}
              >
                Cancel
              </button>
            </p>
          </form>
        )}

        {emailStep === 'pending' && (
          <>
            <p className="gg-note">
              Still your sign-in address until the new one is confirmed.
            </p>

            <div className="gg-banner" role="status">
              <MailIcon style={{ stroke: 'var(--gg-warning)' }} />
              <span>
                Enter the 6-digit code we sent
                {pendingEmail !== '' ? (
                  <>
                    {' to '}
                    <strong style={{ color: 'var(--gg-fg)', fontWeight: 600 }}>
                      {pendingEmail}
                    </strong>
                  </>
                ) : (
                  ' to your new email address'
                )}{' '}
                to switch your sign-in email.
              </span>
            </div>

            {emailNotice !== null && (
              <div className="gg-banner" data-tone="success" role="status">
                <CheckIcon style={{ stroke: 'var(--gg-success)' }} />
                <span>{emailNotice}</span>
              </div>
            )}

            <form className="gg-form" onSubmit={confirmEmailCode} noValidate>
              <CodeField
                id={codeId}
                label="Confirmation code"
                value={code}
                onChange={setCode}
                disabled={verifyChange.isPending}
                invalid={emailError !== null && !verifyChange.isPending}
              />
              {emailError !== null && (
                <p className="gg-error" role="alert">
                  <AlertIcon />
                  <span>{emailError}</span>
                </p>
              )}
              <button
                type="submit"
                className="gg-button"
                disabled={verifyChange.isPending}
              >
                {verifyChange.isPending && (
                  <Spinner
                    className="gg-spinner"
                    style={{ stroke: 'var(--gg-accent-fg)' }}
                  />
                )}
                {verifyChange.isPending ? 'Confirming…' : 'Confirm new email'}
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
                    disabled={resendChange.isPending}
                    onClick={() => {
                      void resendCode()
                    }}
                  >
                    Resend code
                  </button>
                </>
              )}
            </p>
            <p className="gg-aux">
              <button
                type="button"
                className="gg-link"
                onClick={() => {
                  setEmailStep('editing')
                  setNewEmail(pendingEmail)
                  setEmailError(null)
                  setEmailNotice(null)
                }}
              >
                Use a different address
              </button>
            </p>
          </>
        )}
      </section>

      {/* Danger zone ------------------------------------------------- */}
      <section className="gg-section">
        <h2 className="gg-section-title" data-tone="danger">
          Danger zone
        </h2>

        {deleteStep === 'idle' ? (
          <>
            <p className="gg-note">
              Deleting your account is permanent. Decks, matches and history inside other
              Barrin&rsquo;s apps are removed separately, on each app&rsquo;s own
              schedule.
            </p>
            <button
              type="button"
              className="gg-button-danger gg-button-danger--outline"
              onClick={() => {
                setDeleteError(null)
                setDeleteStep('confirming')
              }}
            >
              Delete account&hellip;
            </button>
          </>
        ) : (
          <form className="gg-form" onSubmit={confirmDelete} noValidate>
            <p className="gg-note">
              This permanently deletes your Barrin&rsquo;s account. You&rsquo;ll be signed
              out of every Barrin&rsquo;s app right away, and this can&rsquo;t be undone.
            </p>
            <div className="gg-banner" data-tone="danger" role="status">
              <AlertIcon style={{ stroke: 'var(--gg-danger)' }} />
              <span>Enter your current password to confirm.</span>
            </div>
            <div className="gg-field">
              <label className="gg-label" htmlFor={passwordId}>
                Current password
              </label>
              <input
                id={passwordId}
                className="gg-input"
                type="password"
                autoComplete="current-password"
                value={password}
                disabled={deleteAccount.isPending}
                aria-invalid={deleteError !== null}
                onChange={(event) => {
                  setPassword(event.target.value)
                }}
              />
            </div>
            {deleteError !== null && (
              <p className="gg-error" role="alert">
                <AlertIcon />
                <span>{deleteError}</span>
              </p>
            )}
            <button
              type="submit"
              className="gg-button-danger"
              disabled={deleteAccount.isPending}
            >
              {deleteAccount.isPending && (
                <Spinner className="gg-spinner" style={{ stroke: 'oklch(0.98 0 0)' }} />
              )}
              {deleteAccount.isPending ? 'Deleting…' : 'Delete my account'}
            </button>
            <p className="gg-aux">
              <button
                type="button"
                className="gg-link"
                onClick={() => {
                  setDeleteStep('idle')
                  setPassword('')
                  setDeleteError(null)
                }}
              >
                Cancel
              </button>
            </p>
          </form>
        )}
      </section>
    </div>
  )
}
