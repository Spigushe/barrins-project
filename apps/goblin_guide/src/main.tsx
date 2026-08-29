import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { IdentityProvider } from '@barrins/goblin-guide'
import '@barrins/goblin-guide/styles.css'
import './index.css'
import { App } from './App'
import { IDENTITY_SERVICE_URL } from './config'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
      staleTime: 30_000,
    },
  },
})

const identityConfig = { serviceUrl: IDENTITY_SERVICE_URL }

const rootElement = document.getElementById('root')
if (rootElement === null) throw new Error('#root not found')

createRoot(rootElement).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <IdentityProvider config={identityConfig}>
        <App />
      </IdentityProvider>
    </QueryClientProvider>
  </StrictMode>,
)
