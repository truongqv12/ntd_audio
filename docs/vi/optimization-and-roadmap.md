# Tối ưu & roadmap

> **Cho AI agents:** đây là tài liệu **hướng tương lai**. Mọi mục bên dưới **chưa được implement**. Không document chúng như đang tồn tại. Khi làm một mục, di chuyển khối tương ứng vào `feature-map.md` (kèm đường dẫn file đã land) và rút gọn entry tại đây.
>
> **Cho con người:** danh sách công việc post-Epic-4 đã sắp xếp theo độ ưu tiên, scope theo hình dạng deploy thực tế của dự án: **một người dùng, chạy stack trên một máy bằng Docker.** Mục tiêu là tối ưu giá trị tính năng và UX, không phải hạ tầng đa người dùng / platform-grade.

## TL;DR

- Đối tượng triển khai là **một người, một Docker host**. Multi-user, multi-tenant, Kubernetes — cố tình nằm ngoài phạm vi.
- Tier 1 là **tính năng mới hướng người dùng** (bulk import, multi-voice dialogue, subtitle output).
- Tier 2 là **thích nghi host** (GPU detect, concurrency tuning).
- Tier 3 là **quality of life** (provider plugins, retention đơn giản, smoke E2E).
- Mục "Out of scope" liệt kê những gì cố tình bị loại khỏi roadmap trước và lý do.

## Phạm vi: ai dùng cái này

`ntd_audio` được xây cho người dev chạy trên máy mình để sản xuất audio TTS cho dự án cá nhân (video, podcast, audio drama, học liệu). Điều đó định hình mọi quyết định ưu tiên dưới đây:

- **Auth** chỉ là "API key hoặc không có gì" — không có người thứ hai.
- **Deploy** là `docker compose up`. Helm / Kubernetes / autoscaling không áp dụng.
- **Worker** chạy cùng máy với API. Priority queue, dead-letter queue, per-tenant concurrency cap thêm phức tạp mà không lợi ích gì.
- **Telemetry** không áp dụng — một install ẩn danh đơn lẻ không cho project học được gì.

## Cách tổ chức tài liệu này

Mỗi mục:
1. **Vì sao quan trọng** (pain cụ thể được loại bỏ cho install single-user).
2. **Thay đổi gì** (file / component bị ảnh hưởng).
3. **Acceptance criteria** (test chứng minh đã ship).
4. **Rủi ro và migration** (install hiện hữu cần làm gì).

---

## Tier 1 — Tính năng hướng người dùng

### 1. Bulk import: TXT / CSV → batch project — **đã ship**

Triển khai trong `routes_project_rows.py` + `services_bulk_import.py` + `BulkImportDialog.tsx`.

- `POST /v1/projects/{key}/rows/bulk` (multipart): TXT split theo line / blank-line, CSV với `text_column` cấu hình được, các cột `voice_column`, `speaker_column`, `title_column` tùy chọn. `auto_enqueue=true` enqueue toàn bộ row vừa import.
- `GET /v1/projects/{key}/rows/artifacts.zip?status=succeeded` stream zip nén deflate đặt tên `{key}_{row_index:03d}_{slug}.{ext}`.
- Giới hạn: `BULK_IMPORT_MAX_ROWS=5000`, `BULK_IMPORT_MAX_BYTES=5_242_880`. Trả 413 / 422 cho upload quá lớn hoặc parse lỗi.
- Frontend: nút "Nhập .txt / .csv" + "Tải tất cả .zip" trong toolbar script editor.

Cancel cả batch và cancel từng row dùng hạ tầng queue/cancel có sẵn (Epic 3). Truyền speaker label sang subtitle theo dõi ở #3.

### 2. Multi-voice / dialogue mode — **đã ship (minimum viable)**

Per-row voice routing đã có sẵn qua `provider_voice_id`. Vòng này thêm phần thiếu: cột `speaker_label` trên `project_script_rows` cùng input nhỏ phía dưới ô title trong script editor.

- Migration `20260424_0004` thêm `speaker_label String(80) NULLABLE`. Row hiện hữu giữ `NULL`.
- Schema, `_serialize_row`, và `replace_project_rows` đều propagate `speaker_label`.
- Frontend: `DraftRow` mang `speaker_label`; ô title giờ chứa cả title input và 1 input speaker nhỏ phía dưới (placeholder: "Speaker label (optional)" / "Tên speaker (tuỳ chọn)").

Concat thành 1 mixdown conversation đã có sẵn (`merge_project_rows` + ffmpeg), nên dialogue mode tái dùng flag `join_to_master` và panel "Merge completed" hiện hữu.

Panel "Speakers" map `speaker_label → provider_voice_id` và auto-fill voice cho row mới đang cố ý hoãn. Với personal-use script một lần, set tay voice + speaker per row vẫn ổn; revisit nếu thấy bất tiện thật.

### 3. Subtitle output (.srt / .vtt)

**Vì sao quan trọng.** Cho creator video (đối tượng tự nhiên của workflow TTS này), file audio đơn lẻ chỉ là một nửa asset. Họ muốn 1 subtitle file đồng bộ per row hoặc per conversation, với speaker label tùy chọn cho dialogue.

**Thay đổi gì.**

- Artifact kind mới: `subtitle` (extension `.srt`; `.vtt` qua query param khi download).
- Cho engine emit timing info (một số cloud provider expose timestamp cấp phoneme hoặc câu), dùng timing đó trực tiếp.
- Cho engine không có, ước lượng timing từ `audio_duration_ms` và `char_count` (uniform char/s trong row, sentence break align với punctuation).
- Cho output mode "Conversation", subtitle là 1 `.srt` ghép cover toàn mixdown, mỗi row 1 cue và speaker label (nếu có) làm prefix (`[Anna] Hello there.`).
- Frontend: download subtitle xuất hiện cạnh download audio trên trang project.

**Acceptance criteria.**

- Sau job thành công, download subtitle trả SRT hợp lệ (verify với thư viện `srt`).
- Mode conversation tạo 1 SRT ghép; mode stems tạo 1 SRT per row.
- Cho engine emit timestamp thật (vd Google Cloud TTS markup mode), boundary cue SRT match audio thực tế nói (trong dung sai nhỏ).
- Cho engine không có timing info, SRT ít nhất monotonic và tổng duration match audio file.

**Rủi ro và migration.** Thuần addition. Artifact kind mới cần migration enum nhưng không destructive.

### 4. Inline preview 1 row — **đã ship**

Triển khai trong `routes_providers.py::preview_arbitrary_text` + helper `previewRowSynthesis` + nút "Nghe thử" per row trong script editor.

- `POST /v1/providers/{provider_key}/preview` nhận `{text, voice_id, output_format?, params?}` và stream audio về. Không tạo `synthesis_jobs`, không ghi artifact, không persist DB.
- Cap độ dài qua `PREVIEW_MAX_CHARS` (default 500). Trả 413 nếu vượt.
- Rate-limit dùng chung token bucket (`RATE_LIMIT_PER_MINUTE`).
- Frontend: mỗi row trong `ScriptEditor` có nút "Nghe thử" cạnh ô artifact. Kết quả render qua `<audio controls src=blob:...>`; blob URL được revoke khi unmount.

### 5. Project export bundle

**Vì sao quan trọng.** Project hoàn thành (script + voice mapping + audio + subtitle) là content portable user muốn backup, share, hoặc move giữa máy. Hôm nay, export yêu cầu tải tay từng artifact và nhớ voice nào đã dùng.

**Thay đổi gì.**

- Endpoint mới `GET /v1/projects/{key}/export` trả zip chứa:
  - `script.json` — dump full row, gồm `text`, `voice`, `speaker`, ordering.
  - `voice-map.json` — mapping speaker-to-voice-key (resolve theo catalog tại thời điểm export).
  - `original.txt` / `original.csv` — file đã import (nếu có), giữ nguyên văn.
  - `audio/` — mọi artifact thành công, đặt tên theo convention từ #1.
  - `subtitles/` — file `.srt` tương ứng (khi #3 land).
  - `metadata.json` — project ID, title, timestamp tạo/update, schema version.
- Đảo: `POST /v1/projects/import` nhận cùng zip và recreate project (idempotent trên `project_key`; artifact hiện hữu được reuse).

**Acceptance criteria.**

- Export project 50 row tạo 1 zip chứa mọi row, mọi audio, voice map.
- Import zip đó trên install mới recreate project với row giống thứ tự.
- Round-trip (export → import → export) tạo script.json và voice-map.json byte-identical.

**Rủi ro và migration.** Thuần addition. Schema export là phần của contract công khai; bump yêu cầu CHANGELOG entry.

---

## Tier 2 — Thích nghi host

### 6. Auto-detect GPU / CPU

**Vì sao quan trọng.** Engine OSS (đặc biệt Kokoro và VieNeu) chạy nhanh hơn rõ rệt trên GPU. Hôm nay, user phải tự chọn đúng Compose overlay và tin engine container pick GPU. Không có UI surface báo GPU acceleration có thực sự hoạt động không.

**Thay đổi gì.**

- Lúc API startup, probe host:
  - `nvidia-smi` có sẵn và trả device không?
  - `/dev/dri` populated không (Intel/AMD)?
  - `os.cpu_count()` báo gì?
- Expose ở `GET /v1/system/capabilities` (gate bằng API key khi có): `{ gpu: { vendor, name, vram_mb } | null, cpu: { cores, threads }, recommended_overlays: [...] }`.
- Per engine container, mở rộng `/healthz` nhỏ báo lại engine load lên device nào (CPU vs CUDA).
- Frontend: Settings → tab "Host" hiện hardware đã detect và engine nào đang dùng nó. Nếu có GPU nhưng overlay CPU-only đang active, surface hint "switch to GPU overlay" 1-click với câu lệnh `docker compose` chính xác.

**Acceptance criteria.**

- Trên host có NVIDIA GPU, `/v1/system/capabilities` báo đúng.
- Trên host CPU-only, field GPU là `null` và recommended overlay không gồm variant GPU.
- Tab Settings → Host match cái engine container thực sự báo.

**Rủi ro và migration.** Thuần addition. Không breaking change.

### 7. Concurrency tuning per provider — **đã ship**

Triển khai trong `services_provider_concurrency.py`, wrap synthesize call ở `services_jobs.process_job`.

- `BoundedSemaphore` process-local per provider key; tạo lazy lúc job đầu chạy.
- Default: provider `cloud` → 4 call song song (network-bound), `self_hosted` → 1 (1 backend CPU/GPU duy nhất).
- Override theo category: `PROVIDER_CONCURRENCY_CLOUD` / `PROVIDER_CONCURRENCY_SELF_HOSTED`.
- Override per-provider: `PROVIDER_CONCURRENCY` (JSON dict, vd `{"openai": 6, "voicevox": 2}`).
- Limit hiện hành lộ ra ở `GET /v1/providers` qua field `concurrency_limit`.

Nếu scale bằng nhiều worker process (vd `dramatiq voiceforge.tasks --processes 2`), trần thực tế là `worker_count * provider_limit`. Với personal-use single-host, đây là tradeoff đúng (không cần coordination Redis-side).

Bản tiếp theo có thể thêm Settings → "Performance" panel để persist override trong `app_settings`. Hiện chưa làm — env-driven đã đủ cho personal-use.

### 8. Wire `ArtifactStorage` vào `write_artifact`

**Vì sao quan trọng.** Kể cả install cá nhân, user thường muốn artifact ghi vào NAS, ổ ngoài, hoặc bucket S3-compatible trên home server (MinIO). Hôm nay, `STORAGE_BACKEND=s3` là no-op cho artifact mới vì đường ghi cũ bypass Protocol `ArtifactStorage`. Theo `self-hosting.md` set env vars sẽ ra setup hỏng âm thầm.

**Thay đổi gì.**

- Thay call `Path.write_bytes` / `cache_root` trực tiếp trong `services_jobs.process_job` bằng `storage = get_storage(); storage.write_bytes(key, audio_bytes)`.
- Tương tự cho đường ghi `generation_cache`.
- Migrate đường đọc đọc qua abstraction.
- Thêm smoke test boot MinIO trong CI và round-trip artifact.
- Document trong `self-hosting.md` rằng migration local → S3 cho artifact hiện hữu yêu cầu `aws s3 sync` (không copy tự động lúc boot).

**Acceptance criteria.**

- `STORAGE_BACKEND=s3` cộng `S3_*` env vars khiến job mới ghi vào bucket; download stream từ bucket; không gì chạm `ARTIFACT_ROOT`.
- `STORAGE_BACKEND=local` tiếp tục hoạt động bit-for-bit như cũ.
- Integration test mới pass với MinIO trong CI.

**Rủi ro và migration.** Install `local` hiện hữu không bị ảnh hưởng (default không đổi).

---

## Tier 3 — Quality of life

### 9. Provider plugin entry points

**Vì sao quan trọng.** Thêm engine TTS hôm nay yêu cầu sửa registry. Cho install cá nhân, user thỉnh thoảng muốn plug model riêng (fine-tune, checkpoint research, model ngôn ngữ niche) mà không fork dự án.

**Thay đổi gì.**

- Định nghĩa Protocol provider ổn định (đã formalize một phần) và biến thành ABC tagged.
- Discover provider qua `[project.entry-points."voiceforge.providers"]`. Provider built-in chuyển sang entry; registry load lúc startup.
- Plugin ví dụ nhỏ trong `examples/voiceforge-provider-stub` show contract.
- `docs/en/providers.md` thêm section "Tự build provider".

**Acceptance criteria.**

- Mọi provider hiện hữu tiếp tục hoạt động, register qua entry point.
- Plugin ví dụ cài được bằng `pip install -e ./examples/...` và xuất hiện trong catalog.

**Rủi ro và migration.** Nội bộ — không có breaking change phía operator.

### 10. Retention controls đơn giản

**Vì sao quan trọng.** Artifact và row `generation_cache` tích lũy mãi mãi. User casual với nhiều tháng experiment cuối cùng đầy disk. Roadmap trước đề xuất full retention policy table per-project — overkill cho personal use.

**Thay đổi gì.**

- Settings → panel "Storage": hiện disk usage artifact hiện tại, với nút duy nhất **"Delete jobs older than X days"** (slider, default 30 d, filter status tùy chọn: `failed` / `canceled` / `succeeded` / all).
- Endpoint backend `POST /v1/admin/retention/run-now { older_than_days, statuses }` — đồng bộ cho batch nhỏ, queued cho batch lớn.
- Đếm metric `voiceforge_artifacts_pruned_total{reason}` để user thấy bao nhiêu đã reclaim.

**Acceptance criteria.**

- User click "Delete jobs older than 30 days, failed only" và thấy disk usage giảm tương ứng.
- Action xóa cả DB row và storage object (chạy cho `local` và `s3`).
- Bước confirm tránh wipe nhầm cả history.

**Rủi ro và migration.** Destructive; action opt-in only và có confirm.

### 11. Playwright smoke E2E

**Vì sao quan trọng.** Vitest cover component cô lập; pytest cover handler. Không cái nào bắt được "tôi import CSV, queue batch, đợi qua SSE, và zip download không có đủ file." Một scenario smoke chặt bắt được class regression rộng.

**Thay đổi gì.**

- Một scenario: **bulk import → run → wait → download zip**. CSV 5 row, 2 voice, output mode "Conversation", expect 5 stem + 1 mixdown + 1 SRT trong zip.
- Chạy chống stub-provider Compose profile để không phụ thuộc cloud API.
- CI job mới `frontend-e2e` trên PR chạm `frontend/`, `backend/`, hoặc `engines/`.

**Acceptance criteria.**

- `make e2e` build stack, chạy scenario, tear down. Chạy local và CI.
- E2E fail block PR merge trên path liên quan.

**Rủi ro và migration.** CI minutes mới — limit cho path liên quan.

---

## Out of scope (cố tình loại)

Các mục này đã được đề xuất ở roadmap trước và cố tình **không** theo đuổi, do scope personal-use:

| Loại | Lý do |
|---|---|
| **JWT / multi-user auth** | Một user. Gate `X-API-Key` hiện tại đủ; không cần tài khoản, session, audit per-user. |
| **Workspace boundary / per-user audit** | Tương tự — vấn đề multi-tenant không áp dụng. |
| **Helm chart cho Kubernetes** | Một Docker host. Compose là deployment story. |
| **Worker scaling primitives (DLQ, priority queue, per-project concurrency cap)** | Một host với một worker không hưởng lợi gì. Tier 2 #7 (concurrency tuning) cover nhu cầu thực sự cho personal use. |
| **Telemetry opt-in ẩn danh** | Một install ẩn danh đơn lẻ không cho signal đáng thu thập. Phức tạp không xứng. |
| **Per-project retention policy (full table + nightly cron)** | Tier 3 #10 (1 nút "delete older than X days" duy nhất) cover nhu cầu thực với 1/10 phức tạp. |

Nếu scope dự án thay đổi (multi-user, hosted offering, fleet deployment), revisit section này.

---

## Cách đề xuất sáng kiến mới

1. Mở GitHub issue mô tả triệu chứng, không phải solution.
2. Nếu đề xuất solution, fork structure của doc này (Why / What changes / Acceptance / Risk).
3. Link issue liên quan.
4. PR pick up một mục nên di chuyển entry từ doc này vào `feature-map.md` khi land, kèm đường dẫn file.
