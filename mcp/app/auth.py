import hmac
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from .config import settings


class ApiKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Health check bypass
        if request.url.path == "/health":
            return await call_next(request)

        key = request.headers.get("X-API-Key", "")
        expected = settings.mcp_api_key

        if not key or not hmac.compare_digest(key.encode(), expected.encode()):
            return JSONResponse({"detail": "Invalid or missing X-API-Key"}, status_code=401)

        return await call_next(request)
