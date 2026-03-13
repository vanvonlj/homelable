import hmac

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings
from app.core.security import decode_token

bearer = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    x_mcp_service_key: str | None = Header(default=None),
) -> str:
    # 1. MCP service key (Docker-internal only — backend port is not externally exposed)
    if x_mcp_service_key is not None:
        if not settings.mcp_service_key:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="MCP service key not configured")
        if not hmac.compare_digest(x_mcp_service_key.encode(), settings.mcp_service_key.encode()):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid MCP service key")
        return "__mcp_service__"

    # 2. Standard JWT bearer token
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    username = decode_token(credentials.credentials)
    if not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return username
