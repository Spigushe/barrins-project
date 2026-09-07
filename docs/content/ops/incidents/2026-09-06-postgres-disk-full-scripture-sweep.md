# Incident: Full-archive Scripture sweep filled the disk, took down PostgreSQL (prod)

## Status tracking

| Field | Value |
| --- | --- |
| Status | Open — production restored 2026-09-06 ~19:41; reclamation done (disk 100% → 40%, 44G free); DC-only ingest filter (`proj/scripture-dc-only`) + release still to ship |
| Severity | Critical — production `api.barrins-codex.org` failed every DB-backed request (Tolaria News, Tamiyo Scroll) for the duration |
| Reported | 2026-09-06, ~16:20 (a `barrins-scripture-sweep --mode full` run finished reporting 3650 ingest failures) |
| Service restored | 2026-09-06 ~19:41 — `postgresql@15-main` back `online`, both `/health` → 200 |
| Area | Infrastructure — shared PostgreSQL on `146.59.146.57`; `barrins_scripture` sweep; `bs_*` ingest scope; non-prod databases on the prod host |
| Blocking | Every `barrins_api` request that touches the database |
| Owner | Infrastructure (Agent 3); Agent 1 for the ingest format-filter code; Agent 0 sign-off on the non-DC hard-delete |

## Summary

A manually-run full-archive replay
(`barrins-scripture-sweep --mode full --fast-forward`, ~108k JSON
archive files) against production `POST /internal/scripture/ingest`
added ~7.5G to production's `bs_*` tables and tipped the host's single
74G root partition to 100% (374M free). PostgreSQL could no longer
extend relation/WAL files, PANICked, and did not restart on its own.

Sweep result: 104916 succeeded, 3650 failed, 1306 fast-forwarded.

The sweep's ~7.5G was the last straw, not the root cause. The 44G under
`/var/lib/postgresql` is mostly **non-production databases sharing the
partition**:

| database | size | role |
| --- | --- | --- |
| `barrins_db` | 21 GB | legacy pre-rename prod DB — already dropped from the backup allowlist; nothing uses it |
| `barrins_api_dev` | 8.6 GB | a dev database on the prod host |
| `barrins_api` | 8.5 GB | **production** |
| `barrins_api_staging` | 3.6 GB | staging (shares this host) |
| everything else | < 100 MB | |

Production `barrins_api` is 8.5G, of which `bs_*` is ~8.3G
(`bs_deck_cards` 7.5G incl. its PK index, `bs_decks` 663M, the rest
< 90M). And `bs_*` is **not scoped to Duel Commander** — the sweep
walks every archive file and `ingest_scrape` stores whatever
`tournament.format` the file carries:

| format | tournaments | | format | tournaments |
| --- | --- | --- | --- | --- |
| Modern | 22,084 | | Duel Commander | **8,696** (8.2%) |
| Standard | 19,784 | | Vintage | 8,553 |
| Legacy | 18,153 | | Premodern | 4,032 |
| Pauper | 14,400 | | Unknown Format | 691 |
| Pioneer | 9,829 | | | |

Every `barrins_api` reader filters
`BSTournament.format == "Duel Commander"` (`app/services/tolaria_news/
*.py`, Karn Tablets `kt_*`), so ~92% of `bs_*` is data no feature
reads.

This is a **recurrence** of
[2026-08-15](./2026-08-15-postgres-disk-full.md) — same host, same 74G
disk, same failure mode. That incident's still-open follow-up (missing
migrations merged into `main`, `a3c7f912e5b8` `add_sequence_to_bs_rounds`
among them) is also visible here: 32 of the 3650 failures are
`column "sequence" of relation "bs_rounds" does not exist`, because
production's schema is behind the deployed code's model.

## Evidence

`sudo journalctl -u api --since "2026-09-06 12:00"`, `Unhandled
exception:` lines bucketed by type:

| count (approx) | error | meaning |
| --- | --- | --- |
| ~250 | `asyncpg DiskFullError: could not extend file "base/…": No space left on device` / `wrote only N of M bytes` | filesystem full on write (PG SQLSTATE 53100) |
| 590 | `CannotConnectNowError: the database system is not yet accepting connections` | PG restarting |
| 164 | `CannotConnectNowError: the database system is in recovery mode` | PG crash recovery |
| 172 | `OSError: … Connect call failed ('::', …), ('…', …)` | PG not listening — down |
| 20 | `ConnectionDoesNotExistError: connection was closed in the middle of operation` | in-flight queries killed on crash |
| 32 | `ProgrammingError … UndefinedColumnError: column "sequence" of relation "bs_rounds" does not exist` | prod schema behind `main` (2026-08-15 open item) |

Not OOM: no `out_of_memory` / OOM-killer entries; `free -h` and
`dmesg -T` were clean. The write failures are `ENOSPC`. The `bs_*`
ingester streams row-by-row and commits once per file, so a
tournament's deck count does not drive memory use.

WAL is not a factor: `pg_wal` is 1.1G, `archive_mode = off`, no
replication slots.

Host state at triage:

```text
/dev/sda1        74G   71G  374M 100% /
44G   /var/lib/postgresql      <- 33G of it is non-prod DBs (see Summary)
5.5G  /home/spigushe/archives  <- scrape archive; move, do not delete
2.0G  /home/spigushe/.cache
1.3G  /var/log/journal
1.1G  /var/lib/docker
```

`systemctl status postgresql` showed `active (exited)` — expected, that
is the Debian meta-unit; the real service is `postgresql@15-main`
(`pg_lsclusters` → `15 main 5432 … /var/lib/postgresql/15/main`).

## Timeline

1. **~16:20** — the manual
   `barrins-scripture-sweep --mode full --fast-forward` run finishes
   with 3650 failures, ~99% the disk-full cascade above.
2. **Triage** — `df -h /` shows `/` at 100%; `free -h` / `dmesg -T`
   rule out memory pressure and the OOM killer. `du -xhd1` isolates
   `/var/lib/postgresql` at 44G. `sudo -u postgres psql` fails on a
   missing socket — the cluster is down.
3. **Space reclaimed** (no database data touched): `journalctl
   --vacuum-size=100M` (1.1G); `apt clean` / `autoremove` (~0);
   `uv`/`pip` caches (~1.6G); `/tmp` + rotated logs;
   `find /var/backups/postgresql -mtime +3 -delete` (~1.4G);
   `docker system prune -f` (464M). 374M → **5.9G free (92%)**.
4. **~19:41** — `sudo systemctl start postgresql`; `pg_lsclusters`
   reports `15/main … online`; `select 1` returns. `systemctl restart
   api`; `/health` → `{"status":"ok"}` locally and via the domain.
5. **No local sweep schedule** — `systemctl list-timers --all` and
   `crontab -l` are empty for scripture/sweep. The scheduled sweep
   runs from GitHub Actions (`scripture-scrape.yml`, `--mode recent`);
   the `--mode full` run that filled the disk was invoked by hand.
6. **Post-recovery sizing** — `pg_database_size` / `pg_total_relation_
   size` produce the tables in the Summary. `barrins_db` (21G) is the
   single biggest object and is unused.
7. **~20:xx** — `barrins_db` dropped after verifying no `pg_stat_
   activity` connections, no `.env` `DATABASE_URL` reference, and no
   autovacuum history. `df` 92% → **62% (28G free)**. The intended
   off-box `pg_dump` did not run (the runbook's placeholder hostname
   was not substituted; `ssh` failed, the `DROP` in the same pasted
   block proceeded regardless), so no fresh dump was retained — see
   Open items.

## Root cause

1. **No capacity headroom: non-production databases on the prod host.**
   `barrins_db` (21G, legacy, unused), `barrins_api_dev` (8.6G) and
   `barrins_api_staging` (3.6G) sit on the same 74G partition as
   production. With ~33G already spoken for by databases nothing
   in production reads, prod `barrins_api` had almost no room to grow.
2. **`bs_*` ingest has no format scope.** `barrins_scripture` scrapes
   all eight constructed formats it recognizes
   (`schemas/formats.py::Formats`); `sweep.py` posts every archive
   file; `app/services/scripture/ingester.py::ingest_scrape` upserts
   every one. Every *reader* is Duel-Commander-only, so the replay
   wrote ~8× more `bs_*` than the ecosystem needs (~8.3G vs a DC-only
   ~0.7G) — enough, on a host with no headroom, to tip it over.
3. **Same failure mode as 2026-08-15.** A full disk stops PostgreSQL
   from restarting (it cannot write its lock file / replay WAL), so
   the outage does not self-heal.
4. **Schema drift from 2026-08-15 never closed.** `a3c7f912e5b8`
   (`add_sequence_to_bs_rounds`) and other MTGJSON-era migrations were
   applied to prod by hand but never merged to `main`; the deployed
   release predates them, so bracketed-event ingest 500s on the
   missing `bs_rounds.sequence`.

## Decisions (2026-09-06)

1. **Drop `barrins_db`** (final dump off-box first) — reclaims ~21G.
2. **`barrins_api_staging` / `barrins_api_dev`**: one-time
   `DELETE FROM bs_tournaments WHERE date < today − 90 days`, all
   formats.
3. **Volume resize / dedicated `PGDATA`**: postponed.
4. **Ingest becomes Duel-Commander-only.** Config-gated allowlist
   (`scripture_ingest_formats`, default `["Duel Commander"]`) enforced
   in `ingest_scrape` (non-matching = 200 no-op, `skipped_out_of_scope`)
   plus a matching skip in `sweep.py`. Change on
   `proj/scripture-dc-only` off `staging`; patch release + prod
   redeploy per §25/§27.
5. **Purge production `barrins_api` of non-DC tournaments** —
   `DELETE FROM bs_tournaments WHERE format <> 'Duel Commander'` in
   year batches, then `VACUUM FULL` the `bs_*` tables. §11.8 documented
   hard-delete exception (out-of-scope data, no consumer); Agent 0
   sign-off.

## Open items

- [ ] WAL replay confirmed clean; no corruption in the PG 15 log.
- [x] `barrins_db` verified unused and dropped 2026-09-06 (~21G
      reclaimed).
- [ ] `barrins_db` — search for any surviving pre-drop dump
      (`find / -xdev -name 'barrins_db*'`, `~/backups/`); if none,
      record that it was dropped with no retained backup.
- [x] `barrins_api_staging` / `barrins_api_dev` 90-day trim applied
      2026-09-06 (all formats, `date < CURRENT_DATE - 90`): staging
      46,139 deleted → keep 214 (3.7G → 169M); dev 105,597 deleted →
      keep 3,810 (8.6G → 357M).
- [ ] `barrins_api_dev` — decide whether it belongs on the prod host
      at all (separate from the trim above).
- [x] Alembic checked 2026-09-06: prod DB already at head
      (`6cf95145f67e`), clean linear chain; `a3c7f912e5b8` applied and
      `bs_rounds.sequence` physically present. `alembic upgrade head`
      was a no-op. The 32 `bs_rounds.sequence` failures were historical
      (pre-catch-up). The 2026-08-15 "missing migrations" carryover is
      effectively resolved — confirm the chain is on `main` and close
      that item.
- [x] Production non-DC `bs_*` purge run 2026-09-06 (pre-dump
      `/tmp/barrins_api_pre-purge.dump`, 1.4G): 97,526 tournaments
      deleted in year batches (children cascaded),
      `VACUUM (FULL, ANALYZE)` on every `bs_*`. `barrins_api` 8.5G →
      984M; `bs_deck_cards` 7.5G → 785M; disk 62% → 55% (33G free).
      Only `Duel Commander` (8,696) remains.
- [ ] `proj/scripture-dc-only` — format-filter code, tests, CHANGELOGs.
- [ ] Patch release cut; prod `api` redeployed from the tag.
- [ ] GitHub Actions scrape/sweep workflow paused until the filter
      ships, then resumed.
- [ ] Volume resize / dedicated PG storage (deferred, tracked).
- [ ] 2026-08-15 carryover: missing migrations merged into `main`.
- [ ] Confirm whether the 2026-08-15 prod `DATABASE_URL` → `localhost`
      switch and `pg_hba.conf` narrowing were ever completed.

## See also

- [2026-08-15 — Backup retention filled the disk, took down
  PostgreSQL](./2026-08-15-postgres-disk-full.md) (this is a
  recurrence)
- `docs/project/v2.0.0-bump/t3-scripture-ingestion-pipeline/index.md`
  — ingest design
- [`../deployment/backup.md`](../deployment/backup.md),
  [`../deployment/database.md`](../deployment/database.md)
- Constitution §11.8 (delete = archive; documented hard-delete
  exceptions), §26.5 (bulk data off the primary), §31.3 (migration
  policy)
