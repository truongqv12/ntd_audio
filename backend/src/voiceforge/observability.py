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


# reason → in-flight delta. job_created/job_retried add to the queue;
# terminal transitions remove from it. job_started is a no-op because the job
# was already counted at job_created.
_INFLIGHT_DELTA = {
    "job_created": 1,
    "job_retried": 1,
    "job_succeeded": -1,
    "job_failed": -1,
    "job_canceled": -1,
}


def record_job_event(reason: str, provider_key: str | None = None) -> None:
    jobs_state_transitions_total.labels(reason=reason, provider_key=provider_key or "unknown").inc()
    delta = _INFLIGHT_DELTA.get(reason)
    if delta is None:
        return
    jobs_in_flight.inc(delta)
    # Clamp to ≥ 0. If a terminal event arrives for a job whose creation we
    # never observed (e.g. an old job reaped after a restart), the delta would
    # otherwise drift the gauge negative — meaningless for "in-flight".
    if jobs_in_flight._value.get() < 0:
        jobs_in_flight.set(0)


def seed_jobs_in_flight(count: int) -> None:
    """Seed the in-flight gauge from the DB at startup.

    Without this, a process restart resets the gauge to 0 while jobs still
    sit in the queued/running state in postgres; the next terminal event
    underflows. Called once from the FastAPI lifespan startup hook.
    """
    jobs_in_flight.set(max(0, count))


def render_metrics() -> tuple[bytes, str]:
    return generate_latest(REGISTRY), CONTENT_TYPE_LATEST
