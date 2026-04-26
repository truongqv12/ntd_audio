# Tối ưu & roadmap

> **Cho AI agents:** đây là tài liệu **hướng tương lai**. Mọi mục bên dưới **chưa được implement**. Không document chúng như đang tồn tại. Khi làm một mục, di chuyển khối tương ứng vào `feature-map.md` (kèm đường dẫn file đã land) và rút gọn entry tại đây.
>
> **Cho con người:** danh sách công việc post-Epic-4 đã sắp xếp theo độ ưu tiên — đưa `ntd_audio` từ "self-host được" lên "vận hành thoải mái ở quy mô lớn." Mỗi mục liệt kê triệu chứng, đề xuất, file ảnh hưởng, và cách verify khi land.

## TL;DR

- Epic 1 → Epic 4 đã ship (operational safety, tooling, feature gaps, production readiness). Nền móng vững.
- Phase tiếp theo là **wire-up & scale**: làm cho các mảnh Epic 4 đã đặt nền thực sự được sử dụng, plus multi-user, plus deploy ngoài Compose.
- Tám sáng kiến dưới đây sắp xếp theo **mức tác động lên người vận hành self-host**, không theo độ khó implement.

## Cách tổ chức tài liệu này

Mỗi mục:
1. **Vì sao quan trọng** (pain cụ thể được loại bỏ).
2. **Thay đổi gì** (file / component bị ảnh hưởng).
3. **Acceptance criteria** ("xong" trông như thế nào — test chứng minh đã ship).
4. **Rủi ro và migration** (install hiện hữu cần làm gì).

## 1. Wire `ArtifactStorage` vào `write_artifact`

**Vì sao quan trọng.** Hôm nay, `STORAGE_BACKEND=s3` là no-op cho artifact mới: Protocol `ArtifactStorage` tồn tại trong `services/storage.py`, nhưng đường ghi thực tế trong `services_jobs.process_job` (và helper `storage.py` cũ mà nó gọi) ghi local filesystem vô điều kiện. Operator làm theo `self-hosting.md` set S3 env vars sẽ nhận setup hỏng âm thầm.

**Thay đổi gì.**

- Thay các call `Path.write_bytes` / `cache_root` trực tiếp trong `services_jobs.process_job` bằng `storage = get_storage(); storage.write_bytes(key, audio_bytes)`.
- Tương tự cho đường ghi `generation_cache`.
- Migrate đường đọc (`/v1/jobs/{id}/artifact`, library download) đọc qua abstraction.
- Thêm integration test boot localstack / minio container và round-trip artifact qua `S3ArtifactStorage`.
- Document trade-off S3 vs local rõ ràng trong `self-hosting.md` (đã cover về cấu trúc; cần callout "cái này **không** làm gì" khi local được chọn — ví dụ migration zero-downtime giữa các backend nằm ngoài phạm vi).

**Acceptance criteria.**

- `STORAGE_BACKEND=s3` cộng `S3_*` env vars khiến job mới ghi vào bucket; download stream từ bucket; không gì chạm `ARTIFACT_ROOT`.
- `STORAGE_BACKEND=local` tiếp tục hoạt động bit-for-bit như cũ.
- Integration test mới: `pytest backend/tests/test_storage_s3.py` chạy với MinIO trong CI.

**Rủi ro và migration.** Install `local` hiện hữu không bị ảnh hưởng (default không đổi). Cho install migrate `local → s3`, không có copy tự động; document `aws s3 sync $ARTIFACT_ROOT s3://$S3_BUCKET/$S3_PREFIX` trong `operations.md`.

## 2. JWT / multi-user auth

**Vì sao quan trọng.** API-key gate hiện tại (`X-API-Key`) về bản chất là single-tenant: mọi key có cùng quyền lực trên mọi project, mọi job, mọi setting. Operator self-host muốn share deployment với đồng đội không có per-user audit, không có revocation granular, không có cách scope key vào project.

**Thay đổi gì.**

- Schema: `users (id, email, password_hash, created_at, disabled_at)`, `sessions (id, user_id, expires_at, ...)`, `api_tokens (id, user_id, name, hashed_token, scopes, last_used_at, expires_at)`. Optional ở v1: tier workspace (`workspaces`, `workspace_members`).
- Surface auth: `/v1/auth/login` (email + password), `/v1/auth/logout`, `/v1/auth/sessions/me`, `/v1/auth/tokens` (CRUD). Session cookie (HttpOnly, SameSite=Strict) cho SPA; bearer token cho truy cập programmatic.
- Authz: mọi endpoint hiện hữu nhận dependency `current_user`. `X-API-Key` cũ tiếp tục hoạt động (đọc như token với scope "owner" implicit) để không phá integration cũ.
- Frontend: trang login, session bootstrap, logout. Settings → tab "Tokens" để quản lý token cá nhân.
- Hash password: `argon2-cffi` (đã là transitive dep của `passlib` nếu dùng; nếu không thì add direct).

**Acceptance criteria.**

- Một user có thể đăng ký (hoặc admin seed), login, và vận hành app hoàn toàn qua session cookie.
- Một user có thể tạo named token với expiry tùy chọn và revoke.
- Setup `APP_API_KEYS` hiện hữu vẫn chạy, được xử lý như legacy "superuser" token.
- Test mới cover: chính sách lockout login fail, revocation token, enforce scope trên ít nhất một endpoint.

**Rủi ro và migration.** Đây là mục lớn nhất danh sách. Migration schema không tầm thường và phải reversible. Install single-user hiện hữu default về "không yêu cầu auth" nếu `APP_API_KEYS` rỗng — auth mới phải giữ ergonomic đó trong dev (vd: `APP_AUTH_MODE=open|api-key|jwt`).

## 3. Worker scaling primitives

**Vì sao quan trọng.** Hôm nay, worker là một Dramatiq actor trên queue `voiceforge`. Replicate ngang được (`docker compose up --scale worker=3`), nhưng **không có priority routing**, **không có dead-letter queue**, **không có per-project concurrency cap**, và **không có graceful drain khi deploy**. Một synthesis dài của user này sẽ starve job nhanh của user khác. Một provider lỗi sẽ retry mãi mãi (Dramatiq default) mà không có DLQ để inspect.

**Thay đổi gì.**

- Tách thành hai queue: `voiceforge.fast` (cloud TTS, expected < 30s) và `voiceforge.slow` (engine OSS local, text lớn hơn). Route theo duration dự đoán dựa trên `provider_key` và `len(text)`.
- Cấu hình Dramatiq middleware: `Retries(max_retries=3, retry_when=...)`, `CurrentMessage`, `AsyncIO` nếu cần. Thêm DLQ middleware tùy chỉnh: khi exhaust retry, ghi row vào `dead_letter_jobs` (table cần thêm) và publish `reason=dead_lettered`.
- Per-project concurrency cap qua semaphore Redis-backed (`SETNX project:{key}:slots:{i}`). Số job đồng thời tối đa per project lấy từ `projects.settings.max_concurrent_jobs`.
- Graceful drain: handler SIGTERM finish task in-flight rồi exit; document termination grace period của worker (`stop_grace_period: 120s`) trong compose.

**Acceptance criteria.**

- Hai replica của `worker` chạy độc lập; load phân phối; cancel/retry vẫn hoạt động.
- Job fail exhaust retry land trong `dead_letter_jobs` và visible ở `/v1/jobs?status=dead_lettered`.
- Set `projects.settings.max_concurrent_jobs=1` serialize job project đó kể cả khi nhiều worker.
- Kill worker với `docker compose stop worker` không corrupt job in-flight (chúng finish hoặc bị reaper xử lý).

**Rủi ro và migration.** Tách queue là thay đổi config Dramatiq; job đang queued có thể land sai queue trong cửa sổ upgrade. Mitigation: script one-shot re-route pending job sau upgrade.

## 4. End-to-end browser tests (Playwright)

**Vì sao quan trọng.** Vitest cover component cô lập; pytest cover handler. Không cái nào bắt được "tôi click New Job, chọn voice, submit, kết quả không hiện." E2E test bắt integration glue (CORS, SSE reconnection, drift contract form ↔ API).

**Thay đổi gì.**

- Thêm `frontend/e2e/` với Playwright. Ba scenario cho v1:
  1. **Smoke:** mở `/`, thấy Dashboard, thấy ít nhất một project (default bootstrap).
  2. **Tạo + complete một job:** tạo job với stub provider trả file audio cố định, đợi qua SSE đến `succeeded`, download artifact.
  3. **Hủy một job dài:** start với provider chậm, click Cancel, xác nhận state `canceled` propagate.
- Compose profile `e2e` riêng boot stub provider sidecar (`engines/stub-runtime/`), để test không phụ thuộc cloud API thật.
- CI job mới: `frontend-e2e` trên PR chạm `frontend/`, `backend/`, hoặc `engines/`.

**Acceptance criteria.**

- `make e2e` build stack, chạy Playwright, tear down. Chạy local và CI.
- E2E fail block PR merge trên path liên quan.
- Test artifacts (screenshot + video khi fail) upload vào GitHub Actions run.

**Rủi ro và migration.** CI minutes mới. Mitigate bằng cách chỉ chạy E2E trên path liên quan và trên `main`.

## 5. Provider plugin system

**Vì sao quan trọng.** Thêm engine TTS hôm nay yêu cầu sửa `backend/src/voiceforge/providers/__init__.py` để register. Block hai use case thực: (a) operator self-host muốn thêm model nội bộ mà không fork, và (b) giữ list provider upstream manageable khi engine mới xuất hiện.

**Thay đổi gì.**

- Định nghĩa Protocol provider ổn định trong `backend/src/voiceforge/providers/protocol.py` (đã formalize một phần; biến thành ABC tagged).
- Discover provider qua Python entry points: `[project.entry-points."voiceforge.providers"]`. Provider built-in (voicevox, piper, kokoro, vieneu, openai, elevenlabs, google, azure) chuyển sang entry; registry load lúc startup.
- Cho phép `pip install voiceforge-provider-foo` phía operator để thêm provider mà không thay đổi code ở đây.
- Schema cho `provider parameter schemas` (đã structure per-provider) trở thành phần của return entry-point — registry đọc schema động.

**Acceptance criteria.**

- Mọi provider hiện hữu tiếp tục hoạt động, register qua entry point.
- Plugin ví dụ nhỏ trong directory riêng (`examples/voiceforge-provider-stub`) demonstrate contract; cài được bằng `pip install -e ./examples/...` và xuất hiện trong catalog.
- Protocol provider được document trong `docs/en/providers.md` với section "Tự build provider".

**Rủi ro và migration.** Nội bộ — không có breaking change phía operator.

## 6. Helm chart cho Kubernetes

**Vì sao quan trọng.** Compose tốt cho self-host single-host. Vượt quá đó (multi-replica, autoscale, Postgres managed, Redis managed), operator chuyển sang Kubernetes. Helm chart first-class giữ deployment story của dự án nhất quán.

**Thay đổi gì.**

- Chart mới `deploy/helm/ntd-audio/`. Một Deployment per service (api, worker, frontend), một Job cho `migrate`, sub-chart optional cho Postgres / Redis (hoặc BYO qua values).
- Engine sidecar trở thành optional `values.engines.{voicevox,piper,kokoro,vieneu}.enabled`.
- Secret qua `values.secrets` (operator có thể wire ExternalSecrets / Sealed Secrets / cloud KMS).
- Template Ingress với TLS qua cert-manager.
- Probe health/readiness từ `/health` (đã thiết kế cho việc này).
- Hook `helm test` hit `/health` và `/metrics` chống chart đã deploy.

**Acceptance criteria.**

- `helm install ntd-audio deploy/helm/ntd-audio --set ...` ra app chạy được trên cluster kind / k3d.
- `helm test` pass.
- Chart publish lên Helm repo backed bởi GitHub Pages khi tag.
- Document trên `self-hosting.md` (hoặc `kubernetes.md` mới) với ví dụ values.

**Rủi ro và migration.** Surface deployment mới phải maintain. Defer cho đến khi đường Compose hoàn toàn ổn định (đã ổn định).

## 7. Telemetry opt-in ẩn danh

**Vì sao quan trọng.** "Engine nào phổ biến? Script điển hình lớn cỡ nào? Feature nào người ta thực sự dùng?" — những câu hỏi này feed prioritization. Không có telemetry, dự án bay mù. **Strict opt-in** là design duy nhất chấp nhận được — surveillance-mặc-định không tương thích với self-host.

**Thay đổi gì.**

- Env var mới `TELEMETRY_ENABLED=false` (default). Operator phải set explicit `true`.
- Ping nhỏ daily từ API: `POST https://telemetry.<domain dự án>/v1/install` với:
  - Anonymous install ID (UUID generate ở first run, persist trong `app_settings`).
  - Version, OS / arch.
  - Đếm số (không phải nội dung) của: job theo provider (24h), project active, voice distinct sử dụng.
  - **Không bao giờ:** nội dung text, sample voice, tên project, dữ liệu user.
- Schema payload chính xác được document trong `docs/en/operations.md` dưới section "Telemetry" mới. Schema là phần của contract công khai; thay đổi yêu cầu CHANGELOG entry.
- `/v1/settings/telemetry/preview` trả JSON chính xác sẽ gửi hôm nay, để operator audit được.

**Acceptance criteria.**

- `TELEMETRY_ENABLED=false` (default) không gửi gì — verify bằng network test.
- `TELEMETRY_ENABLED=true` gửi payload đã document daily.
- Operator preview và audit được mọi payload trước khi gửi.
- Document làm rõ guarantee data minimization và liệt kê mọi field với rationale.

**Rủi ro và migration.** Không có cho install hiện hữu (default off). Niềm tin phụ thuộc vào tính minh bạch.

## 8. Garbage collection cho artifact

**Vì sao quan trọng.** Artifact và row `generation_cache` tích lũy mãi mãi hôm nay. Install dùng nặng cuối cùng sẽ đầy disk hoặc S3 bucket. Không có cần để control retention ngoài delete thủ công.

**Thay đổi gì.**

- Table mới `retention_policies` (hoặc cột trên `projects.settings.retention`): `keep_days_succeeded`, `keep_days_failed`, `keep_days_canceled`. Default: `keep_days_succeeded=null` (mãi mãi), `keep_days_failed=30`, `keep_days_canceled=14`.
- Job nightly (Dramatiq scheduled actor):
  - Select job cũ hơn policy.
  - Mỗi job: delete artifact qua `ArtifactStorage.delete(key)`, delete row `generation_cache`, set `synthesis_jobs.archived_at`.
  - Đếm metric: `voiceforge_artifacts_pruned_total{reason}`.
- Endpoint admin `POST /v1/admin/retention/run-now` để trigger thủ công (gate bởi superuser).
- Document policy default và cách override per-project.

**Acceptance criteria.**

- Test tạo job aged (với `created_at` backdate) xác nhận chúng bị prune bởi pass GC.
- Pruning tôn trọng `ArtifactStorage` được chọn (chạy trên S3 và local).
- Operator disable GC hoàn toàn được với `RETENTION_ENABLED=false`.

**Rủi ro và migration.** Đây là destructive; env var mới default off ở v1 và on ở v2 sau feedback operator.

## Vượt qua v1 của danh sách này

Chưa prioritize nhưng trên radar:

- **i18n: thêm locale** (JP, ZH, KR). Tooling frontend đã support; công việc là dịch.
- **Test coverage frontend** ở mức component cho ScriptEditor (drag-drop), Settings (provider creds), Library (paginated, filterable).
- **UX voice cloning.** Khả năng tồn tại với ElevenLabs, VieNeu — UI chưa support sạch upload reference audio, đặt tên clone, route job đến đó.
- **Export / import project.** User self-host muốn "project bundle" portable (script row + voice mapping + artifact đã hoàn thành) cho backup, share, migration.
- **WebSocket hoặc SSE-over-HTTP/2 cho event.** SSE chạy nhưng không multiplex; trên mạng chậm có thể đụng giới hạn connection-per-tab.

## Cách đề xuất sáng kiến mới

1. Mở GitHub issue mô tả triệu chứng, không phải solution.
2. Nếu đề xuất solution, fork structure của doc này (Why / What changes / Acceptance / Risk).
3. Link issue liên quan.
4. PR pick up một mục nên di chuyển entry từ doc này vào `feature-map.md` khi land, kèm đường dẫn file.
