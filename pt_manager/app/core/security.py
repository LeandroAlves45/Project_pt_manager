from fastapi import Header, HTTPException, status

from app.core.config import settings

def require_api_key(x_api_key: str = Header(default=None, alias="X-API-Key")) -> None:
    """
        Valida  API Key enviada no header X-API-Key.  
    """

    if not settings.api_key:

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API key não configurada no servidor.",
        )

    if x_api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key inválida.",
        )