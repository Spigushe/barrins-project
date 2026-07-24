import { createStore } from '@/lib/store'

const ACCESS_TOKEN_KEY = 'tamiyo_access_token'
const REFRESH_TOKEN_KEY = 'tamiyo_refresh_token'

export interface Session {
  accessToken: string | null
  refreshToken: string | null
}

function loadSession(): Session {
  return {
    accessToken: localStorage.getItem(ACCESS_TOKEN_KEY),
    refreshToken: localStorage.getItem(REFRESH_TOKEN_KEY),
  }
}

export const sessionStore = createStore<Session>(loadSession())

export function setSession(tokens: {
  access_token: string
  refresh_token: string
}): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token)
  localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token)
  sessionStore.set({
    accessToken: tokens.access_token,
    refreshToken: tokens.refresh_token,
  })
}

export function clearSession(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY)
  localStorage.removeItem(REFRESH_TOKEN_KEY)
  sessionStore.set({ accessToken: null, refreshToken: null })
}

export function isAuthenticated(): boolean {
  return sessionStore.get().accessToken !== null
}
