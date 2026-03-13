import httpx
from .config import settings


class BackendClient:
    def __init__(self):
        self._client: httpx.AsyncClient | None = None

    async def start(self):
        self._client = httpx.AsyncClient(
            base_url=settings.backend_url,
            headers={"X-MCP-Service-Key": settings.mcp_service_key},
            timeout=30.0,
        )

    async def stop(self):
        if self._client:
            await self._client.aclose()

    async def request(self, method: str, path: str, **kwargs) -> dict:
        resp = await self._client.request(method, path, **kwargs)
        resp.raise_for_status()
        if resp.status_code == 204:
            return {}
        return resp.json()

    async def get(self, path: str) -> dict | list:
        return await self.request("GET", path)

    async def post(self, path: str, body: dict) -> dict:
        return await self.request("POST", path, json=body)

    async def patch(self, path: str, body: dict) -> dict:
        return await self.request("PATCH", path, json=body)

    async def delete(self, path: str) -> dict:
        return await self.request("DELETE", path)


backend = BackendClient()
