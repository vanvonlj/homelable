import json
from mcp.server import Server
from mcp.types import Tool, TextContent
from .backend_client import backend


def register_tools(server: Server):

    @server.list_tools()
    async def list_tools():
        return [
            Tool(name="create_node", description="Add a new node to the homelab canvas", inputSchema={
                "type": "object",
                "required": ["type", "label"],
                "properties": {
                    "type":     {"type": "string", "enum": ["isp","router","switch","server","proxmox","vm","lxc","nas","iot","ap","generic"]},
                    "label":    {"type": "string"},
                    "ip":       {"type": "string"},
                    "hostname": {"type": "string"},
                    "status":   {"type": "string", "enum": ["online","offline","unknown","pending"], "default": "unknown"},
                },
            }),
            Tool(name="update_node", description="Update an existing node", inputSchema={
                "type": "object",
                "required": ["id"],
                "properties": {
                    "id":       {"type": "string"},
                    "label":    {"type": "string"},
                    "ip":       {"type": "string"},
                    "hostname": {"type": "string"},
                    "status":   {"type": "string"},
                },
            }),
            Tool(name="delete_node", description="Delete a node from the canvas", inputSchema={
                "type": "object",
                "required": ["id"],
                "properties": {"id": {"type": "string"}},
            }),
            Tool(name="create_edge", description="Create a network link between two nodes", inputSchema={
                "type": "object",
                "required": ["source", "target"],
                "properties": {
                    "source": {"type": "string"},
                    "target": {"type": "string"},
                    "type":   {"type": "string", "enum": ["ethernet","wifi","iot","vlan","virtual"], "default": "ethernet"},
                    "label":  {"type": "string"},
                },
            }),
            Tool(name="delete_edge", description="Delete a network link", inputSchema={
                "type": "object",
                "required": ["id"],
                "properties": {"id": {"type": "string"}},
            }),
            Tool(name="trigger_scan", description="Trigger a network discovery scan", inputSchema={
                "type": "object",
                "properties": {
                    "ranges": {"type": "array", "items": {"type": "string"}, "description": "CIDR ranges to scan (uses configured defaults if omitted)"},
                },
            }),
            Tool(name="approve_device", description="Approve a pending discovered device and create a node", inputSchema={
                "type": "object",
                "required": ["id"],
                "properties": {
                    "id":    {"type": "string"},
                    "type":  {"type": "string", "enum": ["isp","router","switch","server","proxmox","vm","lxc","nas","iot","ap","generic"], "default": "generic"},
                    "label": {"type": "string"},
                },
            }),
            Tool(name="hide_device", description="Hide a pending discovered device", inputSchema={
                "type": "object",
                "required": ["id"],
                "properties": {"id": {"type": "string"}},
            }),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        result = await _dispatch(name, arguments)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def _dispatch(name: str, args: dict) -> dict:
    if name == "create_node":
        return await backend.post("/api/v1/nodes", args)

    if name == "update_node":
        node_id = args.pop("id")
        return await backend.patch(f"/api/v1/nodes/{node_id}", args)

    if name == "delete_node":
        return await backend.delete(f"/api/v1/nodes/{args['id']}")

    if name == "create_edge":
        return await backend.post("/api/v1/edges", args)

    if name == "delete_edge":
        return await backend.delete(f"/api/v1/edges/{args['id']}")

    if name == "trigger_scan":
        body = {"ranges": args["ranges"]} if "ranges" in args else {}
        return await backend.post("/api/v1/scan/trigger", body)

    if name == "approve_device":
        device_id = args.pop("id")
        return await backend.post(f"/api/v1/scan/pending/{device_id}/approve", args)

    if name == "hide_device":
        return await backend.post(f"/api/v1/scan/pending/{args['id']}/hide", {})

    raise ValueError(f"Unknown tool: {name}")
