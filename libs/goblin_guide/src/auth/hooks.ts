import { useSyncExternalStore } from 'react'
import {
  useMutation,
  type UseMutationResult,
  useQuery,
  useQueryClient,
  type UseQueryResult,
} from '@tanstack/react-query'
import { useIdentityContext } from './context'
import type { Principal } from './schemas'

const ME_QUERY_KEY = ['goblin-guide', 'me'] as const

/** Reactive authentication state, derived from the token store. */
export function useIdentity(): { isAuthenticated: boolean } {
  const { tokenStore } = useIdentityContext()
  const access = useSyncExternalStore(
    tokenStore.subscribe,
    tokenStore.getAccess,
    tokenStore.getAccess,
  )
  return { isAuthenticated: access !== null }
}

/** `GET /api/v1/auth/me`, enabled once there is an access token. */
export function useCurrentUser(): UseQueryResult<Principal> {
  const { client } = useIdentityContext()
  const { isAuthenticated } = useIdentity()
  return useQuery({
    queryKey: ME_QUERY_KEY,
    queryFn: () => client.me(),
    enabled: isAuthenticated,
    staleTime: 5 * 60_000,
  })
}

export interface LoginVariables {
  email: string
  password: string
}

/** `POST /api/v1/auth/token`. On success the token store is populated. */
export function useLogin(): UseMutationResult<unknown, Error, LoginVariables> {
  const { client } = useIdentityContext()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ email, password }: LoginVariables) => client.login(email, password),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ME_QUERY_KEY })
    },
  })
}

/** `POST /api/v1/auth/logout`. Clears cached queries once settled. */
export function useLogout(): UseMutationResult<void, Error, void> {
  const { client } = useIdentityContext()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => client.logout(),
    onSettled: () => {
      queryClient.clear()
    },
  })
}
