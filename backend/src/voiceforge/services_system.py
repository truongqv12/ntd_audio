"""Host capability probe (T2.6).

Detects whether the API container has access to an NVIDIA GPU (via `nvidia-smi`)
and reports basic CPU info. The result is cached for the lifetime of the
process — capabilities don't change without a container restart.

Output is intentionally a flat dict so the frontend Settings → Host tab can
render it directly without a typed schema.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass


@dataclass(slots=True)
class GpuInfo:
    vendor: str
    name: str
    vram_mb: int


@dataclass(slots=True)
class CpuInfo:
    cores: int
    threads: int


@dataclass(slots=True)
class HostCapabilities:
    gpu: GpuInfo | None
    cpu: CpuInfo
    recommended_overlays: list[str]


_NVIDIA_QUERY = ["--query-gpu=name,memory.total", "--format=csv,noheader,nounits"]


def _probe_nvidia() -> GpuInfo | None:
    binary = shutil.which("nvidia-smi")
    if binary is None:
        return None
    try:
        proc = subprocess.run(
            [binary, *_NVIDIA_QUERY],
            check=False,
            capture_output=True,
            text=True,
            timeout=2.0,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None
    if proc.returncode != 0:
        return None
    line = proc.stdout.strip().splitlines()
    if not line:
        return None
    parts = [p.strip() for p in line[0].split(",")]
    if len(parts) < 2:
        return None
    name = parts[0]
    try:
        vram_mb = int(parts[1])
    except ValueError:
        vram_mb = 0
    return GpuInfo(vendor="nvidia", name=name, vram_mb=vram_mb)


def _probe_cpu() -> CpuInfo:
    threads = os.cpu_count() or 1
    cores = threads
    try:
        # On Linux, sched_getaffinity is the most accurate when running in a
        # cgroup (Docker), so prefer it when available.
        if hasattr(os, "sched_getaffinity"):
            cores = max(1, len(os.sched_getaffinity(0)))
    except OSError:
        pass
    return CpuInfo(cores=cores, threads=threads)


def _recommend_overlays(gpu: GpuInfo | None) -> list[str]:
    if gpu is None:
        return []
    return ["docker-compose.gpu.yml"]


_cached: HostCapabilities | None = None


def get_host_capabilities(force_refresh: bool = False) -> HostCapabilities:
    global _cached
    if _cached is not None and not force_refresh:
        return _cached
    gpu = _probe_nvidia()
    cpu = _probe_cpu()
    _cached = HostCapabilities(
        gpu=gpu,
        cpu=cpu,
        recommended_overlays=_recommend_overlays(gpu),
    )
    return _cached


def reset_for_tests() -> None:
    """Clear cached probe. Test-only helper."""
    global _cached
    _cached = None


def to_dict(caps: HostCapabilities) -> dict:
    return {
        "gpu": (
            None
            if caps.gpu is None
            else {"vendor": caps.gpu.vendor, "name": caps.gpu.name, "vram_mb": caps.gpu.vram_mb}
        ),
        "cpu": {"cores": caps.cpu.cores, "threads": caps.cpu.threads},
        "recommended_overlays": list(caps.recommended_overlays),
    }
