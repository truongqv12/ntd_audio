"""Optional API-key authentication.

When ``APP_API_KEYS`` is non-empty, every request that goes through a
router protected with ``Depends(require_api_key)`` must present a matching
``X-API-Key`` header. When the list is empty (default), the dependency is a
no-op so single-user / local-dev installs keep working unchanged.

The health endpoint stays public on purpose — it's used by Docker
healthchecks and load balancers.
"""

from __future__ import annotations

from fastapi import Header, HTTPException, Query, status

from ..config import settings


def _allowed_keys() -> set[str]:
    return {key.strip() for key in settings.app_api_keys if key and key.strip()}


def require_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    api_key: str | None = Query(default=None, alias="api_key"),
) -> None:
    keys = _allowed_keys()
    if not keys:
        return
    presented = x_api_key or api_key
    if not presented or presented not in keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid X-API-Key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
