# Deployment Strategy — Infrastructure Independence

**Status:** Accepted Architecture
**Version:** 1.0
**Audience:** Solution Architect, DevOps, Backend Developers, Frontend Developers

---

## 1. Purpose

This document defines the deployment strategy for the Barrin's ecosystem.

Its objective is to ensure that deployment infrastructure remains an
implementation detail while all public-facing services remain stable.

Applications, APIs and users must never depend on the hosting provider.

Instead, every public service must be accessed exclusively through Barrin's-owned
domains.

---

## 2. Guiding Principle

Infrastructure providers are replaceable.

Public service endpoints are not.

Every public URL is considered part of the Barrin's public contract.

Changing infrastructure must never require changing application code.

---

## 3. Public Service Endpoints

The following host names are reserved for the Barrin's ecosystem.

| Service | Public URL |
| ------- | ---------- |
| Main API | <https://api.barrins-codex.org> |
| Tamiyo Scroll | <https://tamiyo.barrins-codex.org> |
| Identity Provider (future) | <https://auth.barrins-codex.org> |
| Documentation | <https://docs.barrins-codex.org> |

Additional services should follow the same convention.

Examples:

- admin.barrins-codex.org
- ml.barrins-codex.org
- reports.barrins-codex.org

Applications must always communicate through these public host names.

---

## 4. Infrastructure Independence

Applications must never reference provider-specific URLs.

Forbidden examples:

- <https://tamiyo.vercel.app>
- <https://project.fly.dev>
- <https://project.up.railway.app>
- <https://api.azurewebsites.net>

Provider-specific addresses may exist internally but must never appear in:

- source code;
- configuration distributed to users;
- documentation;
- OAuth redirect URIs intended for production.

The only public endpoints are Barrin's-owned domains.

---

## 5. DNS as the Public Contract

DNS is the abstraction layer between applications and infrastructure.

The DNS records owned by Barrin's determine where services are hosted.

This allows infrastructure changes without affecting clients.

Example:

```text
User
 |
https://tamiyo.barrins-codex.org
 |
Barrin's DNS
 |
Hosting provider
```

Applications remain unaware of the hosting platform.

---

## 6. Current Deployment

Current infrastructure:

- Single VPS
- Barrins API
- Tamiyo Scroll

Typical deployment:

```text
Internet
 |
Reverse Proxy
 |
+-----------------------------+
tamiyo.barrins-codex.org
api.barrins-codex.org
+-----------------------------+
 |
FastAPI
React
 |
PostgreSQL
```

This architecture is intentionally simple.

---

## 7. Future Deployment Options

The deployment strategy supports migrating individual services independently.

Possible future examples:

### Option A

Frontend on Vercel

API on VPS

Identity on VPS

### Option B

Frontend on Cloudflare Pages

API on Railway

Identity on VPS

### Option C

Frontend on Vercel

API on Fly.io

Identity on Google Cloud Run

### Option D

Everything on Kubernetes

The applications remain unchanged.

Only infrastructure changes.

---

## 8. Reverse Proxy

A reverse proxy remains the preferred entry point whenever practical.

Responsibilities:

- HTTPS termination
- request routing
- compression
- caching
- security headers
- logging

Recommended technologies include:

- Caddy
- Nginx
- Traefik

The specific implementation is left to the infrastructure team.

---

## 9. TLS

Every public service must be accessible through HTTPS.

Certificates must:

- renew automatically;
- be monitored;
- never require application changes.

TLS is considered an infrastructure concern.

---

## 10. Environment Strategy

Minimum environments:

- Development
- Testing
- Production

Each environment must have:

- isolated configuration;
- dedicated secrets;
- independent deployments.

Production configuration must never be reused for development.

---

## 11. Configuration Strategy

Applications must be configured through environment variables.

Examples include:

- API base URL
- Identity endpoint
- Database connection
- SMTP configuration

Configuration must not be hardcoded.

---

## 12. Release Strategy

Production deployments must originate from released versions.

The recommended workflow is:

1. Create release.
2. Build release artifact.
3. Deploy artifact.
4. Validate deployment.
5. Monitor.
6. Roll back if necessary.

Development branches must never be deployed directly to production.

---

## 13. Deployment Independence

Every component must be deployable independently.

For example:

Deploying Tamiyo Scroll must not require:

- rebuilding the API;
- migrating the database;
- restarting unrelated services.

Likewise, deploying the API must not require rebuilding frontend applications.

---

## 14. Identity Provider

The future Barrin's Identity application will become another independently
deployable service.

Public endpoint:

<https://auth.barrins-codex.org>

Applications should eventually authenticate through this endpoint while
continuing to communicate with the API using their existing endpoints.

This migration must not require changing the public URLs of existing services.

---

## 15. Provider Migration Strategy

Changing infrastructure providers should follow these principles.

Allowed changes:

- DNS records
- deployment pipeline
- infrastructure configuration
- certificates
- monitoring

Forbidden changes:

- API contracts
- public URLs
- frontend routing
- OAuth client configuration (except provider registration)
- user-facing documentation referencing service URLs

---

## 16. Provider Evaluation Criteria

Infrastructure providers should be evaluated using the following criteria:

### Reliability

- uptime
- operational maturity
- backup capabilities

### Security

- TLS support
- secret management
- access control

### Deployment

- automation
- rollback support
- release management

### Networking

- custom domains
- IPv6
- DNS flexibility

### Cost

- predictable pricing
- scaling costs
- bandwidth

---

## 17. Migration Matrix

| Migration | Application Changes | DNS Changes | CI/CD Changes |
| --------- | ------------------- | ----------- | ------------- |
| VPS → Vercel (Frontend) | No | Yes | Yes |
| VPS → Railway (API) | No | Yes | Yes |
| Railway → AWS | No | Yes | Yes |
| Vercel → Cloudflare Pages | No | Yes | Yes |
| VPS → Kubernetes | No | Usually No | Yes |
| VPS → Azure | No | Yes | Yes |

A successful migration should require infrastructure work only.

---

## 18. Definition of Success

The deployment architecture is considered successful if:

- users never notice infrastructure changes;
- applications never require provider-specific code;
- public service URLs remain stable;
- deployments are independent;
- providers can be replaced with minimal operational effort.

---

## 19. Architectural Rule

Infrastructure is temporary.

Public service URLs are permanent.

Every design decision must preserve this principle.

The Barrin's ecosystem owns its domains.

Hosting providers are implementation details.
