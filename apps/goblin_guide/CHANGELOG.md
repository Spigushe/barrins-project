# Changelog

Format: Keep a Changelog + Semantic Versioning — see the Changelog
section of the docs site for details.

## [2.0.0] "Morningtide" - 2026-09-06

### Added

- Initial standalone shell for Goblin Guide (T11-T15), serving the
  canonical `goblin.barrins-codex.org` and giving the Karn Tablets
  Jupyter reverse-proxy (T9) a login page to redirect to. A thin
  router + `QueryClientProvider` + `IdentityProvider` (cookie mode,
  ADR-18) around the shared `@barrins/goblin-guide` library
  (`libs/goblin_guide/`), which holds every actual screen/hook/token
  handling — see that package's own changelog for the T11-T15 slices
  themselves (login, signup/verify, password reset, account
  settings/delete, admin service accounts).
- Deploy playbook: `ops/my-server/goblin_guide.yml` (rollout Phase 5),
  a frontend-only SPA playbook calling `barrins_identity` directly in
  cookie mode, never `barrins_api`.
- Mounted as the "Manage my account" destination from `apps/tamiyo_scroll`
  (rollout Phase 7+8, ADR-20) via `?return_to=`/`?return_label=`, so its
  header can offer a "← Back to Tamiyo Scroll" link home.

## [1.0.0] "WorldWake" - 2026-07-24

Nothing yet.
