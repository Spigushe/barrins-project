/**
 * Karn Tablets (T4 iteration 2 / T6, ADR-13) — Metagame/Archetypes/Trends
 * pages are prepared ahead of their backend but stay entirely hidden until
 * this is explicitly turned on. Unset in every environment today; flip it
 * once T4 iteration 2 actually ships. See
 * docs/project/v2.0.0-bump/t5-tolaria-news-frontend/index.md.
 */
export const karnTabletsEnabled: boolean =
  import.meta.env.VITE_FEATURE_KARN_TABLETS === 'true'
