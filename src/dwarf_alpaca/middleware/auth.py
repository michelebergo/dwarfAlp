from __future__ import annotations

import hmac

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = structlog.get_logger(__name__)

# Paths that bypass authentication (health check for external monitoring).
_PUBLIC_PATHS: set[str] = {"/management/health"}


class ApiKeyMiddleware(BaseHTTPMiddleware):
    """Validates an API key sent via header or query parameter."""

    def __init__(self, app, *, api_key: str, header_name: str = "X-API-Key") -> None:
        super().__init__(app)
        self._api_key = api_key
        self._header_name = header_name

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        if request.url.path in _PUBLIC_PATHS:
            return await call_next(request)

        supplied = request.headers.get(self._header_name) or request.query_params.get("api_key")

        if not supplied or not hmac.compare_digest(supplied, self._api_key):
            logger.warning(
                "auth.rejected",
                path=request.url.path,
                method=request.method,
                reason="missing_or_invalid_api_key",
            )
            return JSONResponse(
                status_code=401,
                content={
                    "ErrorNumber": 1401,
                    "ErrorMessage": "Unauthorized – invalid or missing API key",
                },
            )

        return await call_next(request)
