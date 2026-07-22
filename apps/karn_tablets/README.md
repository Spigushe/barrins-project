# Karn Tablets: metagame/analytics calculation backend

Placeholder — periodic ML/analytics backend that reads tournament/decklist
data from `barrins_api` and writes computed results back into it (see the
Tolaria News platform doc's §3, "Backend-side detail: `karn_tablets`", for
the data-flow rationale). Not yet decided: app name/location (ML-01), auth
mechanism with `barrins_api` (ML-02), calculation schedule/trigger (ML-03),
write-back payload shape (ML-04), and the underlying tournament/decklist
data pipeline (ML-05).
