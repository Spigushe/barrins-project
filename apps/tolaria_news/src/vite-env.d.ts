/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string
  readonly VITE_FEATURE_KARN_TABLETS?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

/** The monorepo release version, injected at build time from
 * docs/CHANGELOG.md's latest heading -- see vite.config.ts. */
declare const __APP_VERSION__: string
