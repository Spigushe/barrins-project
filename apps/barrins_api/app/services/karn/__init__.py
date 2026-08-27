"""Karn Tablets domain services (ADR-13).

Isolated from `app/services/metrics/` (Tamiyo-Scroll-only) per
Constitution §45.1 — machine-learning-adjacent data stays out of the
core/report services.

- `ingester` — persists a pushed clustering run into `kt_*`, matching each
  cluster to a stable archetype identity.
- `read` — the shared read layer behind both the public Tolaria News BFF
  routes and the S6 admin dashboard route (§4.2 — one implementation, two
  callers).
"""
