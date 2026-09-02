/// <reference types="vitest/config" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // `@barrins/goblin-guide` is a symlinked path dependency with its own
  // node_modules; without dedupe, React (and other hook-bearing peers)
  // would resolve to a second copy inside it and break the hooks
  // dispatcher.
  resolve: {
    dedupe: ['react', 'react-dom', 'react-router-dom', '@tanstack/react-query'],
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    server: {
      deps: {
        inline: ['@barrins/goblin-guide'],
      },
    },
    css: true,
    env: {
      VITE_IDENTITY_SERVICE_URL: 'http://localhost:8001',
    },
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html'],
      exclude: ['src/main.tsx'],
    },
  },
})
