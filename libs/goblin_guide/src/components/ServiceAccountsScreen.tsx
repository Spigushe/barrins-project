import { type FormEvent, type KeyboardEvent, useId, useState } from 'react'
import { IdentityError } from '../auth/client'
import {
  useCreateServiceAccount,
  useCurrentUser,
  useRevokeServiceAccount,
  useServiceAccounts,
} from '../auth/hooks'
import type { ServiceAccount, ServiceAccountCreated } from '../auth/schemas'
import {
  AlertIcon,
  CheckIcon,
  CloseIcon,
  CopyIcon,
  KeyIcon,
  ShieldMark,
  Spinner,
} from './icons'
import '../styles.css'

export interface ServiceAccountsScreenProps {
  /** Called by the "Back to my account" button on the non-admin panel. */
  onBack?: () => void
  /** Heading. */
  title?: string
  /** Line under the heading. */
  subtitle?: string
}

const GENERIC_ERROR = 'Something went wrong. Please try again.'

function messageOf(err: unknown): string {
  return err instanceof IdentityError ? err.message : GENERIC_ERROR
}

function formatDate(iso: string): string {
  const date = new Date(iso)
  return Number.isNaN(date.getTime())
    ? iso
    : new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(date)
}

/**
 * Admin service-account management (`G-03` step 5 / `G-04`,
 * integration.md §4.6). A `useCurrentUser()` gate: non-admins get the
 * access panel, admins get the list + create + revoke flows.
 */
export function ServiceAccountsScreen({
  onBack,
  title = 'Service accounts',
  subtitle = "Machine-to-machine credentials for Barrin's apps and jobs — each one authenticates without a user. Administrators only.",
}: ServiceAccountsScreenProps) {
  const { data: user } = useCurrentUser()

  if (user === undefined) {
    return (
      <div className="gg-scope gg-account">
        <h1 className="gg-account-title">{title}</h1>
        <p className="gg-account-lede">Loading…</p>
      </div>
    )
  }

  if (user.role !== 'admin') {
    return <ForbiddenPanel onBack={onBack} />
  }

  return <ServiceAccountsAdmin title={title} subtitle={subtitle} />
}

function ForbiddenPanel({ onBack }: { onBack?: () => void }) {
  return (
    <div className="gg-scope">
      <div
        className="gg-card"
        style={{ maxWidth: 400, margin: '0 auto', textAlign: 'center' }}
      >
        <div className="gg-brand">
          <ShieldMark />
          <h1 className="gg-title">Administrator access required</h1>
          <p className="gg-subtitle">
            Your account doesn&rsquo;t have permission to manage service accounts. If you
            think this is a mistake, contact a Barrin&rsquo;s administrator.
          </p>
        </div>
        {onBack && (
          <button
            type="button"
            className="gg-button gg-button--secondary"
            onClick={onBack}
          >
            Back to my account
          </button>
        )}
      </div>
    </div>
  )
}

interface AdminProps {
  title: string
  subtitle: string
}

function ServiceAccountsAdmin({ title, subtitle }: AdminProps) {
  const descId = useId()
  const scopeId = useId()

  const list = useServiceAccounts()
  const create = useCreateServiceAccount()
  const revoke = useRevokeServiceAccount()

  // --- create form ------------------------------------------------------
  const [description, setDescription] = useState('')
  const [scopes, setScopes] = useState<string[]>([])
  const [scopeDraft, setScopeDraft] = useState('')
  const [formError, setFormError] = useState<string | null>(null)

  // --- one-time secret panel -----------------------------------------
  const [created, setCreated] = useState<ServiceAccountCreated | null>(null)
  const [copied, setCopied] = useState<'id' | 'secret' | null>(null)

  // --- revoke confirmation -----------------------------------------
  const [revoking, setRevoking] = useState<ServiceAccount | null>(null)
  const [revokeError, setRevokeError] = useState<string | null>(null)

  function addScope(raw: string) {
    const scope = raw.trim()
    setScopeDraft('')
    if (scope === '' || scopes.includes(scope)) return
    setScopes([...scopes, scope])
  }

  function onScopeKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'Enter' || event.key === ',') {
      event.preventDefault()
      addScope(scopeDraft)
    } else if (event.key === 'Backspace' && scopeDraft === '' && scopes.length > 0) {
      setScopes(scopes.slice(0, -1))
    }
  }

  async function submitCreate(event: FormEvent) {
    event.preventDefault()
    setFormError(null)
    const draft = scopeDraft.trim()
    const finalScopes =
      draft !== '' && !scopes.includes(draft) ? [...scopes, draft] : scopes
    if (finalScopes.length === 0) {
      setFormError('Add at least one scope.')
      return
    }
    try {
      const result = await create.mutateAsync({
        description: description.trim() === '' ? undefined : description.trim(),
        scopes: finalScopes,
      })
      setCreated(result)
      setDescription('')
      setScopes([])
      setScopeDraft('')
    } catch (err) {
      setFormError(messageOf(err))
    }
  }

  function copy(text: string, key: 'id' | 'secret') {
    void navigator.clipboard?.writeText(text)
    setCopied(key)
    window.setTimeout(() => {
      setCopied(null)
    }, 2000)
  }

  async function confirmRevoke() {
    if (revoking === null) return
    setRevokeError(null)
    try {
      await revoke.mutateAsync(revoking.client_id)
      setRevoking(null)
    } catch (err) {
      setRevokeError(messageOf(err))
    }
  }

  // One-time secret panel takes over the screen until dismissed.
  if (created !== null) {
    return (
      <div className="gg-scope gg-account">
        <h1 className="gg-account-title">Service account created</h1>
        <p className="gg-account-lede">
          Copy the client secret now — it is shown once and cannot be retrieved again.
          Only its hash is stored.
        </p>

        <section className="gg-section">
          <div className="gg-banner" data-tone="warning" role="status">
            <AlertIcon style={{ stroke: 'var(--gg-warning)' }} />
            <span>
              This is the only time the secret is displayed. Store it in your secrets
              manager before you leave this page.
            </span>
          </div>

          <div className="gg-field" style={{ marginTop: 16 }}>
            <span className="gg-label">Client ID</span>
            <div className="gg-cred">
              <code className="gg-cred-val">{created.client_id}</code>
              <button
                type="button"
                className="gg-icon-btn"
                aria-label="Copy client ID"
                onClick={() => {
                  copy(created.client_id, 'id')
                }}
              >
                {copied === 'id' ? (
                  <CheckIcon style={{ stroke: 'var(--gg-success)' }} />
                ) : (
                  <CopyIcon />
                )}
              </button>
            </div>
          </div>

          <div className="gg-field" style={{ marginTop: 14 }}>
            <span className="gg-label">Client secret</span>
            <div className="gg-cred">
              <code className="gg-cred-val">{created.client_secret}</code>
              <button
                type="button"
                className="gg-icon-btn"
                aria-label="Copy client secret"
                onClick={() => {
                  copy(created.client_secret, 'secret')
                }}
              >
                {copied === 'secret' ? (
                  <CheckIcon style={{ stroke: 'var(--gg-success)' }} />
                ) : (
                  <CopyIcon />
                )}
              </button>
            </div>
            <span className="gg-hint">
              Exchanged for a short-lived service token at{' '}
              <code>POST /api/v1/service-token</code>.
            </span>
          </div>

          {created.scopes.length > 0 && (
            <div className="gg-field" style={{ marginTop: 14 }}>
              <span className="gg-label">Scopes</span>
              <div className="gg-sa-chips">
                {created.scopes.map((scope) => (
                  <span key={scope} className="gg-sa-chip">
                    {scope}
                  </span>
                ))}
              </div>
            </div>
          )}

          <button
            type="button"
            className="gg-button"
            onClick={() => {
              setCreated(null)
              setCopied(null)
            }}
          >
            Done — I&rsquo;ve saved these credentials
          </button>
        </section>
      </div>
    )
  }

  // Revoke confirmation takes over the screen until confirmed or cancelled.
  if (revoking !== null) {
    return (
      <div className="gg-scope gg-account">
        <h1 className="gg-account-title">Revoke service account</h1>
        <p className="gg-account-lede">
          Revoking is immediate and permanent. The account stays in the list, marked
          revoked, for the audit trail.
        </p>

        <div className="gg-sa-card" style={{ marginTop: 20 }}>
          <div className="gg-sa-head">
            <code className="gg-sa-id">{revoking.client_id}</code>
            <StatusChip active={revoking.is_active} />
          </div>
          <p className="gg-sa-desc">{revoking.description ?? 'No description'}</p>
          {revoking.scopes.length > 0 && (
            <div className="gg-sa-chips">
              {revoking.scopes.map((scope) => (
                <span key={scope} className="gg-sa-chip">
                  {scope}
                </span>
              ))}
            </div>
          )}
        </div>

        <section className="gg-section">
          <h2 className="gg-section-title" data-tone="danger">
            Confirm revocation
          </h2>
          <div className="gg-banner" data-tone="danger" role="alert">
            <AlertIcon style={{ stroke: 'var(--gg-danger)' }} />
            <span>
              Every token issued to{' '}
              <strong style={{ color: 'var(--gg-fg)', fontWeight: 600 }}>
                {revoking.client_id}
              </strong>{' '}
              stops working right away. Any app or job still using these credentials will
              start getting 401s.
            </span>
          </div>
          <p className="gg-note">
            There is no un-revoke. To restore access, create a new service account and
            roll the credentials.
          </p>
          {revokeError !== null && (
            <p className="gg-error" role="alert">
              <AlertIcon />
              <span>{revokeError}</span>
            </p>
          )}
          <button
            type="button"
            className="gg-button-danger"
            disabled={revoke.isPending}
            onClick={() => {
              void confirmRevoke()
            }}
          >
            {revoke.isPending && (
              <Spinner className="gg-spinner" style={{ stroke: 'oklch(0.98 0 0)' }} />
            )}
            {revoke.isPending ? 'Revoking…' : 'Revoke service account'}
          </button>
          <p className="gg-aux">
            <button
              type="button"
              className="gg-link"
              onClick={() => {
                setRevoking(null)
                setRevokeError(null)
              }}
            >
              Cancel
            </button>
          </p>
        </section>
      </div>
    )
  }

  const accounts =
    list.data === undefined
      ? undefined
      : [...list.data].sort(
          (a, b) =>
            Number(b.is_active) - Number(a.is_active) ||
            b.created_at.localeCompare(a.created_at),
        )

  return (
    <div className="gg-scope gg-account">
      <h1 className="gg-account-title">{title}</h1>
      <p className="gg-account-lede">{subtitle}</p>

      {/* Create ---------------------------------------------------------- */}
      <section className="gg-section">
        <h2 className="gg-section-title">New service account</h2>
        <form className="gg-form" onSubmit={submitCreate} noValidate>
          <div className="gg-field">
            <label className="gg-label" htmlFor={descId}>
              Description{' '}
              <span style={{ textTransform: 'none', fontWeight: 400 }}>(optional)</span>
            </label>
            <input
              id={descId}
              className="gg-input"
              type="text"
              value={description}
              disabled={create.isPending}
              placeholder="e.g. Tolaria News BFF cache warmer"
              onChange={(event) => {
                setDescription(event.target.value)
              }}
            />
            <span className="gg-hint">
              Shown in the list so you can tell accounts apart.
            </span>
          </div>

          <div className="gg-field">
            <label className="gg-label" htmlFor={scopeId}>
              Scopes
            </label>
            <div style={{ display: 'flex', gap: 8, alignItems: 'stretch' }}>
              <div className="gg-taginput" style={{ flex: 1 }}>
                {scopes.map((scope) => (
                  <span key={scope} className="gg-tag">
                    {scope}
                    <button
                      type="button"
                      aria-label={`Remove ${scope}`}
                      disabled={create.isPending}
                      onClick={() => {
                        setScopes(scopes.filter((s) => s !== scope))
                      }}
                    >
                      <CloseIcon />
                    </button>
                  </span>
                ))}
                <input
                  id={scopeId}
                  className="gg-tag-field"
                  type="text"
                  value={scopeDraft}
                  disabled={create.isPending}
                  placeholder={scopes.length === 0 ? 'e.g. bs:read' : 'Add another'}
                  onChange={(event) => {
                    setScopeDraft(event.target.value)
                  }}
                  onKeyDown={onScopeKeyDown}
                />
              </div>
              <button
                type="button"
                className="gg-button gg-button--sm gg-button--secondary"
                disabled={create.isPending || scopeDraft.trim() === ''}
                onClick={() => {
                  addScope(scopeDraft)
                }}
              >
                Add
              </button>
            </div>
            <span className="gg-hint">
              A scope is a permission string the target service checks — e.g.{' '}
              <code>bs:read</code>, <code>kt:read</code>. Type one and press Enter (or
              click Add); repeat for more. At least one is required.
            </span>
          </div>

          {formError !== null && (
            <p className="gg-error" role="alert">
              <AlertIcon />
              <span>{formError}</span>
            </p>
          )}

          <button type="submit" className="gg-button" disabled={create.isPending}>
            {create.isPending && (
              <Spinner className="gg-spinner" style={{ stroke: 'var(--gg-accent-fg)' }} />
            )}
            {create.isPending ? 'Creating…' : 'Create service account'}
          </button>
        </form>
      </section>

      {/* List ---------------------------------------------------------- */}
      <section className="gg-section">
        <h2 className="gg-section-title">
          Existing accounts
          {accounts !== undefined && accounts.length > 0 && ` · ${accounts.length}`}
        </h2>

        {list.isLoading && <p className="gg-note">Loading service accounts…</p>}

        {list.isError && (
          <p className="gg-error" role="alert">
            <AlertIcon />
            <span>{messageOf(list.error)}</span>
          </p>
        )}

        {accounts !== undefined && accounts.length === 0 && (
          <div className="gg-sa-empty">
            <KeyIcon width={26} height={26} style={{ stroke: 'var(--gg-subtle)' }} />
            <p>
              No service accounts yet. Create one above to let an app or scheduled job
              call Barrin&rsquo;s services without a user signed in.
            </p>
          </div>
        )}

        {accounts !== undefined && accounts.length > 0 && (
          <div className="gg-sa-list">
            {accounts.map((account) => (
              <ServiceAccountCard
                key={account.id}
                account={account}
                onRevoke={() => {
                  setRevokeError(null)
                  setRevoking(account)
                }}
              />
            ))}
          </div>
        )}
      </section>
    </div>
  )
}

function StatusChip({ active }: { active: boolean }) {
  return (
    <span className="gg-status" data-tone={active ? 'active' : 'revoked'}>
      <span className="gg-status-dot" />
      {active ? 'Active' : 'Revoked'}
    </span>
  )
}

function ServiceAccountCard({
  account,
  onRevoke,
}: {
  account: ServiceAccount
  onRevoke: () => void
}) {
  return (
    <div className="gg-sa-card">
      <div className="gg-sa-head">
        <code className="gg-sa-id">{account.client_id}</code>
        <StatusChip active={account.is_active} />
      </div>
      <p className="gg-sa-desc">{account.description ?? 'No description'}</p>
      {account.scopes.length > 0 && (
        <div className="gg-sa-chips">
          {account.scopes.map((scope) => (
            <span key={scope} className="gg-sa-chip">
              {scope}
            </span>
          ))}
        </div>
      )}
      <div className="gg-sa-meta">
        <span className="gg-sa-created">Created {formatDate(account.created_at)}</span>
        {account.is_active && (
          <button
            type="button"
            className="gg-button-danger gg-button-danger--outline gg-button--sm"
            onClick={onRevoke}
          >
            Revoke
          </button>
        )}
      </div>
    </div>
  )
}
