# Incident: mtgtop8.com explain_deck 500s silently stopped all archiving

## Status tracking

| Field | Value |
| --- | --- |
| Status | Fixed — `get_notes()` no longer aborts the deck/tournament on this endpoint failing; verified via manual `workflow_dispatch` |
| Severity | High but silent — zero MTGTop8 tournaments archived for ~17 days, no error surfaced anywhere (CI stayed green, VPS timers stayed "successful") |
| Reported | 2026-09-18 (user noticed `Spigushe/mtg_decklist_cache` had no recent MTGTop8 commits) |
| Introduced | ~2026-09-01/02 (mtgtop8.com side change; last archived MTGTop8 commit before this gap is `015e69069`, 2026-09-01T00:07:58Z) |
| Resolved | 2026-09-18 |
| Area | Barrin's Scripture — MTGTop8 parser (`parsers/mtgtop8.py::get_notes`) |
| Blocking | Any MTGTop8 scrape (scheduled or manual), on every environment that ran it |
| Owner | Backend/Barrin's Scripture (Agent 1) |

## Summary

`Spigushe/mtg_decklist_cache` had committed `mtgo.com/` files every night
but no `mtgtop8.com/` files since 2026-09-01, on both
`.github/workflows/scripture-scrape.yml` and the (at the time still-live)
VPS `barrins_scripture` timer. Nothing was reporting failure: the GitHub
Actions job and the VPS's `journalctl` logs both showed green/successful
runs every night.

## Root cause

mtgtop8.com's "explain this deck" feature
(`https://mtgtop8.com/event?e=1&d=<id>&explain_deck=Y` — an AI-generated
notes blurb, see the `_AI_DISCLAIMER` constant in `parsers/mtgtop8.py`)
started returning `500 Internal Server Error` for **every** deck ID,
site-wide — not specific to any one tournament or deck.

`get_notes()` called `response.raise_for_status()` unconditionally on
that request, and was itself called unconditionally by
`get_deck_from_top8()`/`get_deck_out_top8()` for every deck. The
resulting `HTTPError` propagated up through `decks()` into
`services/mtgtop8.py`'s `consumer()`, where it was caught by a broad
`except Exception: logger.exception(...); queue.task_done()` — the
tournament was silently dropped (no file written, no retry, no non-zero
exit). Since this hit literally every deck, every tournament failed this
way, so `mtgtop8.com/` never had anything new for either the GitHub
Actions checkout or the VPS's local clone to commit — there was nothing
missing to "push," there was nothing being produced at all.

## Why this stayed invisible

- `consumer()`'s per-tournament exception handling is intentionally
  non-fatal (a single bad tournament shouldn't kill the whole scrape run)
  — but that also means a *systemic* failure hitting 100% of tournaments
  looks identical to a series of unrelated one-off failures, and the CLI
  process itself always exits 0.
- The workflow's "Commit and push archive changes" step only commits
  `if [ -n "$(git status --porcelain)" ]` — with zero new files, that's
  correctly a no-op, not a failure.
- Nightly runs (GitHub Actions and, independently, the VPS's own sweep —
  see the related VPS-duplication note below) both looked "successful"
  throughout, because MTGO scraping was completely unaffected and kept
  producing real commits every night, masking that MTGTop8 had gone
  silent alongside it in the same job/log stream.

## Fix

`get_notes()` now catches `requests.exceptions.RequestException` around
the `explain_deck=Y` request and returns `""` instead of raising — notes
are a cosmetic extra (see `_AI_DISCLAIMER`), not core deck data
(mainboard/sideboard), so a failure fetching them must not abort the
whole deck or tournament.

```python
try:
    response = requests.get(deck_url, headers=HEADERS, timeout=10)
    response.raise_for_status()
except requests.exceptions.RequestException:
    return ""
```

Follow-up (circuit breaker): after `NOTES_FAILURE_LIMIT` (5) consecutive
`explain_deck` failures in one run, `get_notes()` skips the endpoint for
the rest of the run instead of spending one doomed request per deck; a
success resets the count, and `scrape_mtgtop8` resets it at the start of
each run. This removes the per-deck notes request while the site is
broken and self-heals when it recovers. Notes fetched later (enrichment
pass) remain possible: `""` marks "fetch failed", `None` marks "no notes
on the page".

Landed via PR #156 (`fix(scripture): don't abort mtgtop8 deck scrape when
explain_deck=Y 500s`), merged to `staging` as merge commit `d4f4cec3`.
Covered by `TestGetNotes` in `tests/test_parsers.py` (both the
500-error path and the normal-parse path).

## Verification

A manual `workflow_dispatch` run of `scripture-scrape.yml` against
`staging` (run
[35392159651](https://github.com/Spigushe/barrins-project/actions/runs/35392159651))
was triggered after the fix merged. Result: all steps green, and archive
commit `e1a00758f` (2026-09-18T21:17Z) landed on
`Spigushe/mtg_decklist_cache` with MTGTop8 files again (300+ files, the
GitHub API's listing cap; ~270 of them under `mtgtop8.com/`, mostly
2026/08 and 2026/09). The sweep then reported `37 succeeded, 0 failed,
319 filtered (format not in ['Duel Commander'])`.

The run took about 43 minutes, versus the 10-15 minutes of the preceding
nightly runs. That is expected for this run only: it was the first in
which tournaments actually completed (previously each one died on its
first deck), so it worked through ~17 days of backlog, and the scraper
archives every format even though the sweep only ingests Duel Commander
(319 of the files above were filtered out at ingest). Nightly runs should
return to roughly the old duration plus one day of decks.

## Related finding: the VPS still ran a duplicate scraper

While auditing why nothing was being pushed, a second, independent issue
surfaced: `barrins_scripture.timer`/`.service` and
`barrins_scripture_sweep.timer`/`.service` were still `enabled` and
actively running on the production VPS, even though
`ops/my-server/barrins_scripture.yml` has set
`scripture_scraper_teardown: true` since ADR-12 (2026-08-10) specifically
to decommission this path in favor of GitHub Actions. The teardown code
existed and worked; it had simply never been executed against the live
host — the declared Ansible config and the host's actual running state
had drifted apart.

This was masked by the same explain_deck=Y bug (both the VPS and GitHub
Actions were independently producing zero MTGTop8 output, so there was
nothing for the two to race over), but it had already caused one manual
merge commit in the archive's history on 2026-08-23 before that
coincidence held, and would have started conflicting again the moment
MTGTop8 archiving resumed — the VPS's local archive clone is never
`git pull`ed between ticks, so a push racing against GitHub Actions'
always-fresh checkout is a real non-fast-forward risk once both sides are
producing files again.

Resolved 2026-09-18 by actually running
`ansible-playbook barrins_scripture.yml -e deploy_env=production`
(teardown path) — confirmed via direct inspection of the host: no
`barrins_scripture*` systemd units, wrapper scripts, archive clone, or
app checkout remain. The final sweep tick (08:15 UTC, before teardown)
had already pushed everything current, so no data was lost. See
`docs/content/service/barrins_scripture/incidents/2026-08-10-mtgo-network-block.md`'s
rollout checklist, now fully checked off.

## Impact

MTGTop8 tournaments played roughly 2026-09-01 through 2026-09-18 are
missing from `Spigushe/mtg_decklist_cache`. Backfilling this gap is not
yet done — same open item as the role's README's "Not automated yet"
section (`--id-from`/`--span` backfill), just a smaller, bounded window
this time. Track separately; not blocking this incident's resolution.

## See also

- `apps/barrins_scripture/barrins_scripture/parsers/mtgtop8.py`
- `apps/barrins_scripture/barrins_scripture/services/mtgtop8.py`
- `apps/barrins_scripture/tests/test_parsers.py::TestGetNotes`
- `docs/content/service/barrins_scripture/incidents/2026-08-10-mtgo-network-block.md`
- `docs/content/ops/architecture/decisions.md` (ADR-12)
- `ops/my-server/roles/scripture_scraper/README.md`
