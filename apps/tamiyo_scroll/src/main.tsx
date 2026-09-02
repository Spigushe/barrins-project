import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClientProvider } from '@tanstack/react-query'
import { IdentityProvider } from '@barrins/goblin-guide'
import '@barrins/goblin-guide/styles.css'
import './index.css'
import App from './App.tsx'
import { queryClient } from './lib/queryClient.ts'
import { IDENTITY_COOKIE_MODE, IDENTITY_SERVICE_URL } from './config.ts'
import { identityTokenStore } from './identity.ts'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <IdentityProvider
        config={{
          serviceUrl: IDENTITY_SERVICE_URL,
          cookieMode: IDENTITY_COOKIE_MODE,
          tokenStore: identityTokenStore,
        }}
      >
        <App />
      </IdentityProvider>
    </QueryClientProvider>
  </StrictMode>,
)
