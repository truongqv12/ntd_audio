# Architecture

## Mục tiêu của bản này

Bản này tập trung giải quyết khoảng cách giữa:
- **UI / orchestration app**
- và **engine runtimes thật**

Thay vì để adapter gọi sample contract mơ hồ, hệ thống được đổi sang mô hình:

```text
Frontend
  -> API
      -> PostgreSQL / Redis
      -> Worker
          -> provider registry
              -> cloud APIs
              -> self-hosted runtimes thật
```

## Runtimes thật đã được đóng vào repo

### VOICEVOX
- engine độc lập qua Docker image chính thức
- backend gọi HTTP API `/speakers`, `/audio_query`, `/synthesis`

### Piper
- runtime riêng: `engines/piper-runtime`
- dùng package `piper-tts`
- dùng command chính thức `python -m piper.download_voices` để tải voice
- synthesize qua `python -m piper`

### Kokoro
- runtime riêng: `engines/kokoro-runtime`
- dùng official `kokoro` inference library
- synthesize qua `KPipeline`
- API wrapper tự đóng gói thành service HTTP để backend gọi ổn định

### VieNeu-TTS
- runtime riêng: `engines/vieneu-runtime`
- dùng official `vieneu` SDK
- local Turbo mode để ưu tiên thực dụng cho local/self-host trước
- API wrapper tự đóng gói thành service HTTP

## Vì sao tách engine thành runtime service riêng

Lý do chính:
1. tránh nhồi toàn bộ dependency nặng vào `api` và `worker`
2. giữ backend orchestration sạch hơn
3. mỗi engine có lifecycle và dependency riêng
4. dễ bật/tắt bằng Docker Compose overrides
5. sau này scale riêng CPU/GPU workers dễ hơn

## SSE strategy

Backend có route SSE dạng polling snapshot:
- `GET /events/stream`

Cách này chưa phải event bus tinh vi nhất, nhưng đủ để:
- tránh phải F5 thủ công
- giữ frontend sync với job state
- dễ maintain hơn WebSocket ở giai đoạn này

## Project management strategy

Project là lớp tổ chức workflow cốt lõi:
- job luôn gắn với project
- project mang default settings
- project là điểm mở rộng cho presets / favorites / storage segregation / metrics

Định hướng này phù hợp hơn nhiều so với việc coi project chỉ là một label mỏng.

## Điều đã sửa ở orchestration layer

### Cache key
Cache key giờ phải tính cả `output_format`, tránh reuse sai artifact giữa `wav` và `mp3`.

### Provider health
Provider health giờ phản ánh runtime thật:
- nếu runtime service không lên -> provider unreachable
- nếu runtime có voices thực tế -> catalog sync được

## Hướng phát triển tiếp

### gần hạn
- live progress event granularity tốt hơn
- cancel/retry jobs
- upload reference audio cho cloning flows
- presets theo project

### trung hạn
- S3/MinIO artifact storage
- per-project provider routing
- benchmark & cost telemetry
- project/workspace RBAC
