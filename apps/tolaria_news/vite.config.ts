/// <reference types="vitest/config" />
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

/** The monorepo's release version -- the latest `## [X.Y.Z...]` heading
 * in the repo-root changelog, the single source of truth for it
 * (docs/CHANGELOG.md). Not tolaria_news/package.json's own version,
 * which tracks this app's own release cadence separately. Falls back to
 * "0.0.0-unknown" rather than throwing if the changelog is ever missing
 * or reformatted -- a stale eyebrow label is a much smaller problem than
 * a broken build. */
function readMonorepoVersion(): string {
  try {
    const changelog = readFileSync(
      path.resolve(__dirname, '../../docs/CHANGELOG.md'),
      'utf-8',
    )
    const match = /^## \[([^\]]+)\]/m.exec(changelog)
    return match ? match[1] : '0.0.0-unknown'
  } catch {
    return '0.0.0-unknown'
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  define: {
    __APP_VERSION__: JSON.stringify(readMonorepoVersion()),
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    css: true,
    env: {
      VITE_API_BASE_URL: 'http://localhost:8000',
    },
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html'],
      exclude: ['src/components/ui/**', 'src/components/landing/**', 'src/main.tsx'],
    },
  },
})
