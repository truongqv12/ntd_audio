# Tài liệu

> Tiếng Việt · [English](README.md)

Tài liệu cho `ntd_audio`, được tổ chức thành hai cây song song:

- [`en/`](en/) — tiếng Anh (bản gốc).
- [`vi/`](vi/) — bản tiếng Việt.

## Đọc trước

Nếu là **AI agent**, các quy tắc và bất biến nằm trong [`../AGENTS.md`](../AGENTS.md).

Nếu là **người đọc**, bắt đầu từ [`../README.vi.md`](../README.vi.md).

## Chủ đề

| Chủ đề | English | Tiếng Việt |
|---|---|---|
| Kiến trúc | [`en/architecture.md`](en/architecture.md) | [`vi/architecture.md`](vi/architecture.md) |
| Self-hosting | [`en/self-hosting.md`](en/self-hosting.md) | [`vi/self-hosting.md`](vi/self-hosting.md) |
| Vận hành | [`en/operations.md`](en/operations.md) | [`vi/operations.md`](vi/operations.md) |
| Database | [`en/database.md`](en/database.md) | [`vi/database.md`](vi/database.md) |
| HTTP API | [`en/api.md`](en/api.md) | [`vi/api.md`](vi/api.md) |
| Engine | [`en/providers.md`](en/providers.md) | [`vi/providers.md`](vi/providers.md) |
| Phát triển | [`en/development.md`](en/development.md) | [`vi/development.md`](vi/development.md) |
| Bản đồ tính năng | [`en/feature-map.md`](en/feature-map.md) | [`vi/feature-map.md`](vi/feature-map.md) |
| Tối ưu & roadmap | [`en/optimization-and-roadmap.md`](en/optimization-and-roadmap.md) | [`vi/optimization-and-roadmap.md`](vi/optimization-and-roadmap.md) |
| Design system | [`en/design-system.md`](en/design-system.md) | [`vi/design-system.md`](vi/design-system.md) |
| Đóng góp | [`../CONTRIBUTING.md`](../CONTRIBUTING.md) | [`vi/contributing.md`](vi/contributing.md) |
| Bảo mật | [`../SECURITY.md`](../SECURITY.md) | [`vi/security.md`](vi/security.md) |

## Đóng góp tài liệu

1. Cập nhật bản tiếng Anh trong `en/` trước.
2. Cập nhật bản mirror tiếng Việt trong `vi/` trong cùng PR. Nếu chưa kịp dịch, thêm file với placeholder "TODO: dịch" và liên kết tới bản tiếng Anh.
3. Các thay đổi về kiến trúc mà người vận hành cần biết cũng nên ghi vào [`../CHANGELOG.md`](../CHANGELOG.md).

## Phong cách

- Mỗi doc bắt đầu bằng hai khối ngắn: `For AI agents:` và `For humans:` (giữ tiêu đề tiếng Anh để đồng nhất với bản EN, nội dung viết tiếng Việt).
- TL;DR dưới 5 gạch đầu dòng, rồi đến các phần chi tiết.
- Dùng Mermaid cho diagram; không nhúng ảnh cho thứ có thể viết bằng code.
- Dẫn dắt bằng việc người đọc thực sự cần làm. Lý thuyết chỉ giải thích khi nó thay đổi quyết định.
