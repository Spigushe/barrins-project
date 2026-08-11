# Incident: VPS's outbound connection to mtgo.com appears blocked at the network level

## Status tracking

| Field | Value |
| --- | --- |
| Status | Mitigated — fix decided and implemented (ADR-12: move scraping+sweep to GitHub Actions); rollout (secrets, smoke test, VPS teardown) pending |
| Severity | High if confirmed on production — MTGO ingestion would be silently returning 0 tournaments, not erroring |
| Reported | 2026-08-10 |
| Resolved | — |
| Area | Barrin's Scripture — MTGO scraper, and possibly the VPS's outbound network path in general |
| Blocking | Any MTGO scrape (backfill or scheduled) from this VPS |
| Owner | Infrastructure (Agent 3) — this is not fixable in application code |

## Summary

A manual backfill run on staging:

```bash
uv run scrape --source mtgo --date-from 2025-11 --date-to 2025-11 \
  --output-dir /home/spigushe/archives/barrins_scripture-staging
```

logged `2025-11: found 0 tournaments to scrape` with no exception. Two
code-level fixes were tried and deployed in sequence before the
investigation found the actual cause was outside the application entirely.

## Investigation timeline

1. **Hypothesis 1 — page-load timeout too short.** `PAGE_LOAD_TIMEOUT` (30s)
   was a fixed ceiling on `driver.get()` that never grew across retries,
   unlike the `WebDriverWait` render timeout which already widened by 10s
   per attempt. Fixed and deployed
   (`fix(scripture): scale the MTGO page-load timeout across retries`,
   base raised to 45s, now scales on retry like the render-wait timeout).
   **Did not fix the symptom** — same `found 0 tournaments` after redeploy.

2. **Hypothesis 2 — `load` event never fires.** Selenium's default
   `page_load_strategy="normal"` blocks `driver.get()` until every
   subresource (ads/trackers/beacons) finishes loading; one stuck
   subresource on a heavy page would explain a `TimeoutException: Timed out
   receiving message from renderer` regardless of timeout size. Switched to
   `page_load_strategy="eager"` (DOM-ready only) and deployed
   (`fix(scripture): switch MTGO scraper to eager page-load strategy`).
   **Also did not fix it** — identical renderer-timeout error persisted,
   confirmed against the redeployed commit (`git log -1` on the VPS matched).

3. **Direct diagnostic via Selenium** (`driver.get()` against the MTGO
   homepage, a recent month that the daily cron scrapes successfully, and
   the target month) — **all three failed identically**, ruling out
   anything page-specific or date-specific.

4. **`curl` from the VPS itself** to the same URL: `HTTP:000 TIME:131s
   SIZE:0` — no response at all, not a slow one. This is a connection-level
   failure, not an application-level block (which would return a real HTTP
   status).

5. **IPv6 red herring ruled out.** The VPS's default egress showed an IPv6
   address, but `getent ahosts mtgo.com` resolves only an IPv4 address
   (`64.37.171.30`, no `AAAA` record) — `curl -6` failing instantly is
   expected and irrelevant.

6. **`curl -4` forcing the actual (only) address mtgo.com has** still hung
   ~130s and returned nothing. **This eliminates every remaining
   application/DNS/protocol-preference explanation.**

7. **Control domains** (`example.com`, `github.com`) over the same `-4`
   path succeeded instantly — the VPS's general outbound internet is fine.

8. **Direct-IP request bypassing DNS** (`curl -4 -H "Host: mtgo.com"
   https://64.37.171.30 -k`) also failed identically — rules out DNS
   poisoning/hijacking as the cause.

9. **`mtr`/`traceroute` to `64.37.171.30`** showed a clean path through the
   VPS's provider (OVH, Paris) all the way to a Las Vegas hop
   (`ae0.11.bar1.LasVegas1.net`), then **100% packet loss** on every hop
   beyond that — consistent with the destination (or something immediately
   in front of it) silently dropping/blackholing traffic from this VPS's
   IP, rather than a routing failure anywhere on the VPS's own path.

10. **The same unmodified scraper code, run from two other networks,
    works fine.** From a personal laptop (`uv run --active scrape
    --source mtgo --date-from 2015-11 --date-to 2015-11`): `found 427
    tournaments to scrape`, no errors. GitHub Actions runner IPs (the
    old pre-migration scraping path, per T1) were also unaffected. Both
    are datacenter/hosting-adjacent IPs in the broad sense (GH Actions
    runners especially), yet neither is blocked — this rules out a
    blanket "block all datacenter IPs" policy on mtgo.com's side.

## Root cause (as currently understood)

This VPS's specific IP (`146.59.146.57`) appears to be individually
blocked or null-routed by mtgo.com's edge/WAF — not a blanket
datacenter/hosting-range policy (a laptop IP and GitHub Actions runner
IPs both reach mtgo.com fine with the same unmodified code), and not
this VPS's network path in general (control domains and even mtgo.com's
own IP direct-dialed all fail identically only for this one host). This
is the classic signature of a specific address getting individually
flagged/blackholed — plausibly tied to this VPS's own prior scraping
traffic pattern/volume, rather than an IP-range or protocol issue. No
application-level fix (timeout tuning, page-load strategy, retries) can
address a TCP connection that never completes.

**Confirmed:** the block is specific to this one VPS IP, not the
provider's range/ASN — narrows the fix options toward "get this VPS a
different IP" over "route around a whole blocked range."

## Impact — needs confirmation

Staging and production run as independent instances but **share the same
VPS and outbound IP** (`146.59.146.57`). If the block affects that IP
generally, the production MTGO scrape (daily, 22:00 UTC) is likely also
silently returning 0 tournaments — no exception is raised, so nothing
would have surfaced this on its own. `journalctl -u barrins_scripture` on
the VPS should be checked to determine how long this has been happening
in production, separately from this staging investigation.

## Changes made during this investigation (kept, but did not resolve the issue)

- `fix(scripture): scale the MTGO page-load timeout across retries` —
  legitimate independent improvement (a fixed non-scaling page-load
  ceiling was a real, if secondary, issue), but not the cause of the
  `found 0 tournaments` symptom.
- `fix(scripture): switch MTGO scraper to eager page-load strategy` —
  same: a reasonable change (avoids blocking on unrelated slow
  subresources) that doesn't address a connection that never completes at
  all.

Both are covered by unit tests and pass lint/type-check; neither is being
reverted, since they're correct independent of this incident.

## Resolution

**Decided and implemented (2026-08-10):** move MTGO + MTGTop8 scraping
and the sweep/ingestion tick from the VPS's systemd timers to a new
GitHub Actions workflow, `.github/workflows/scripture-scrape.yml` —
GitHub Actions runner IPs are confirmed unaffected (investigation step
10 above), and the repo being public means this costs nothing in Actions
minutes. Full alternatives/trade-offs writeup: **ADR-12**,
`docs/content/ops/architecture/decisions.md`.

`ops/my-server/roles/scripture_scraper/` is not deleted — its
`.service`/`.timer` units, wrapper scripts, local archive clone, and app
checkout are torn down on the VPS via a new `scripture_scraper_teardown`
role var (`ops/my-server/roles/scripture_scraper/tasks/teardown.yml`),
while the role's deploy logic stays in the repo, unchanged, behind that
same var — see the role's README for the rollback story.

## Rollout status

- [x] Root cause confirmed (IP-specific block).
- [x] Fix decided (ADR-12).
- [x] `.github/workflows/scripture-scrape.yml` written.
- [x] `scripture_scraper_teardown` var + `tasks/teardown.yml` written.
- [ ] `ARCHIVE_PUSH_TOKEN`/`SCRIPTURE_INGEST_TOKEN` set as GitHub Actions
      repository secrets.
- [ ] Workflow smoke-tested via `workflow_dispatch` — MTGO step
      succeeds, archive commit lands on `Spigushe/mtg_decklist_cache`,
      sweep logs `0 failed`.
- [ ] VPS teardown applied (`ansible-playbook barrins_scripture.yml -e
      deploy_env=staging`) — only after the smoke test above passes.
- [ ] Status flipped to Resolved once the above are all checked and the
      new schedule has completed at least one unattended (non-manual)
      run.

## See also

- `apps/barrins_scripture/barrins_scripture/utils/selenium_driver.py`
- `apps/barrins_scripture/barrins_scripture/utils/mtgo.py`
- `.github/workflows/scripture-scrape.yml`
- `docs/content/ops/architecture/decisions.md` (ADR-12)
