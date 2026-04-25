# Providers

> **For AI agents:** every provider adapter implements the same Protocol. When adding a new one, mirror an existing file under `backend/src/voiceforge/providers/` and update the registry.
>
> **For humans:** matrix of supported engines, capabilities, env vars, and how they reach the API.

## TL;DR

- Cloud (4): OpenAI, ElevenLabs, Google Cloud TTS, Azure Speech.
- Open-source / self-hosted (4): VOICEVOX, Piper, Kokoro, VieNeu-TTS.
- All providers expose `synthesize`, `list_voices`, `health` to the worker. The worker never special-cases a provider — capability differences flow through metadata.

## Capability matrix

| Engine | Type | Vietnamese | English | Cloning | Streaming | Locale focus | Compose overlay |
|---|---|---|---|---|---|---|---|
| **VOICEVOX** | OSS, self-hosted | – | – | – | – | Japanese | base + (optional) `gpu.yml` |
| **Piper** | OSS, self-hosted | yes | yes | – | – | Multilingual via voice files | `piper.yml` / `oss.yml` |
| **Kokoro** | OSS, self-hosted | – | yes | – | – | English-first | `kokoro.yml` / `oss.yml` |
| **VieNeu-TTS** | OSS, self-hosted | yes (focus) | – | yes | – | Vietnamese | `vieneu.yml` / `oss.yml` |
| **OpenAI** | Cloud | – | yes | – | yes | Multilingual | – |
| **ElevenLabs** | Cloud | yes | yes | yes | yes | Multilingual | – |
| **Google Cloud TTS** | Cloud | yes | yes | – | yes | Multilingual | – |
| **Azure Speech** | Cloud | yes | yes | yes | yes | Multilingual | – |

"Cloning" here means voice cloning from reference audio. "Streaming" means the engine returns audio chunks before the full sample is ready.

## Self-hosted engines

### VOICEVOX

- Image: official VOICEVOX engine.
- Endpoint: `VOICEVOX_BASE_URL` (default `http://voicevox:50021`).
- Worker calls `/speakers`, `/audio_query`, `/synthesis`.
- GPU build available via `docker-compose.gpu.yml`.

### Piper

- Runtime: `engines/piper-runtime/` (this repo).
- Built on `piper-tts` Python package.
- Voices: set via `PIPER_VOICE_IDS` (CSV of voice IDs from the Piper voice list). Auto-downloaded at startup if `PIPER_DOWNLOAD_ON_START=true`.
- Endpoint: `PIPER_BASE_URL` (default `http://piper:8080`).

### Kokoro

- Runtime: `engines/kokoro-runtime/`.
- Built on the official `kokoro` Python library; uses `KPipeline`.
- Endpoint: `KOKORO_BASE_URL` (default `http://kokoro:8080`).
- Cold start downloads model weights from HuggingFace; first synthesis is slow.

### VieNeu-TTS

- Runtime: `engines/vieneu-runtime/`.
- Built on the official `vieneu` SDK in local Turbo mode (CPU-friendly).
- Endpoint: `VIENEU_TTS_BASE_URL` (default `http://vieneu:8080`).

## Cloud engines

| Provider | Required env vars | Optional |
|---|---|---|
| OpenAI | `OPENAI_API_KEY` | `OPENAI_TTS_MODEL` (default `gpt-4o-mini-tts`) |
| ElevenLabs | `ELEVENLABS_API_KEY` | `ELEVENLABS_MODEL_ID` (default `eleven_multilingual_v2`) |
| Google Cloud TTS | `GOOGLE_TTS_ACCESS_TOKEN`, `GOOGLE_TTS_PROJECT_ID` | – |
| Azure Speech | `AZURE_SPEECH_KEY`, `AZURE_SPEECH_REGION` | – |

Each provider is automatically registered when its credentials are present. With empty credentials, the provider is filtered out of the catalog — clients won't see it.

## Adding a new provider

Files:

```
backend/src/voiceforge/providers/<provider_key>.py   # adapter
backend/src/voiceforge/providers/__init__.py         # register
backend/src/voiceforge/services_catalog.py           # voice listing (if non-trivial)
```

Adapter Protocol (informal):

```python
class Provider:
    key: str

    def health(self) -> ProviderHealth: ...
    def list_voices(self, *, timeout_seconds: float) -> list[CatalogEntry]: ...
    def synthesize(self, *, text: str, voice_id: str, params: dict, output_format: str) -> bytes: ...
```

Then:

1. Register in the provider registry.
2. Add env vars to `.env.example` with empty defaults so the engine stays disabled until the operator opts in.
3. Add a row to the capability matrix above.
4. If the provider has bespoke parameters, add a parameter schema in `services_app_settings.py` so the UI can render the right form fields.
5. If the provider needs a sidecar container (OSS engines do), drop a `docker-compose.<key>.yml` overlay and document it in [`self-hosting.md`](self-hosting.md).

## Provider parameter schemas

Each provider declares the parameters its synthesis accepts. The frontend reads these via `/v1/settings/schemas` and renders the appropriate form (number sliders, enum dropdowns, etc.) — no per-provider UI code is needed.
