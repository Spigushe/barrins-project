import { type FormEvent, useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { ApiError } from '@/api/client'
import { useResendVerification, useVerifyEmail } from '@/hooks/useAuth'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

const RESEND_COOLDOWN_SECONDS = 60

export function VerifyEmailPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  const [email, setEmail] = useState(searchParams.get('email') ?? '')
  const [code, setCode] = useState(searchParams.get('code') ?? '')
  const [error, setError] = useState<string | null>(null)
  const [resendMessage, setResendMessage] = useState<string | null>(null)
  const [cooldown, setCooldown] = useState(0)

  const verify = useVerifyEmail()
  const resend = useResendVerification()

  useEffect(() => {
    if (cooldown <= 0) return
    const timer = window.setInterval(() => {
      setCooldown((current) => Math.max(0, current - 1))
    }, 1000)
    return () => {
      window.clearInterval(timer)
    }
  }, [cooldown])

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)

    if (!email || !/^\d{6}$/.test(code)) {
      setError('Email et code à 6 chiffres requis.')
      return
    }

    try {
      await verify.mutateAsync({ email, code })
      navigate('/app/metagame')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Une erreur est survenue.')
    }
  }

  async function handleResend() {
    setError(null)
    setResendMessage(null)
    if (!email) {
      setError('Renseignez votre email pour recevoir un nouveau code.')
      return
    }
    try {
      const response = await resend.mutateAsync(email)
      setResendMessage(response.detail)
      setCooldown(RESEND_COOLDOWN_SECONDS)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Une erreur est survenue.')
    }
  }

  return (
    <div className="flex min-h-svh items-center justify-center px-4">
      <div className="w-full max-w-[400px] rounded-(--radius-login-card) border border-border bg-card p-8">
        <h1 className="text-center text-xl font-extrabold text-foreground">
          Vérifiez votre email
        </h1>
        <p className="mt-1 text-center text-[13px] text-muted-foreground">
          Saisissez le code à 6 chiffres envoyé à votre adresse — ou suivez le lien reçu
          par email puis confirmez ci-dessous.
        </p>

        <form className="mt-6 flex flex-col gap-3" onSubmit={handleSubmit}>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="verify-email">Email</Label>
            <Input
              id="verify-email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(event) => {
                setEmail(event.target.value)
              }}
              className="rounded-[8px] text-sm"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="code">Code de vérification</Label>
            <Input
              id="code"
              inputMode="numeric"
              autoComplete="one-time-code"
              maxLength={6}
              value={code}
              onChange={(event) => {
                setCode(event.target.value.replace(/\D/g, '').slice(0, 6))
              }}
              className="rounded-[8px] text-center font-mono text-sm tracking-[0.3em]"
            />
          </div>

          {error !== null && <p className="text-[12.5px] text-destructive">{error}</p>}
          {resendMessage !== null && (
            <p className="text-[12.5px] text-success">{resendMessage}</p>
          )}

          <Button
            type="submit"
            disabled={verify.isPending}
            className="mt-2 h-auto w-full rounded-[8px] py-3 font-bold"
          >
            Confirmer mon compte
          </Button>

          <Button
            type="button"
            variant="outline"
            disabled={resend.isPending || cooldown > 0}
            onClick={handleResend}
            className="h-auto w-full rounded-[8px] py-2.5 text-sm"
          >
            {cooldown > 0
              ? `Renvoyer le code (${String(cooldown)}s)`
              : 'Renvoyer le code'}
          </Button>
        </form>

        <p className="mt-4 text-center text-[13px] text-muted-foreground">
          <button
            type="button"
            className="cursor-pointer font-semibold text-accent hover:underline"
            onClick={() => {
              navigate('/login')
            }}
          >
            Retour à la connexion
          </button>
        </p>

        <p className="mt-6 border-t border-border pt-4 text-center text-[11.5px] text-subtle-foreground">
          Compte géré par barrins_api.
        </p>
      </div>
    </div>
  )
}
