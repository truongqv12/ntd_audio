"""Prometheus metrics surface (Epic 4).

Exposes ``/metrics`` (Prometheus text format) when ``METRICS_ENABLED`` is true.
We track the metrics that matter for SRE-on-call: HTTP request rate / latency,
job state counters, queue depth gauge. Other modules call ``record_job_event``
on state transitions.
"""

from __future__ import annotations

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

REGISTRY = CollectorRegistry(auto_describe=True)

http_requests_total = Counter(
    "voiceforge_http_requests_total",
    "Total HTTP requests handled.",
    labelnames=("method", "path_template", "status"),
    registry=REGISTRY,
)

http_request_duration_seconds = Histogram(
    "voiceforge_http_request_duration_seconds",
    "HTTP request duration in seconds.",
    labelnames=("method", "path_template"),
    buckets=(0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    registry=REGISTRY,
)

jobs_state_transitions_total = Counter(
    "voiceforge_jobs_state_transitions_total",
    "Job state transitions (queued/running/succeeded/failed/canceled/retried).",
    labelnames=("reason", "provider_key"),
    registry=REGISTRY,
)

jobs_in_flight = Gauge(
    "voiceforge_jobs_in_flight",
    "Jobs currently in queued or running state.",
    registry=REGISTRY,
)


def record_http(method: str, path_template: str, status: int, duration_seconds: float) -> None:
    http_requests_total.labels(method=method, path_template=path_template, status=str(status)).inc()
    http_request_duration_seconds.labels(method=method, path_template=path_template).observe(duration_seconds)


def record_job_event(reason: str, provider_key: str | None = None) -> None:
    jobs_state_transitions_total.labels(reason=reason, provider_key=provider_key or "unknown").inc()


def render_metrics() -> tuple[bytes, str]:
    return generate_latest(REGISTRY), CONTENT_TYPE_LATEST
