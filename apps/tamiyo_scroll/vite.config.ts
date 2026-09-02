/// <reference types="vitest/config" />
import path from 'node:path'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
    // `@barrins/goblin-guide` is a symlinked path dependency with its own
    // node_modules; without dedupe, React (and other hook-bearing peers)
    // would resolve to a second copy inside it and break the hooks
    // dispatcher. Mirrors `apps/goblin_guide/vite.config.ts`.
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
      VITE_API_BASE_URL: 'http://localhost:8000',
      VITE_IDENTITY_SERVICE_URL: 'http://localhost:8001',
    },
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html'],
      exclude: ['src/components/ui/**', 'src/main.tsx'],
    },
  },
})
