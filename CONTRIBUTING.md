# Contributing to ntd_audio

> **Bilingual:** [Tiếng Việt](docs/vi/contributing.md) · English (this file)

Thanks for your interest in contributing to `ntd_audio`. The project's design goal is **self-host-first TTS orchestration** — every change should keep that intact.

If an AI assistant is helping you, also read [`AGENTS.md`](AGENTS.md). It captures stricter invariants the assistant must follow.

## Quick start

```bash
git clone https://github.com/truongqv12/ntd_audio
cd ntd_audio
cp .env.example .env
docker compose up --build
```

The frontend serves at `http://localhost:5173`, the API at `http://localhost:8000` (docs at `/docs`).

For full local development without Docker, see [`docs/en/development.md`](docs/en/development.md).

## How to contribute

### Reporting a bug or proposing a feature

1. Search existing issues first.
2. Open an issue describing what happened, what you expected, the steps to reproduce, and your environment (OS, Docker version, branch/commit).
3. Include logs from `docker compose logs api worker` when relevant.

### Submitting a pull request

1. **Branch from `main`.** Use `devin/<timestamp>-<short-topic>` or `feat/<topic>` / `fix/<topic>`.
2. **One concern per PR.** Splitting reviews is much cheaper than splitting commits later.
3. **Run quality gates locally** before pushing:

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

4. **Commit messages** follow Conventional Commits: `feat(api): add /v1/jobs cancel`, `fix(worker): retry on Redis transient`, `docs: ...`, `chore: ...`.
5. **Open the PR.** Fill the template — description, testing notes, and any migrations or env-var changes. Link the issue if there is one.
6. **Address reviews** in the threads where they were raised. Avoid force-pushing once review is in progress; add fixup commits and let the maintainer squash on merge.

### Schema changes

Anything that touches `backend/src/voiceforge/models.py` needs an accompanying Alembic revision:

```bash
make migrate-autogenerate m="add foo column to jobs"
# review the generated file under backend/alembic/versions/
git add backend/alembic/versions/
```

Do not rely on `create_all`. It only runs in `APP_ENV=development` / `test`. See [`docs/en/database.md`](docs/en/database.md) for the full migration workflow.

### Adding a new TTS provider

Provider adapters live under `backend/src/voiceforge/providers/`. The minimum surface is documented in [`docs/en/providers.md`](docs/en/providers.md). Required items:

- An adapter implementing `synthesize`, `list_voices`, and `health`.
- A `provider_key` registered in the registry.
- Optional capability metadata so the UI can show the right form fields.
- A migration if you introduce a new persisted setting.

### Documentation changes

Documentation lives in two parallel trees:

- `docs/en/` — English source of truth.
- `docs/vi/` — Vietnamese mirror. If you update an English doc, update the Vietnamese sibling in the same PR (or open a follow-up issue).

Architectural decisions or changes that operators need to know about should also land in `CHANGELOG.md`.

## Code style

- **Python:** Black (line length 100), Ruff, Mypy. See `backend/pyproject.toml`.
- **TypeScript/React:** ESLint + Prettier with the repo defaults. See `frontend/.eslintrc` / `frontend/.prettierrc`.
- **Commit hooks** are managed by `pre-commit`. Run `pre-commit install` once after cloning.

## License

By contributing, you agree your contribution is licensed under the [MIT License](LICENSE).
