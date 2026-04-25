# Chính sách bảo mật

## Báo cáo lỗ hổng

> **Đừng mở issue GitHub công khai cho báo cáo bảo mật.**

Vui lòng email **truongqv13@gmail.com** kèm:

- Mô tả lỗ hổng.
- Bước reproduce, kèm version/commit nếu có thể.
- Tác động bạn quan sát hoặc dự kiến.
- Thông tin liên hệ để follow-up.

Maintainer sẽ xác nhận trong **5 ngày làm việc** và cố gắng đưa kế hoạch khắc phục trong **30 ngày** cho báo cáo hợp lệ. Ưu tiên coordinated disclosure — vui lòng không công khai chi tiết cho đến khi bản fix được phát hành.

## Phạm vi

Trong phạm vi:

- Service FastAPI `backend/` và các handler.
- Worker Dramatiq (`backend/src/voiceforge/tasks.py`).
- App React `frontend/`.
- Cấu hình `docker-compose*.yml` mặc định ship từ repo.
- Script migration trong `backend/alembic/`.

Ngoài phạm vi:

- Service TTS bên thứ ba (OpenAI, ElevenLabs, Google Cloud TTS, Azure Speech, ...). Báo upstream.
- Image OSS engine bundled (`voicevox`, `piper`, `kokoro`, `vieneu`). Cũng báo upstream.
- Lỗ hổng cần admin malicious đã auth `APP_API_KEYS`, trừ leo thang đặc quyền giữa workspace.
- DoS qua synthesis hợp pháp nhưng tốn — rate limit (`RATE_LIMIT_PER_MINUTE`) là trách nhiệm operator.

## Kỳ vọng hardening cho operator self-host

Default trong `docker-compose.yml` là **cho local dev**. Trước khi phơi instance ra Internet:

1. Apply `docker-compose.prod.yml` — bỏ binding port host của Postgres/Redis và bỏ mount Docker socket.
2. Set `APP_API_KEYS` thành CSV không rỗng. Không có nó, mọi route trừ `/health` đều mở.
3. Set `APP_ENCRYPTION_KEY` (32-byte URL-safe base64 Fernet). Không thì secret provider trong DB lưu plaintext.
4. Set `APP_ALLOWED_ORIGINS` là origin frontend thật. Default rỗng tắt CORS wildcard.
5. Set `RATE_LIMIT_PER_MINUTE` theo quota provider của bạn.
6. Bật HTTPS ở reverse proxy. Cấu hình nginx trong `frontend/nginx.conf` là điểm khởi đầu, không phải production hardened — terminate TLS phía trước nó.
7. Restrict `/metrics` (khi `METRICS_ENABLED=true`) ở proxy. Endpoint không auth có chủ ý cho Prometheus scrape.

Xem [`self-hosting.md`](self-hosting.md) cho checklist production đầy đủ.

## Version được hỗ trợ

Chỉ `main` được hỗ trợ. Tagged release nhận backport security khi báo cáo land trong cùng minor version.
