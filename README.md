# VoiceForge Studio

VoiceForge Studio là codebase cho **voice generation / TTS orchestration** theo hướng:

- **PostgreSQL-first**
- **FastAPI + worker + Redis**
- UI quản lý job/provider/project
- Hỗ trợ cả **cloud TTS** và **open-source/self-hosted TTS runtimes thật**
- Có **SSE stream** để frontend tự cập nhật, không cần F5 liên tục

## Bản cập nhật này tập trung vào gì

Phần khó nhất của codebase trước là các engine open-source vẫn ở mức adapter/placeholder. Bản này chuyển 3 engine sang **runtime thật**:

- **Piper** runtime thật bằng `piper-tts` + tải voice models bằng `python -m piper.download_voices`  
- **Kokoro** runtime thật bằng official `kokoro` Python library và `KPipeline`  
- **VieNeu-TTS** runtime thật bằng official `vieneu` SDK ở chế độ local/turbo  

Ngoài ra vẫn giữ:
- **VOICEVOX** self-hosted engine thật
- các cloud adapters: OpenAI / ElevenLabs / Google / Azure

## Cấu trúc runtime

```text
frontend (React/Vite)
api (FastAPI)
worker (Dramatiq)
postgres
redis
voicevox
piper-runtime
kokoro-runtime
vieneu-runtime
```

## Các engine open-source đã tích hợp thật

### 1) VOICEVOX
Dùng image engine chính thức của VOICEVOX.

### 2) Piper
- runtime riêng tại `engines/piper-runtime`
- dùng package `piper-tts`
- có thể auto-download voices khi service khởi động
- hiện compose mặc định gợi ý các voice:
  - `vi_VN-vais1000-medium`
  - `en_US-lessac-medium`
  - `en_GB-alan-medium`

### 3) Kokoro
- runtime riêng tại `engines/kokoro-runtime`
- dùng package `kokoro`
- synthesize thật qua `KPipeline`
- hỗ trợ nhóm voices English và một số locale khác theo model/voice set Kokoro

### 4) VieNeu-TTS
- runtime riêng tại `engines/vieneu-runtime`
- dùng package `vieneu`
- chạy local Turbo mode để ưu tiên deployment thực tế cho CPU/local trước
- dùng preset voices từ SDK và synthesize thật

## Chạy stack cơ bản

```bash
cp .env.example .env
docker compose up --build
```

Services mặc định:
- frontend: `http://localhost:5173`
- api: `http://localhost:8000`
- docs: `http://localhost:8000/docs`
- postgres: `localhost:5432`

## Chạy kèm tất cả OSS runtimes

```bash
docker compose -f docker-compose.yml -f docker-compose.oss.yml up --build
```

## Chạy từng runtime riêng

### Piper
```bash
docker compose -f docker-compose.yml -f docker-compose.piper.yml up --build
```

### Kokoro
```bash
docker compose -f docker-compose.yml -f docker-compose.kokoro.yml up --build
```

### VieNeu-TTS
```bash
docker compose -f docker-compose.yml -f docker-compose.vieneu.yml up --build
```

## GPU cho VOICEVOX

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build
```

## Biến môi trường quan trọng

### Core
- `DATABASE_URL`
- `REDIS_URL`
- `ARTIFACT_ROOT`
- `CACHE_ROOT`

### VOICEVOX
- `VOICEVOX_BASE_URL`

### Piper runtime
- `PIPER_BASE_URL`
- `PIPER_TIMEOUT_SECONDS`
- `PIPER_VOICE_IDS`
- `PIPER_DOWNLOAD_ON_START`

### Kokoro runtime
- `KOKORO_BASE_URL`
- `KOKORO_TIMEOUT_SECONDS`

### VieNeu runtime
- `VIENEU_TTS_BASE_URL`
- `VIENEU_TTS_TIMEOUT_SECONDS`

## Ghi chú thực tế

### Piper
Piper runtime là integration thật, nhưng model files phụ thuộc voice IDs mà anh chọn. Compose override hiện đã hỗ trợ auto-download một số voice phổ biến khi service khởi động.

### Kokoro
Kokoro runtime là integration thật qua official Python library. Lần chạy đầu có thể chậm hơn vì model/weights cần được kéo về local cache.

### VieNeu-TTS
VieNeu runtime trong repo này dùng local Turbo mode của official SDK để dễ self-host và dễ chạy local hơn. Nó là engine thật, không còn chỉ là contract mẫu nữa. Tuy vậy, em chưa thể verify end-to-end package build trong môi trường hiện tại.

## SSE
Backend có:
- `GET /events/snapshot`
- `GET /events/stream`

Frontend có thể subscribe SSE để tự cập nhật jobs / events / project stats mà không cần refresh tay.

## Project management
Repo hiện đã có lớp project để tổ chức workflow:
- project metadata
- default provider / output format
- tags / settings
- jobs gắn với project

Đây là base để sau này mở sang:
- workspace
- presets
- access control
- billing / usage analytics

## Tài liệu nên đọc tiếp
- `ARCHITECTURE.md`
- `SCHEMA.md`
- `CURRENT_STATE.md`
- `ROADMAP_4_WEEKS.md`


## Performance, monitoring and self-host operations

This build adds:
- backend voice search (`/catalog/voices/search`)
- monitor endpoints (`/monitor/status`, `/monitor/logs`)
- change-aware SSE snapshots with heartbeat fallback
- request/job lifecycle logging to rotating log files
- in-app self-host monitor page

See `PERFORMANCE_NOTES.md` for the bottlenecks found and what was changed.


## Engine logs in Monitor

The Monitor page can now tail both:
- application logs (`api`, `worker`)
- engine container logs (`voicevox`, `piper`, `kokoro`, `vieneu`)

For Docker Compose deployments, the API container reads engine logs through the Docker socket mounted read-only at `/var/run/docker.sock`.

## Project script rows

Projects can now store ordered script rows through the backend API:
- `GET /projects/{project_key}/rows`
- `PUT /projects/{project_key}/rows`
- `POST /projects/{project_key}/rows/queue`
- `POST /projects/{project_key}/rows/merge`

This model is intended for line-by-line narration workflows where each row can be regenerated independently and optionally merged into a final master file.

## Script line editor UI

Bản này đã kéo `project_script_rows` lên thành màn hình frontend hoàn chỉnh tại route `#/script`.

UI hiện hỗ trợ:
- chọn project đang làm việc
- import script nhiều dòng
- thêm / sửa / xoá / nhân bản / reorder từng dòng
- bật/tắt từng dòng
- chọn dòng có được đưa vào file master hay không
- gán voice riêng cho từng dòng bằng full voice picker đa engine
- bulk apply voice cho các dòng đã chọn hoặc toàn bộ dòng bật
- lưu script rows xuống backend
- render dòng đã chọn hoặc toàn bộ dòng bật
- preview/download artifact từng dòng
- merge các dòng đã hoàn thành thành một master audio artifact

Workflow thực tế nên dùng:
1. tạo project
2. mở `Script Editor`
3. import hoặc thêm từng dòng text
4. gán voice mặc định hoặc override từng dòng
5. save rows
6. queue selected/enabled rows
7. nghe lại artifact từng dòng
8. merge completed rows thành file master

Lưu ý: API rows hiện dùng `PUT` replace toàn bộ rows, nên khi sửa script và lưu, các row được tái tạo theo thứ tự hiện tại. Đây là lựa chọn đơn giản cho MVP; phase sau nên bổ sung PATCH từng row để giữ lịch sử chi tiết hơn.

## Provider credentials and per-engine voice settings

Bản này bổ sung một lớp settings thực tế cho self-host và cloud providers:

- `GET /settings`
- `PUT /settings/provider-credentials/{provider_key}`
- `GET /settings/voice-parameter-schemas`
- `PATCH /settings/merge-defaults`

### API keys / runtime endpoints

Vào **Settings → Provider credentials** để cấu hình:
- OpenAI API key / model
- ElevenLabs API key / model
- Google Cloud TTS access token / project id
- Azure Speech key / region
- VOICEVOX / Piper / Kokoro / VieNeu runtime URL

Nếu biến môi trường tương ứng đã được set, ENV sẽ được ưu tiên hơn DB settings. UI sẽ hiển thị trạng thái `ENV override active` để tránh nhầm lẫn.

### Voice parameter schema

Không dùng một form cố định cho tất cả voice. Mỗi provider có schema riêng:
- OpenAI: `speed`, `instructions`
- ElevenLabs: `speed`, `stability`, `similarity_boost`, `style`, `use_speaker_boost`
- Google: `speakingRate`, `pitch`, `volumeGainDb`, `sampleRateHertz`
- Azure: SSML-style `rate`, `pitch`, `volume`, `style`
- VOICEVOX: `speedScale`, `pitchScale`, `intonationScale`, `volumeScale`, pause controls
- Piper: `length_scale`, `noise_scale`, `noise_w`, `speaker_id`
- Kokoro / VieNeu: speed/reference-oriented controls

Frontend dùng schema này để render form động ở:
- `Create Job`
- `Script Editor` row-level voice settings
- `Settings → Voice parameter schemas`

### Merge defaults

`merge_silence_ms`, `merge_output_format`, `normalize_loudness` được cấu hình ở hai cấp:
- **Global merge defaults** trong Settings
- **Project defaults** trong Settings, override global cho project hiện tại

Script Editor dùng project defaults làm giá trị ban đầu cho merge master audio.
