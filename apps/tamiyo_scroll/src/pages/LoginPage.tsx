import { type FormEvent, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ApiError } from '@/api/client'
import { useLogin, useSignup } from '@/hooks/useAuth'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

export function LoginPage() {
  const navigate = useNavigate()
  const [isSignup, setIsSignup] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)

  const login = useLogin()
  const signup = useSignup()
  const pending = login.isPending || signup.isPending

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)

    if (!email || !password) {
      setError('Email and password required.')
      return
    }

    try {
      if (isSignup) {
        const result = await signup.mutateAsync({ email, password })
        if (result.verification_required) {
          navigate(`/verify-email?email=${encodeURIComponent(email)}`)
        } else {
          navigate('/app/metagame')
        }
      } else {
        await login.mutateAsync({ email, password })
        navigate('/app/metagame')
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'An error occurred.')
    }
  }

  return (
    <div className="flex min-h-svh items-center justify-center px-4">
      <div className="w-full max-w-[400px] rounded-(--radius-login-card) border border-border bg-card p-8">
        <h1 className="text-center text-xl font-extrabold text-foreground">
          Competitive MTG Tracker
        </h1>
        <p className="mt-1 text-center text-[13px] text-muted-foreground">
          {isSignup ? 'Create an account' : 'Log in to your tracker'}
        </p>

        <form className="mt-6 flex flex-col gap-3" onSubmit={handleSubmit}>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
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
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              type="password"
              autoComplete={isSignup ? 'new-password' : 'current-password'}
              value={password}
              onChange={(event) => {
                setPassword(event.target.value)
              }}
              className="rounded-[8px] text-sm"
            />
          </div>

          {error !== null && <p className="text-[12.5px] text-destructive">{error}</p>}

          <Button
            type="submit"
            disabled={pending}
            className="mt-2 h-auto w-full rounded-[8px] py-3 font-bold"
          >
            {isSignup ? 'Create account' : 'Log in'}
          </Button>
        </form>

        <p className="mt-4 text-center text-[13px] text-muted-foreground">
          {isSignup ? 'Already have an account?' : "Don't have an account yet?"}{' '}
          <button
            type="button"
            className="cursor-pointer font-semibold text-accent hover:underline"
            onClick={() => {
              setIsSignup((current) => !current)
              setError(null)
            }}
          >
            {isSignup ? 'Log in' : 'Create an account'}
          </button>
        </p>

        <p className="mt-6 border-t border-border pt-4 text-center text-[11.5px] text-subtle-foreground">
          Account managed by barrins_identity.
        </p>
      </div>
    </div>
  )
}
