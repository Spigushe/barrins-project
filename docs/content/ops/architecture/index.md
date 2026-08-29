# Infrastructure Architecture

- [Infrastructure Independence](independence.md) — why `ops/my-server/`
  lives in this monorepo, and how one-playbook-per-application is enforced.
- [Decision Records](decisions.md) — secrets management (ADR-1),
  release-tag deployment (ADR-2), production email sending (ADR-3), the
  v1.0.0 release's backup/monitoring/Moxfield decisions (ADR-4), adopting
  Barrin's Identity as the RS256/JWKS authority (ADR-16, which lifts
  ADR-7's delay), and `identity_client` / Goblin Guide as shared monorepo
  packages (ADR-17), in Constitution §16.3 format.
- [Deployment Strategy](../deployment_strategy.md) — the broader
  provider-independence principles (DNS as the public contract, provider
  evaluation criteria, migration matrix) these decisions operate within.
