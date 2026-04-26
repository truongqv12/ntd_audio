# Optimization & roadmap

> **For AI agents:** this is the **forward-looking** doc. Anything here is **not yet implemented**. Do not document items below as if they exist. When working on one of these initiatives, move the relevant block into `feature-map.md` (with the file paths it landed in) and shrink the entry here.
>
> **For humans:** the prioritized list of post-Epic-4 work that turns `ntd_audio` from "self-hostable" into "comfortable to operate at scale." Each item lists the symptom, the proposed fix, where it touches, and how to verify when it lands.

## TL;DR

- Epic 1 → Epic 4 has shipped (operational safety, tooling, feature gaps, production readiness). The base is solid.
- The next phase is **wire-up & scale**: making the pieces Epic 4 introduced actually exercised, plus multi-user, plus deployability beyond Compose.
- The eight initiatives below are ordered by **impact on a self-hosting operator**, not by implementation effort.

## How this doc is organized

For each item:
1. **Why it matters** (concrete pain it removes).
2. **What changes** (files / components touched).
3. **Acceptance criteria** (what "done" looks like — the test that proves it shipped).
4. **Risk and migration notes** (what existing installs need to do).

## 1. Wire `ArtifactStorage` into `write_artifact`

**Why it matters.** Today, `STORAGE_BACKEND=s3` is a no-op for new artifacts: the `ArtifactStorage` Protocol exists in `services/storage.py`, but the real write path in `services_jobs.process_job` (and the existing `storage.py` helper it calls) writes to the local filesystem unconditionally. Operators who follow `self-hosting.md` and set the S3 env vars get a silently-broken setup.

**What changes.**

- Replace the direct `Path.write_bytes` / `cache_root` calls in `services_jobs.process_job` with `storage = get_storage(); storage.write_bytes(key, audio_bytes)`.
- Same for the `generation_cache` write path.
- Migrate the read path (`/v1/jobs/{id}/artifact`, library download) to read through the abstraction.
- Add an integration test that boots a localstack / minio container and round-trips an artifact through `S3ArtifactStorage`.
- Document the S3 vs local trade-offs explicitly in `self-hosting.md` (already covered structurally; needs a "what does this **not** do" callout when local is selected — e.g., zero-downtime migration between backends is out of scope).

**Acceptance criteria.**

- `STORAGE_BACKEND=s3` plus `S3_*` env vars makes new jobs write into the bucket; downloads stream from the bucket; nothing touches `ARTIFACT_ROOT`.
- `STORAGE_BACKEND=local` continues to work bit-for-bit identically.
- New integration test: `pytest backend/tests/test_storage_s3.py` runs against MinIO in CI.

**Risk and migration.** Existing `local` installs are unaffected (default unchanged). For installs migrating `local → s3`, there's no automatic copy; document `aws s3 sync $ARTIFACT_ROOT s3://$S3_BUCKET/$S3_PREFIX` in operations.md.

## 2. JWT / multi-user auth

**Why it matters.** The current API-key gate (`X-API-Key`) is fundamentally single-tenant: every key has the same authority over every project, every job, every setting. Self-host operators who want to share the deployment among teammates have no per-user audit, no revocation granularity, and no way to scope a key to a project.

**What changes.**

- Schema: `users (id, email, password_hash, created_at, disabled_at)`, `sessions (id, user_id, expires_at, ...)`, `api_tokens (id, user_id, name, hashed_token, scopes, last_used_at, expires_at)`. Optional in v1: workspace tier (`workspaces`, `workspace_members`).
- Auth surface: `/v1/auth/login` (email + password), `/v1/auth/logout`, `/v1/auth/sessions/me`, `/v1/auth/tokens` (CRUD). Session cookie (HttpOnly, SameSite=Strict) for the SPA; bearer token for programmatic access.
- Authz: every existing endpoint takes a `current_user` dependency. Existing `X-API-Key` keeps working (read as a token with implicit "owner" scope) so existing integrations don't break.
- Frontend: login page, session bootstrap, logout. Settings → "Tokens" tab to manage personal tokens.
- Password hashing: `argon2-cffi` (already a transitive dep of `passlib` if we use it; otherwise add direct).

**Acceptance criteria.**

- A user can register (or be seeded by an admin), log in, and operate the app entirely via session cookie.
- A user can mint named tokens with optional expiry and revoke them.
- An existing `APP_API_KEYS` setup keeps working, treated as legacy "superuser" tokens.
- New tests cover: failed login lockout policy, token revocation, scope enforcement on at least one endpoint.

**Risk and migration.** This is the largest item on the list. Schema migration is non-trivial and has to be reversible. Existing single-user installs default to "no auth required" if `APP_API_KEYS` is empty — the new auth must keep that ergonomic in dev (e.g., `APP_AUTH_MODE=open|api-key|jwt`).

## 3. Worker scaling primitives

**Why it matters.** Today, the worker is one Dramatiq actor on the `voiceforge` queue. Replicating it horizontally is doable (`docker compose up --scale worker=3`), but there is **no priority routing**, **no dead-letter queue**, **no per-project concurrency cap**, and **no graceful drain on deploy**. A long synthesis from one user will starve fast jobs from another. A failing provider will retry forever (Dramatiq default) without a DLQ to inspect.

**What changes.**

- Split into two queues: `voiceforge.fast` (cloud TTS, expected < 30s) and `voiceforge.slow` (OSS local engines, larger texts). Route by predicted duration based on `provider_key` and `len(text)`.
- Configure Dramatiq middleware: `Retries(max_retries=3, retry_when=...)`, `CurrentMessage`, `AsyncIO` if needed. Add a custom DLQ middleware that, on max retries, writes a row to `dead_letter_jobs` (table to add) and publishes `reason=dead_lettered`.
- Per-project concurrency cap via Redis-backed semaphore (`SETNX project:{key}:slots:{i}`). Max simultaneous jobs per project from `projects.settings.max_concurrent_jobs`.
- Graceful drain: SIGTERM handler that finishes in-flight tasks then exits; document the worker termination grace period (`stop_grace_period: 120s`) in compose.

**Acceptance criteria.**

- Two replicas of `worker` can run independently; load distributes; cancel/retry still work.
- Failed jobs that exhaust retries land in `dead_letter_jobs` and are visible in `/v1/jobs?status=dead_lettered`.
- Setting `projects.settings.max_concurrent_jobs=1` serializes that project's jobs even with multiple workers.
- Killing the worker with `docker compose stop worker` does not corrupt in-flight jobs (they finish or are reaped).

**Risk and migration.** Queue split is a Dramatiq config change; existing queued jobs might land in the wrong queue during the upgrade window. Mitigation: a one-shot script that re-routes pending jobs after the upgrade.

## 4. End-to-end browser tests (Playwright)

**Why it matters.** Vitest covers components in isolation; pytest covers handlers. Neither catches "I clicked New Job, picked a voice, hit submit, and the result isn't visible." E2E tests catch the integration glue (CORS, SSE reconnection, form ↔ API contract drift).

**What changes.**

- Add `frontend/e2e/` with Playwright. Three scenarios for v1:
  1. **Smoke:** open `/`, see Dashboard, see at least one project (the bootstrap default).
  2. **Create + complete a job:** create a job with a stub provider that returns a fixed audio file, wait via SSE for `succeeded`, download artifact.
  3. **Cancel a long job:** start with a slow provider, click Cancel, confirm `canceled` state propagates.
- A separate Compose profile `e2e` that boots a stub provider sidecar (`engines/stub-runtime/`), so tests don't depend on real cloud APIs.
- New CI job: `frontend-e2e` on PRs that touch `frontend/`, `backend/`, or `engines/`.

**Acceptance criteria.**

- `make e2e` builds the stack, runs Playwright, tears down. Runs locally and in CI.
- Failing E2E blocks PR merges on the relevant paths.
- Test artifacts (screenshots + video on failure) uploaded to the GitHub Actions run.

**Risk and migration.** New CI minutes. Mitigate by only running E2E on relevant paths and on `main`.

## 5. Provider plugin system

**Why it matters.** Adding a TTS engine today requires editing `backend/src/voiceforge/providers/__init__.py` to register it. That blocks two real use cases: (a) self-host operators who want to add their own internal model without forking, and (b) keeping the upstream provider list manageable as new engines emerge.

**What changes.**

- Define a stable provider Protocol in `backend/src/voiceforge/providers/protocol.py` (already partially formalized; turn it into a tagged ABC).
- Discover providers via Python entry points: `[project.entry-points."voiceforge.providers"]`. The built-in ones (voicevox, piper, kokoro, vieneu, openai, elevenlabs, google, azure) move to entries; the registry loads them at startup.
- Allow operator-side `pip install voiceforge-provider-foo` to add a provider with no code changes here.
- Schema for `provider parameter schemas` (already structured per-provider) becomes part of the entry-point return — registry reads schemas dynamically.

**Acceptance criteria.**

- All existing providers continue to work, registered via entry points.
- A small example plugin in a separate directory (`examples/voiceforge-provider-stub`) demonstrates the contract; it's installable with `pip install -e ./examples/...` and shows up in the catalog.
- The provider Protocol is documented in `docs/en/providers.md` with a "Build your own" section.

**Risk and migration.** Internal — no operator-facing breaking change.

## 6. Helm chart for Kubernetes

**Why it matters.** Compose is great for single-host self-host. Past that (multi-replica, autoscale, managed Postgres, managed Redis), operators move to Kubernetes. A first-class Helm chart keeps the project's deployment story coherent.

**What changes.**

- New `deploy/helm/ntd-audio/` chart. One Deployment per service (api, worker, frontend), one Job for `migrate`, optional sub-charts for Postgres / Redis (or BYO via values).
- Engine sidecars become optional `values.engines.{voicevox,piper,kokoro,vieneu}.enabled`.
- Secrets via `values.secrets` (operator can wire ExternalSecrets / Sealed Secrets / cloud KMS).
- Ingress template with TLS via cert-manager.
- Health/readiness probes from `/health` (already designed for it).
- A `helm test` hook that hits `/health` and `/metrics` against the deployed chart.

**Acceptance criteria.**

- `helm install ntd-audio deploy/helm/ntd-audio --set ...` produces a running app on a kind / k3d cluster.
- `helm test` passes.
- Chart published to a GitHub Pages-backed Helm repo on tag.
- Document on `self-hosting.md` (or a new `kubernetes.md`) with values examples.

**Risk and migration.** New deployment surface to maintain. Defer until the Compose path is fully stable (it is).

## 7. Anonymous opt-in telemetry

**Why it matters.** "Which engines are popular? How big are typical scripts? Which features do people actually use?" — these questions feed prioritization. Without telemetry, the project is flying blind. **Strict opt-in** is the only acceptable design — surveillance-by-default is incompatible with self-host.

**What changes.**

- New env var `TELEMETRY_ENABLED=false` (default). Operator must set it explicitly to `true`.
- A small daily ping from the API: `POST https://telemetry.<project domain>/v1/install` with:
  - Anonymous install ID (UUID generated on first run, persisted in `app_settings`).
  - Version, OS / arch.
  - Counts (not contents) of: jobs by provider (24h), active projects, distinct voices used.
  - **Never:** text content, voice samples, project names, user data.
- The exact payload schema is documented in `docs/en/operations.md` under a new "Telemetry" section. The schema is part of the public contract; changes require a CHANGELOG entry.
- `/v1/settings/telemetry/preview` returns the exact JSON that would be sent today, so operators can audit it.

**Acceptance criteria.**

- `TELEMETRY_ENABLED=false` (default) sends nothing — verified by network test.
- `TELEMETRY_ENABLED=true` sends the documented payload daily.
- Operator can preview and audit any payload before it's sent.
- Documentation makes the data minimization guarantee explicit and lists every field with rationale.

**Risk and migration.** None for existing installs (default off). Trust hinges on transparency.

## 8. Artifact garbage collection

**Why it matters.** Artifacts and `generation_cache` rows accumulate forever today. A heavy-usage install will eventually fill its disk or its S3 bucket. There's no lever to control retention beyond manual deletion.

**What changes.**

- New table `retention_policies` (or columns on `projects.settings.retention`): `keep_days_succeeded`, `keep_days_failed`, `keep_days_canceled`. Defaults: `keep_days_succeeded=null` (forever), `keep_days_failed=30`, `keep_days_canceled=14`.
- A nightly job (Dramatiq scheduled actor) that:
  - Selects jobs older than the policy.
  - For each: delete artifact via `ArtifactStorage.delete(key)`, delete `generation_cache` row, set `synthesis_jobs.archived_at`.
  - Counts metric: `voiceforge_artifacts_pruned_total{reason}`.
- Admin endpoint `POST /v1/admin/retention/run-now` to trigger manually (gated by superuser).
- Document the default policy and how to override per-project.

**Acceptance criteria.**

- A test that creates aged jobs (with `created_at` backdated) confirms they're pruned by the GC pass.
- Pruning respects the `ArtifactStorage` selected (works on S3 and local).
- Operators can disable GC entirely with `RETENTION_ENABLED=false`.

**Risk and migration.** This is destructive; a new env var defaults to off in v1 and on in v2 after operator feedback.

## Beyond v1 of this list

Not yet prioritized but on the radar:

- **i18n: more locales** (JP, ZH, KR). Frontend tooling already supports it; the work is translation.
- **Frontend test coverage** at the component level for ScriptEditor (drag-drop), Settings (provider creds), Library (paginated, filterable).
- **Voice cloning UX.** The capability exists for ElevenLabs, VieNeu — the UI doesn't yet cleanly support uploading reference audio, naming a clone, and routing jobs to it.
- **Project export / import.** Self-hosting users want a portable "project bundle" (script rows + voice mappings + completed artifacts) for backup, sharing, and migration.
- **WebSocket or SSE-over-HTTP/2 for events.** SSE works but doesn't multiplex; on slow networks you can run into connection-per-tab limits.

## How to propose a new initiative

1. Open a GitHub issue describing the symptom, not the solution.
2. If you're proposing a solution, fork this doc's structure (Why / What changes / Acceptance / Risk).
3. Link related issues.
4. PRs that pick up an item should move the entry from this doc into `feature-map.md` once it lands, with file paths.
