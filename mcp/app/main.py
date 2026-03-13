from contextlib import asynccontextmanager
from fastapi import FastAPI
from mcp.server import Server
from mcp.server.sse import SseServerTransport

from .auth import ApiKeyMiddleware
from .backend_client import backend
from .resources import register_resources
from .tools import register_tools


mcp_server = Server("homelable")
register_resources(mcp_server)
register_tools(mcp_server)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await backend.start()
    yield
    await backend.stop()


app = FastAPI(title="Homelable MCP", lifespan=lifespan)
app.add_middleware(ApiKeyMiddleware)

sse = SseServerTransport("/mcp/messages")


@app.get("/mcp")
async def mcp_sse(request):
    async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
        await mcp_server.run(streams[0], streams[1], mcp_server.create_initialization_options())


@app.post("/mcp/messages")
async def mcp_messages(request):
    await sse.handle_post_message(request.scope, request.receive, request._send)


@app.get("/health")
async def health():
    return {"status": "ok"}
