"""Authentication helpers."""
from fastapi import Header, HTTPException

from app.config import settings


def verify_api_key(x_api_key: str | None = Header(default=None)) -> str:
    """Validate X-API-Key header and return key for downstream usage."""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing API key. Include header: X-API-Key")
    if x_api_key != settings.agent_api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key
