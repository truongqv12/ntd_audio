from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import docker
from docker.errors import DockerException, NotFound
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .config import settings
from .models import SynthesisJob, VoiceCatalogEntry
from .provider_registry import list_providers
from .services_app_settings import apply_provider_settings
from .schemas import (
    LogSourceResponse,
    LogTailResponse,
    MonitorStatusResponse,
    ProviderCapabilitiesResponse,
    ProviderDiagnosticResponse,
    QueueMetricsResponse,
)
from .utils_logs import tail_lines

_APP_STARTED_AT = time.monotonic()


@dataclass(slots=True)
class LogSource:
    key: str
    label: str
    source_type: str
    description: str
    file_path: str | None = None
    compose_service: str | None = None


LOG_SOURCES: list[LogSource] = [
    LogSource("api", "API", "file", "FastAPI application log", file_path="/data/logs/voiceforge-api.log"),
    LogSource("worker", "Worker", "file", "Dramatiq worker log", file_path="/data/logs/voiceforge-worker.log"),
    LogSource("voicevox", "VOICEVOX", "container", "VOICEVOX engine container logs", compose_service="voicevox"),
    LogSource("piper", "Piper", "container", "Piper runtime container logs", compose_service="piper-runtime"),
    LogSource("kokoro", "Kokoro", "container", "Kokoro runtime container logs", compose_service="kokoro-runtime"),
    LogSource("vieneu", "VieNeu-TTS", "container", "VieNeu runtime container logs", compose_service="vieneu-runtime"),
]


def _provider_target(provider: Any) -> str | None:
    if hasattr(provider, "_base_url"):
        try:
            return provider._base_url()
        except Exception:
            pass
    for attr in ("base_url",):
        value = getattr(provider, attr, None)
        if value:
            return str(value)
    return None


def _docker_client() -> docker.DockerClient | None:
    if not settings.monitor_container_logs_enabled:
        return None
    socket_path = Path(settings.monitor_docker_socket_path)
    if not socket_path.exists():
        return None
    try:
        return docker.DockerClient(base_url=f"unix://{socket_path}")
    except DockerException:
        return None


def _find_compose_container(client: docker.DockerClient, service_name: str):
    try:
        containers = client.containers.list(all=True, filters={"label": f"com.docker.compose.service={service_name}"})
    except DockerException:
        return None
    return containers[0] if containers else None


def list_log_sources() -> list[LogSourceResponse]:
    client = _docker_client()
    items: list[LogSourceResponse] = []
    for source in LOG_SOURCES:
        available = False
        if source.source_type == "file":
            available = bool(source.file_path and Path(source.file_path).exists())
        elif source.source_type == "container" and client is not None and source.compose_service:
            available = _find_compose_container(client, source.compose_service) is not None
        items.append(
            LogSourceResponse(
                key=source.key,
                label=source.label,
                source_type=source.source_type,
                available=available,
                description=source.description,
            )
        )
    if client is not None:
        client.close()
    return items


def build_monitor_status(db: Session) -> MonitorStatusResponse:
    apply_provider_settings(db)
    checked_at = datetime.utcnow()
    providers: list[ProviderDiagnosticResponse] = []
    for provider in list_providers():
        started = time.perf_counter()
        reachable, reason = provider.healthcheck()
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        voice_count = db.scalar(
            select(func.count(VoiceCatalogEntry.id)).where(
                VoiceCatalogEntry.provider_key == provider.key,
                VoiceCatalogEntry.is_active.is_(True),
            )
        ) or 0
        active_jobs = db.scalar(
            select(func.count(SynthesisJob.id)).where(
                SynthesisJob.provider_key == provider.key,
                SynthesisJob.status.in_(["queued", "running"]),
            )
        ) or 0
        providers.append(
            ProviderDiagnosticResponse(
                key=provider.key,
                label=provider.label,
                category=provider.category,
                configured=provider.is_configured(),
                reachable=reachable,
                reason=reason,
                latency_ms=latency_ms,
                checked_at=checked_at,
                voice_count=int(voice_count),
                active_jobs=int(active_jobs),
                service_target=_provider_target(provider),
                capabilities=ProviderCapabilitiesResponse(**provider.capabilities.to_dict()),
            )
        )

    queued = db.scalar(select(func.count(SynthesisJob.id)).where(SynthesisJob.status == "queued")) or 0
    running = db.scalar(select(func.count(SynthesisJob.id)).where(SynthesisJob.status == "running")) or 0
    failed = db.scalar(select(func.count(SynthesisJob.id)).where(SynthesisJob.status == "failed")) or 0
    succeeded = db.scalar(select(func.count(SynthesisJob.id)).where(SynthesisJob.status == "succeeded")) or 0
    total = db.scalar(select(func.count(SynthesisJob.id))) or 0

    guidance = [
        "Use the Monitor page to compare API/worker logs with engine container logs before blaming the provider adapter.",
        "For self-host operation, keep engine runtimes isolated and monitor per-engine voice count, latency, and container health.",
        "For future public hosting, split control-plane API from engine workers and add per-project quotas, storage offload, and centralized logs/metrics.",
    ]

    return MonitorStatusResponse(
        app_name=settings.app_name,
        checked_at=checked_at,
        uptime_seconds=round(time.monotonic() - _APP_STARTED_AT, 2),
        queue=QueueMetricsResponse(
            queued_jobs=int(queued),
            running_jobs=int(running),
            failed_jobs=int(failed),
            succeeded_jobs=int(succeeded),
            total_jobs=int(total),
        ),
        providers=providers,
        guidance=guidance,
    )


def _read_container_log(source: LogSource, limit: int) -> list[str]:
    client = _docker_client()
    if client is None or not source.compose_service:
        return []
    try:
        container = _find_compose_container(client, source.compose_service)
        if container is None:
            return []
        raw = container.logs(tail=limit).decode("utf-8", errors="replace")
        return raw.splitlines()
    except (DockerException, NotFound):
        return []
    finally:
        try:
            client.close()
        except Exception:
            pass


def read_log_tail(source_key: str = "api", limit: int = 200) -> LogTailResponse:
    source = next((item for item in LOG_SOURCES if item.key == source_key), None)
    if source is None:
        source = LOG_SOURCES[0]

    if source.source_type == "file":
        lines = tail_lines(source.file_path or settings.log_file_path, limit=limit)
        return LogTailResponse(
            source=source.key,
            source_label=source.label,
            source_type=source.source_type,
            file_path=source.file_path,
            lines=lines,
        )

    lines = _read_container_log(source, limit)
    return LogTailResponse(
        source=source.key,
        source_label=source.label,
        source_type=source.source_type,
        file_path=None,
        lines=lines,
    )
