# Incident: mtgtop8 backfill OOM'd the VPS

_2026-08-09_

## What happened

A manual backfill run:

```bash
uv run scrape --source mtgtop8 --output-dir /home/spigushe/archives/barrins_scripture-staging --span 70000
```

crashed the whole server (Hetrix reported the host itself down, not just the
scraper process — consistent with an OOM-kill/swap-thrash event rather than
an unhandled Python exception).

## Root cause

`scrape_mtgtop8()` in
`apps/barrins_scripture/barrins_scripture/services/mtgtop8.py` ran producers
and consumers as two fully sequential phases instead of a pipeline:

1. Every producer batch (10 threads at a time) ran to completion first. Each
   producer that found a scrapable, unscraped tournament id pushed the full
   parsed `BeautifulSoup` DOM tree — not just the URL or raw HTML — onto an
   **unbounded** `Queue`.
2. Only after all `span // 10` batches had finished did consumer threads
   start draining that queue.

A parsed `BeautifulSoup` tree carries far more memory overhead than the
source HTML (every tag/string is a Python object with parent/sibling/
navigable-string links). With `--span 70000`, a large fraction of those ids
were new/unscraped, so tens of thousands of full DOM trees accumulated in
memory simultaneously before a single consumer had a chance to drain one.

The consumer's exit condition was also why producers had to finish first:
`consumer()` broke out of its loop the instant it observed `queue.empty()`,
with no way to distinguish "nothing left, ever" from "nothing queued yet."
Starting consumers concurrently with producers under the old logic would
have raced them into exiting immediately.

## Fix

Same file, no behavior change to what gets scraped or how retries work —
only the concurrency model:

- **Bounded queue**: `Queue(maxsize=num_threads * 10)` instead of unbounded.
  Producers now block (backpressure) once the queue is full instead of
  piling up unbounded parsed trees.
- **Real pipelining**: consumer threads start *before* the producer batches
  run, so the queue drains continuously instead of the whole span's worth of
  candidates sitting in memory until the last batch finishes.
- **Completion signal**: a `producers_done` `threading.Event` replaces the
  `queue.empty() → break` check. Consumers poll `queue.get(timeout=...)` and
  only exit once producers have finished *and* the queue is empty.
- **Retry re-`put()` moved outside the `retries`-dict lock** — with a bounded
  queue, blocking on a full queue while holding that lock could otherwise
  stall every other consumer thread's retry accounting too.

## Verification

- `apps/barrins_scripture/tests/test_services_mtgtop8.py` updated for the
  new `producer()`/`consumer()` signatures, plus two new tests: one asserting
  the queue is actually bounded, one asserting a consumer does not exit while
  the queue is momentarily empty but producers are still running (the
  pipelining fix itself).
- Full suite: 152 passed, 95.69% coverage (≥ 90% required).
- `ruff format --check`, `ruff check`, `ty check`: all clean.

## What this does not change

- Retry semantics (same soup reused, same `max_retries` default of 3).
- What counts as scrapable (`we_should_scrape_it`, format filtering).
- The CLI (`--span`, `--id-from`, `--output-dir` flags unchanged).

## Residual recommendation

The fix removes the unbounded-memory failure mode, but a very large
`--span` on a small VPS still means a long-running job. Prefer the default
`num_threads=4` rather than increasing it, since memory now scales with
`num_threads * 10` in-flight documents rather than with `span` itself. This
fix needs to be released and deployed (per this repo's release-based
deployment policy) before it's live on staging/production — it currently
only exists on `feat/barrins-scripture`.
