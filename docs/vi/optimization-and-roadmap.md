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

### 6. Auto-detect GPU / CPU — **đã ship**

Triển khai trong `services_system.py`, expose tại `GET /v1/system/capabilities`.

- Probe chạy `nvidia-smi --query-gpu=name,memory.total --format=csv,noheader,nounits` 1 lần / process (cache theo lifetime container — capability không thay đổi nếu không restart).
- CPU info dùng `os.sched_getaffinity(0)` khi có (cgroup-aware trên Docker), nếu không thì `os.cpu_count()`.
- Shape response: `{ gpu: { vendor, name, vram_mb } | null, cpu: { cores, threads }, recommended_overlays: ["docker-compose.gpu.yml"] }`. GPU `null` trên host CPU-only và `recommended_overlays` rỗng.
- Frontend: Settings page có panel "Host" mới render hardware đã detect cộng câu lệnh `docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d` chính xác để switch overlay khi có GPU.

Reporting "engine load device nào thực sự" (CPU vs CUDA) từ trong engine container vẫn là extension mở; hiện panel báo cái container API thấy được, đủ verify GPU được mount đúng vào compose project.

### 7. Concurrency tuning per provider — **đã ship**

Triển khai trong `services_provider_concurrency.py`, wrap synthesize call ở `services_jobs.process_job`.

- `BoundedSemaphore` process-local per provider key; tạo lazy lúc job đầu chạy.
- Default: provider `cloud` → 4 call song song (network-bound), `self_hosted` → 1 (1 backend CPU/GPU duy nhất).
- Override theo category: `PROVIDER_CONCURRENCY_CLOUD` / `PROVIDER_CONCURRENCY_SELF_HOSTED`.
- Override per-provider: `PROVIDER_CONCURRENCY` (JSON dict, vd `{"openai": 6, "voicevox": 2}`).
- Limit hiện hành lộ ra ở `GET /v1/providers` qua field `concurrency_limit`.

Nếu scale bằng nhiều worker process (vd `dramatiq voiceforge.tasks --processes 2`), trần thực tế là `worker_count * provider_limit`. Với personal-use single-host, đây là tradeoff đúng (không cần coordination Redis-side).

Bản tiếp theo có thể thêm Settings → "Performance" panel để persist override trong `app_settings`. Hiện chưa làm — env-driven đã đủ cho personal-use.

### 8. Wire `ArtifactStorage` vào `write_artifact` — **đã ship (write path)**

`storage.py::write_artifact` giờ delegate vào `services.storage.get_storage().write_bytes(...)`. Operator set `STORAGE_BACKEND=s3` (hoặc re-target `ARTIFACT_ROOT` qua NAS / ổ ngoài) cuối cùng thấy bytes route qua abstraction. Contract `(relative_key, size, sha256_hex)` không đổi.

Đường đọc (`artifact_absolute_path` + `FileResponse`) vẫn local-fs only. Thêm S3 read / redirect — stream bytes qua FastAPI hoặc trả presigned URL — là follow-up tự nhiên nhưng cố ý out of scope ở đây để PR nhỏ và reviewable.

Migration tree artifact local hiện hữu sang S3 vẫn cần `aws s3 sync` ngoài luồng (không copy tự động lúc boot).

---

## Tier 3 — Quality of life

### 9. Provider plugin entry points — **đã ship (discovery)**

Registry hiện discover provider thứ ba từ entry-point group `voiceforge.providers` lúc startup. Một package có dạng

```toml
[project.entry-points."voiceforge.providers"]
my_engine = "my_pkg.module:MyProvider"
```

đăng ký provider ngay khi `pip install` vào cùng environment với API. Factory có thể là class hoặc callable trả instance của `VoiceProvider`. Lỗi lúc discovery được log và skip — một plugin hỏng không làm chết API. Plugin không thể shadow key built-in (built-in thắng, plugin được log và ignore).

Provider built-in vẫn import eager để cold-start cost và mypy strictness không đổi. Migrate chúng sang entry point là follow-up khả thi nhưng không cần thiết cho use case ("cho tôi ship model riêng"). `examples/voiceforge-provider-stub` cùng section "Tự build provider" trong `docs/en/providers.md` là bước tiếp theo tự nhiên.

### 10. Retention controls đơn giản — **đã ship**

Trang Settings có panel "Retention" với window "Cũ hơn (ngày)" cấu hình được (default 30). Endpoint mới:

- `GET /v1/admin/retention/preview?older_than_days=N` trả `{ cutoff_iso, job_count, artifact_count, bytes_on_disk }`.
- `POST /v1/admin/retention/purge` body `{ older_than_days: N, confirm: true }` xóa terminal job (`succeeded`/`failed`/`canceled`) cũ hơn cutoff cùng artifact (DB row + file trên disk). API reject nếu thiếu `confirm: true`.

Flow UI là preview → confirm → delete: nút "Xóa ngay" disable đến khi load được preview non-empty. Job active và recent không bao giờ bị động. Counter `voiceforge_artifacts_pruned_total` và filter theo status là follow-up có chủ ý.

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
