# Performance & Self-Host Notes

## Bottlenecks found in the previous build

### 1. SSE pushed full snapshots on every interval
The old `/events/stream` implementation pushed the entire snapshot every cycle, even when nothing changed.

**Why this hurts**
- extra network traffic
- repeated JSON serialization
- unnecessary frontend reconciliation
- more database work than needed

**What changed**
- introduced a lightweight `build_live_signature()`
- SSE now emits a full `snapshot` only when jobs/events/projects changed
- otherwise it emits a lightweight `heartbeat`

---

### 2. Project stats had an N+1 style cost
The old project stats flow loaded jobs per project and counted them in Python.

**Why this hurts**
- expensive on self-host installs with many jobs
- bad fit for SSE/live views
- scales poorly when projects increase

**What changed**
- moved project stats to grouped SQL aggregates
- `list_projects()` now reuses a stats map instead of recomputing per project

---

### 3. Voice search was frontend-only
The old voice picker filtered the entire voice catalog in the browser.

**Why this hurts**
- large catalogs become slow
- multiple engines/locales make UI harder to reason about
- frontend and backend capabilities drift apart

**What changed**
- added backend route: `GET /catalog/voices/search`
- voice picker now uses deferred input + backend search
- fallback local filtering is kept as a resilience path

---

### 4. Health checks were too shallow for self-host operations
Basic provider status was not enough to run this as a real self-host tool.

**What changed**
- added `GET /monitor/status`
- provider diagnostics now include:
  - reachability
  - latency
  - active jobs
  - visible voice count
  - target URL when available
- added `GET /monitor/logs`
- added in-app monitor page with log tail viewer

---

### 5. Logging was not clear enough
Basic stdout logs were not enough for a self-host admin/operator.

**What changed**
- request logging middleware with request id + latency
- rotating file logs
- job lifecycle logs (`created`, `started`, `cache_hit`, `completed`, `failed`)
- log tail endpoint and UI viewer

---

## Frontend / backend gaps that were closed

### Closed
- voice search now exists in backend, not only frontend
- monitor/log endpoints now exist for self-host diagnostics
- SSE traffic is reduced when nothing changed
- project stats are no longer recomputed inefficiently per project

### Still open
- provider-specific advanced params are still intentionally selective, not exhaustive
- monitor logs currently show API/worker logs, not direct Docker runtime logs from every engine container
- queue uses Dramatiq + Redis, but no dead-letter or retry policy UI yet
- artifact storage is still local filesystem only

---

## Direction for later public/shared deployment

When moving from private self-host to shared/public usage, the next architecture step should be:

1. split control-plane API from worker/engine nodes
2. isolate engines in separate containers/pools
3. add per-project and per-user quotas
4. add storage abstraction (S3/MinIO)
5. add queue retry policy + dead-letter handling
6. add auth / workspace boundaries
7. add metrics export (Prometheus-style) and alerting

The current build is still optimized for **self-host first**, but the new monitor/search/logging structure is meant to reduce migration cost later.


## New bottlenecks / gaps addressed

### Engine logs in Monitor UI
- Before: app could only read API/worker file logs.
- Now: monitor can also tail Docker Compose engine containers through `/var/run/docker.sock`.
- Sources exposed in-app: `api`, `worker`, `voicevox`, `piper`, `kokoro`, `vieneu`.

### Voice preview strategy
- The catalog now falls back to an internal preview URL when the engine/provider does not ship a sample URL.
- This keeps the UI consistent across engines: the picker can always attempt playback from the same place.
- For self-host engines, preview is generated on demand and should be treated as an operational convenience, not a zero-cost action.

### Project line-based workflow
- Added `project_script_rows` as a first-class model.
- Each row can hold its own text, optional provider/voice overrides, params, enable flag, and join-to-master flag.
- Batch queue and merge endpoints exist so a project can move from single prompt generation to row-by-row scripting.
