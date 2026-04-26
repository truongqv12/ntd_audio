# Đóng góp cho ntd_audio

> Song ngữ: Tiếng Việt (file này) · [English](../../CONTRIBUTING.md)

Cảm ơn vì quan tâm đóng góp cho `ntd_audio`. Mục tiêu thiết kế của dự án là **điều phối TTS ưu tiên self-host** — mọi thay đổi nên giữ nguyên trục đó.

Nếu một AI assistant đang trợ giúp, đọc thêm [`AGENTS.md`](../../AGENTS.md). File đó định nghĩa các bất biến nghiêm ngặt mà assistant phải tuân thủ.

## Quickstart

```bash
git clone https://github.com/truongqv12/ntd_audio
cd ntd_audio
cp .env.example .env
docker compose up --build
```

Frontend ở `http://localhost:5173`, API ở `http://localhost:8000` (docs ở `/docs`).

Chi tiết phát triển local không Docker: xem [`development.md`](development.md).

## Cách đóng góp

### Báo bug hoặc đề xuất tính năng

1. Search issue đã có trước.
2. Mở issue mô tả: việc gì xảy ra, mong đợi gì, các bước reproduce, môi trường (OS, Docker version, branch/commit).
3. Đính kèm log từ `docker compose logs api worker` khi liên quan.

### Gửi pull request

1. **Tách branch từ `main`.** Dùng `devin/<timestamp>-<short-topic>` hoặc `feat/<topic>` / `fix/<topic>`.
2. **Một mối quan tâm mỗi PR.** Tách review rẻ hơn nhiều so với tách commit về sau.
3. **Chạy quality gate local** trước khi push:

   ```bash
   # backend
   cd backend
   ruff check src tests
   black --check src tests
   mypy src
   pytest -q

   # frontend
   cd ../frontend
   npm run lint
   npm run typecheck
   npm test
   ```

4. **Commit message** theo Conventional Commits: `feat(api): add /v1/jobs cancel`, `fix(worker): retry on Redis transient`, `docs: ...`, `chore: ...`.
5. **Mở PR.** Điền template — description, ghi chú test, mọi migration / env var thay đổi. Link issue nếu có.
6. **Phản hồi review** trong cùng thread đặt comment. Tránh force-push khi review đang chạy; thêm fixup commit và để maintainer squash khi merge.

### Schema change

Bất cứ thay đổi nào chạm `backend/src/voiceforge/models.py` cần đi kèm Alembic revision:

```bash
make migrate-autogenerate m="add foo column to jobs"
# review file sinh ra trong backend/alembic/versions/
git add backend/alembic/versions/
```

Không dựa vào `create_all`. Nó chỉ chạy ở `APP_ENV=development` / `test`. Xem [`database.md`](database.md) cho workflow migration đầy đủ.

### Thêm provider TTS mới

Adapter provider nằm trong `backend/src/voiceforge/providers/`. Tối thiểu cần document trong [`providers.md`](providers.md). Yêu cầu:

- Adapter implement `synthesize`, `list_voices`, `health`.
- `provider_key` register trong registry.
- Metadata capability (tùy chọn) để UI render đúng form.
- Migration nếu thêm setting persist.

### Thay đổi tài liệu

Tài liệu sống trong hai cây song song:

- `docs/en/` — tiếng Anh, source of truth.
- `docs/vi/` — bản tiếng Việt mirror. Nếu update doc EN, update sibling VI cùng PR (hoặc mở issue follow-up).

Quyết định kiến trúc hoặc thay đổi mà operator cần biết cũng nên ghi vào `CHANGELOG.md`.

## Code style

- **Python:** Black (line length 100), Ruff, Mypy. Xem `backend/pyproject.toml`.
- **TypeScript/React:** ESLint + Prettier với default repo. Xem `frontend/.eslintrc` / `frontend/.prettierrc`.
- **Commit hook** quản lý bởi `pre-commit`. Chạy `pre-commit install` một lần sau clone.

## License

Khi đóng góp, bạn đồng ý đóng góp được cấp phép theo [MIT License](../../LICENSE).
