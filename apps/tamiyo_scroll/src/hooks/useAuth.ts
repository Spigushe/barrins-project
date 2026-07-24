import { useSyncExternalStore } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import * as authApi from '@/api/auth'
import { clearSession, type Session, sessionStore, setSession } from '@/api/session'

export function useSession(): Session {
  return useSyncExternalStore(sessionStore.subscribe, sessionStore.get, sessionStore.get)
}

export function useCurrentUser() {
  const session = useSession()
  return useQuery({
    queryKey: ['me'],
    queryFn: authApi.getMe,
    enabled: session.accessToken !== null,
    staleTime: 5 * 60_000,
  })
}

export function useLogin() {
  return useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) =>
      authApi.login(email, password),
    onSuccess: (tokens) => {
      setSession(tokens)
    },
  })
}

export function useSignup() {
  return useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) =>
      authApi.signup(email, password),
    onSuccess: (result) => {
      if (result.tokens) setSession(result.tokens)
    },
  })
}

export function useVerifyEmail() {
  return useMutation({
    mutationFn: ({ email, code }: { email: string; code: string }) =>
      authApi.verifyEmail(email, code),
    onSuccess: (tokens) => {
      setSession(tokens)
    },
  })
}

export function useResendVerification() {
  return useMutation({
    mutationFn: (email: string) => authApi.resendVerification(email),
  })
}

export function useLogout() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: authApi.logout,
    onSettled: () => {
      clearSession()
      queryClient.clear()
    },
  })
}
