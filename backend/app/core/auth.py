from fastapi import Security, HTTPException, status
from fastapi.security.api_key import APIKeyHeader
from app.core.config import settings

api_key_header = APIKeyHeader(name="X-API-Token", auto_error=False)

async def verify_api_token(api_token: str = Security(api_key_header)):
    if not api_token:
        if settings.api_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing X-API-Token header",
            )
        return "default"
    return api_token
