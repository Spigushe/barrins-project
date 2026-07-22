# Ops

Infrastructure and deployment documentation for the Barrin's ecosystem,
structured per Constitution §38:

- [Architecture](architecture/index.md) — infrastructure independence,
  and the decision records behind how secrets and releases are handled.
- [Deployment](deployment/index.md) — backend, frontend, and rollback
  runbooks.
- [Security](security/index.md) — secrets management, TLS, CORS.
- [Operations](operations/index.md) — logging, monitoring, backups
  (including current gaps, documented honestly).
- [Deployment Strategy](deployment_strategy.md) — the broader
  provider-independence principles this infrastructure operates within.

The infrastructure itself (Ansible playbooks and roles) lives at
`ops/my-server/` in this repository — see that directory's README for the
full command reference.
