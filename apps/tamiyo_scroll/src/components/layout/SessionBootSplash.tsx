/**
 * Shown while the identity provider makes its one-shot cookie-mode session
 * restore on page load (ADR-18). Without it, a reload with a valid refresh
 * cookie would briefly flash the login screen before the session comes back.
 */
export function SessionBootSplash() {
  return (
    <div className="flex min-h-svh items-center justify-center bg-background">
      <p className="text-[13px] text-muted-foreground">Restoring your session…</p>
    </div>
  )
}
