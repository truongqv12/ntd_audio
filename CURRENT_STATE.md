# Current State

## Đã làm xong trong bản này

### Engine integration thật
- `VOICEVOX`: đang là engine thật
- `Piper`: đã có runtime service thật bằng `piper-tts`
- `Kokoro`: đã có runtime service thật bằng official `kokoro`
- `VieNeu-TTS`: đã có runtime service thật bằng official `vieneu`

### Backend
- PostgreSQL-first schema
- project layer
- job orchestration + artifact metadata + cache
- SSE endpoints
- provider registry không còn `mock`

### Infra
- `docker-compose.yml` base stack
- `docker-compose.piper.yml`
- `docker-compose.kokoro.yml`
- `docker-compose.vieneu.yml`
- `docker-compose.oss.yml`
- `docker-compose.gpu.yml`

## Mức độ hoàn thiện hiện tại

### Đã ở mức usable foundation
- orchestration rõ
- runtimes thật đã có chỗ cắm và source trong repo
- UI/UX không còn ở mức thô sơ
- schema rõ và tiếp tục mở rộng được

### Chưa thể nói là production-ready hoàn toàn
- chưa có cancel/retry policy hoàn chỉnh
- chưa có benchmarking tự động
- chưa có auth/workspace isolation hoàn thiện
- chưa verify end-to-end tất cả engine builds trong môi trường hiện tại

## Điểm cần nói thẳng

### Piper
Integration là thật và thực tế nhất trong 3 OSS runtimes mới. Dựa trên package và CLI chính thức.

### Kokoro
Integration là thật. Service wrapper dùng official inference library. Tuy nhiên, lần chạy đầu sẽ phụ thuộc việc model weights được tải thành công.

### VieNeu-TTS
Integration là thật ở mức code/runtime design, dùng official SDK thay vì placeholder contract. Nhưng em chưa thể xác nhận build runtime end-to-end ngay trong container hiện tại.

## Priority tiếp theo nên làm

1. smoke-test từng runtime trên máy/dev server thật
2. upload reference audio flow cho cloning
3. cancel / retry job lifecycle
4. provider-specific advanced form renderer
5. artifact storage abstraction

## Script editor completed

The frontend now includes a dedicated `Script Editor` page wired to the existing project row APIs.

Implemented:
- project selector
- multiline import
- editable row table
- add/delete/duplicate/reorder rows
- row selection
- row-level voice picker
- bulk voice assignment
- save rows
- queue selected rows
- queue enabled rows
- row artifact preview/download
- merge completed rows into master audio

Remaining future improvements:
- row-level PATCH instead of replace-all save
- keyboard shortcuts
- row virtualization for very large scripts
- per-row advanced provider parameters editor
- retry failed rows quick action
- waveform preview

## Provider settings and parameter schemas completed

Implemented in this build:
- `app_settings` persistence for provider credentials and global merge defaults
- `/settings` API group
- runtime provider config application before provider health/catalog/synthesis access
- masked secret handling in UI
- env variables take precedence over DB settings
- provider-specific voice parameter schemas
- dynamic voice parameter UI in Create Job
- dynamic row-level voice parameter UI in Script Editor
- Settings page sections for provider credentials, project defaults, global merge defaults and schema inspection

Remaining future work:
- encrypt secrets at rest or integrate a real secret manager
- per-project provider credential scoping for future public/shared mode
- PATCH row API so parameter changes can preserve row identity/history
- deeper provider-specific validation based on live voice metadata
