import { QueryClient } from '@tanstack/react-query'
import { ApiError } from '@/api/client'

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (failureCount, error) => {
        // Don't retry on client errors (4xx) — only network/server errors
        // (5xx, timeout) are worth retrying.
        if (error instanceof ApiError && error.status < 500) return false
        return failureCount < 2
      },
      staleTime: 30_000,
    },
  },
})
