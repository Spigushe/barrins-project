/** Base URL of the Barrin's Identity service this shell talks to. */
export const IDENTITY_SERVICE_URL: string =
  (import.meta.env.VITE_IDENTITY_SERVICE_URL as string | undefined) ??
  'http://localhost:8001'
