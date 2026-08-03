# T5. `apps/tolaria_news` real frontend

[← Back to project index](../index.md)

| | | Comment |
| --- | --- | --- |
| **Target** | `apps/tolaria_news` (React/Vite) | Currently a one-line README only |
| **Initial date** | / | Not started |
| **Status** | 🔲 **Blocked** — depends on T4 and I1 | / |
| **Source** | Request item 1 | / |
| **Dependency** | T4, I1 (shared identity — if this app needs auth at all) | Blocks nothing further downstream |

---

## Context

`ops/my-server/tolaria_news.yml` already exists and deploys
`apps/tolaria_news` from this monorepo — it's just waiting for real
code. Its own comments note today's state plainly: "no application code
(README.md only)." Since the Tolaria News BFF (T4) is public/read-only,
this frontend may not need any authentication at all for its core
purpose (browsing tournament results) — worth confirming during design
whether any admin/write surface is planned for it, which would be the
only reason I1 actually blocks this item.

## Done statement

- A real React/Vite app scaffolded at `apps/tolaria_news`, calling only
  T4's BFF (Constitution §4.1/§4.2 — no client-side computation of
  aggregates), matching `VITE_API_BASE_URL`'s existing build-time
  injection pattern already used by `tamiyo_scroll`
  (`ops/my-server/`'s `react_frontend_build_env`).
- Deployable through the existing `tolaria_news.yml` playbook with no
  playbook changes needed — it was built in advance for exactly this.

## Tasks

- [ ] Confirm whether this frontend needs any authenticated surface at
      all for v2.0.0 (if none: I1 stops blocking this item entirely).
- [ ] Scaffold with Vite + React + TypeScript, matching
      `tamiyo_scroll`'s toolchain choices (TanStack Query, Zod, Tailwind,
      shadcn/ui) for consistency unless a reason emerges not to.
- [ ] Build the core screens (tournament list/detail, deck/standing
      views) against T4's routes.
- [ ] Update `apps/tolaria_news/README.md`/`CHANGELOG.md` (currently
      placeholders) with real content.

## UAT (manual)

- [ ] `ansible-playbook tolaria_news.yml -e deploy_env=staging` succeeds
      and serves the real app (today it would serve nothing/fail, since
      there's no code).
- [ ] Browsing the deployed staging site shows real tournament data from
      the BFF, with no client-side recomputation of anything the backend
      already provides.

## Non-regression tests

- New Vitest + Testing Library suite, mirroring `tamiyo_scroll`'s
  existing test conventions (`__tests__/`, component tests colocated
  with pages).
