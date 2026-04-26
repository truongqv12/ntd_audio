# Documentation

> [Tiếng Việt](README.vi.md) · English

Documentation for `ntd_audio`, organized into two parallel trees:

- [`en/`](en/) — English (source of truth).
- [`vi/`](vi/) — Vietnamese mirror.

## Read this first

If you are an **AI agent**, the rules and invariants are in [`../AGENTS.md`](../AGENTS.md).

If you are a **human**, start with the root [`../README.md`](../README.md).

## Topics

| Topic | English | Tiếng Việt |
|---|---|---|
| Architecture | [`en/architecture.md`](en/architecture.md) | [`vi/architecture.md`](vi/architecture.md) |
| Self-hosting | [`en/self-hosting.md`](en/self-hosting.md) | [`vi/self-hosting.md`](vi/self-hosting.md) |
| Operations | [`en/operations.md`](en/operations.md) | [`vi/operations.md`](vi/operations.md) |
| Database | [`en/database.md`](en/database.md) | [`vi/database.md`](vi/database.md) |
| HTTP API | [`en/api.md`](en/api.md) | [`vi/api.md`](vi/api.md) |
| Providers | [`en/providers.md`](en/providers.md) | [`vi/providers.md`](vi/providers.md) |
| Development | [`en/development.md`](en/development.md) | [`vi/development.md`](vi/development.md) |
| Feature map | [`en/feature-map.md`](en/feature-map.md) | [`vi/feature-map.md`](vi/feature-map.md) |
| Optimization & roadmap | [`en/optimization-and-roadmap.md`](en/optimization-and-roadmap.md) | [`vi/optimization-and-roadmap.md`](vi/optimization-and-roadmap.md) |
| Design system | [`en/design-system.md`](en/design-system.md) | [`vi/design-system.md`](vi/design-system.md) |
| Contributing | [`../CONTRIBUTING.md`](../CONTRIBUTING.md) | [`vi/contributing.md`](vi/contributing.md) |
| Security | [`../SECURITY.md`](../SECURITY.md) | [`vi/security.md`](vi/security.md) |

## Contributing to docs

1. Update the English source first under `en/`.
2. Update the Vietnamese mirror under `vi/` in the same PR. If you can't translate yet, add the file with a "TODO: dịch" placeholder and link the English version.
3. Architectural changes that operators must know about also belong in [`../CHANGELOG.md`](../CHANGELOG.md).

## Style

- Each doc starts with two short callouts: `For AI agents:` and `For humans:`.
- TL;DR section under 5 bullets, then detailed sections.
- Mermaid for diagrams; do not embed images for things expressible as code.
- Lead with what the reader actually does. Theory only when it changes a decision.
