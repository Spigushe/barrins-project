# Roles

The Ansible roles that make up `ops/my-server/` — each page below is
generated from that role's own `README.md` (see
`docs/hooks/sync_readmes.py`), so it stays in sync with the source of
truth instead of drifting into a second copy.

- [Backend Website](backend_website/index.md) — nginx HTTPS vhost + reverse
  proxy for a backend process.
- [Create SSH Key](create_ssh_key/index.md) — provisions a dedicated
  deploy keypair.
- [FastAPI Backend](fastapi_backend/index.md) — deploys and runs a
  FastAPI app under systemd.
- [pgAdmin](pgadmin/index.md) — pgAdmin4 in Docker, reverse-proxied with
  TLS.
- [React Frontend](react_frontend/index.md) — builds and serves a static
  Node.js frontend.
- [Register SSL](register_ssl/index.md) — issues/renews Let's Encrypt
  certificates.
- [Setup Base User](setup_base_user/index.md) — creates the operational
  Linux user.
- [Setup Packages](setup_packages/index.md) — base OS packages and
  baseline nginx state.

See [Deployment](../deployment/index.md) for how these roles are composed
into the backend and frontend playbooks.
