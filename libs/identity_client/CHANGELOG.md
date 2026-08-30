# Changelog

Format: Keep a Changelog + Semantic Versioning — see the Changelog
section of the docs site for details.

## [Unreleased]

### Added

- Initial package (T10): `JWKSCache` (fetch + monotonic-TTL cache +
  refresh-on-unknown-`kid`), the framework-free `verify_token` returning
  a `VerifiedPrincipal`, and `make_verify_dependency` for FastAPI
  consumers. Verifies the RS256 user/service token format issued by
  `apps/barrins_identity` (integration.md §2–§3). Not yet wired into any
  consumer — `apps/barrins_api` adopts it at the cutover
  (platform.md §10).
