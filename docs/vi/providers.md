# Engine

> **Dành cho AI agent:** mỗi adapter provider triển khai cùng Protocol. Khi thêm provider mới, mirror file có sẵn trong `backend/src/voiceforge/providers/` và cập nhật registry.
>
> **Dành cho người đọc:** ma trận engine được hỗ trợ, capability, env var, và cách chúng đi tới API.

## TL;DR

- Cloud (4): OpenAI, ElevenLabs, Google Cloud TTS, Azure Speech.
- Mã nguồn mở / self-hosted (4): VOICEVOX, Piper, Kokoro, VieNeu-TTS.
- Mọi provider expose `synthesize`, `list_voices`, `health` cho worker. Worker không bao giờ special-case provider; khác biệt capability đi qua metadata.

## Ma trận capability

| Engine | Loại | Tiếng Việt | Tiếng Anh | Cloning | Streaming | Ngôn ngữ chính | Compose overlay |
|---|---|---|---|---|---|---|---|
| **VOICEVOX** | OSS, self-hosted | – | – | – | – | Tiếng Nhật | base + (tùy chọn) `gpu.yml` |
| **Piper** | OSS, self-hosted | có | có | – | – | Đa ngôn ngữ qua voice file | `piper.yml` / `oss.yml` |
| **Kokoro** | OSS, self-hosted | – | có | – | – | Ưu tiên tiếng Anh | `kokoro.yml` / `oss.yml` |
| **VieNeu-TTS** | OSS, self-hosted | có (focus) | – | có | – | Tiếng Việt | `vieneu.yml` / `oss.yml` |
| **OpenAI** | Cloud | – | có | – | có | Đa ngôn ngữ | – |
| **ElevenLabs** | Cloud | có | có | có | có | Đa ngôn ngữ | – |
| **Google Cloud TTS** | Cloud | có | có | – | có | Đa ngôn ngữ | – |
| **Azure Speech** | Cloud | có | có | có | có | Đa ngôn ngữ | – |

"Cloning" = cloning giọng từ audio reference. "Streaming" = engine trả audio chunk trước khi sample đầy đủ sẵn sàng.

## Engine self-hosted

### VOICEVOX

- Image: VOICEVOX engine chính thức.
- Endpoint: `VOICEVOX_BASE_URL` (mặc định `http://voicevox:50021`).
- Worker gọi `/speakers`, `/audio_query`, `/synthesis`.
- Bản GPU qua `docker-compose.gpu.yml`.

### Piper

- Runtime: `engines/piper-runtime/` (repo này).
- Build trên package `piper-tts`.
- Voice: set qua `PIPER_VOICE_IDS` (CSV voice ID từ danh sách Piper). Auto-download lúc startup nếu `PIPER_DOWNLOAD_ON_START=true`.
- Endpoint: `PIPER_BASE_URL` (mặc định `http://piper:8080`).

### Kokoro

- Runtime: `engines/kokoro-runtime/`.
- Build trên thư viện `kokoro` chính thức; dùng `KPipeline`.
- Endpoint: `KOKORO_BASE_URL` (mặc định `http://kokoro:8080`).
- Cold start tải model weights từ HuggingFace; synthesis đầu tiên chậm.

### VieNeu-TTS

- Runtime: `engines/vieneu-runtime/`.
- Build trên SDK `vieneu` chính thức ở mode local Turbo (CPU-friendly).
- Endpoint: `VIENEU_TTS_BASE_URL` (mặc định `http://vieneu:8080`).

## Engine cloud

| Provider | Env var bắt buộc | Tùy chọn |
|---|---|---|
| OpenAI | `OPENAI_API_KEY` | `OPENAI_TTS_MODEL` (mặc định `gpt-4o-mini-tts`) |
| ElevenLabs | `ELEVENLABS_API_KEY` | `ELEVENLABS_MODEL_ID` (mặc định `eleven_multilingual_v2`) |
| Google Cloud TTS | `GOOGLE_TTS_ACCESS_TOKEN`, `GOOGLE_TTS_PROJECT_ID` | – |
| Azure Speech | `AZURE_SPEECH_KEY`, `AZURE_SPEECH_REGION` | – |

Mỗi provider tự register khi credential có. Credential rỗng = provider bị filter ra khỏi catalog.

## Thêm provider mới

File:

```
backend/src/voiceforge/providers/<provider_key>.py   # adapter
backend/src/voiceforge/providers/__init__.py         # register
backend/src/voiceforge/services_catalog.py           # voice listing (nếu phức tạp)
```

Protocol adapter (informal):

```python
class Provider:
    key: str

    def health(self) -> ProviderHealth: ...
    def list_voices(self, *, timeout_seconds: float) -> list[CatalogEntry]: ...
    def synthesize(self, *, text: str, voice_id: str, params: dict, output_format: str) -> bytes: ...
```

Sau đó:

1. Register vào provider registry.
2. Thêm env var vào `.env.example` với default rỗng để engine tắt cho đến khi operator opt-in.
3. Thêm dòng vào ma trận capability ở trên.
4. Nếu provider có tham số đặc thù, thêm parameter schema vào `services_app_settings.py` để UI render đúng form.
5. Nếu provider cần sidecar container (OSS engine có), drop một `docker-compose.<key>.yml` overlay và document trong [`self-hosting.md`](self-hosting.md).

## Parameter schema của provider

Mỗi provider khai báo tham số mà synthesis của nó nhận. Frontend đọc qua `/v1/settings/schemas` và render form (slider số, dropdown enum, ...) phù hợp — không cần code UI per-provider.
