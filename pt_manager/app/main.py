from fastapi import FastAPI
from app.core.security import require_api_key
from fastapi import Depends

#importa a função de inicialização do banco de dados(criação de tabelas)
from app.db.init_db import init_db  
from app.api.v1.clients import router as clients_router
from app.api.v1.packs import router as packs_router
from app.api.v1.pack_types import router as pack_types_router
from app.api.v1.sessions import router as sessions_router

app = FastAPI(
    title="PT Manager API",
    version= "0.1.0",
)

@app.on_event("startup")
def on_startup() -> None:
    """
    Hook de statup do FastAPI.
    -Garante que a BD/tabelas existam
    -Em produção, trocariamos isto por migração (Alembic)
    """
    init_db()

@app.get("/")
def root() -> dict:
    """
    Rota raiz para evitar 404 no browser.
    """
    return {"message": "PT Manager API", "docs": "/docs", "health": "/health"}

@app.get("/health", tags=["health"])
def health_check() -> dict:
    """
    Endpoint simples para verificar se a app está de pé
    """
    return {"status": "ok"}


#Protege todas as rotas 
common_depedencies = [Depends(require_api_key)]
#versão da API (V1)
app.include_router(clients_router, prefix="/api/v1", dependencies=[Depends(require_api_key)])
app.include_router(packs_router, prefix="/api/v1", dependencies=[Depends(require_api_key)])
app.include_router(pack_types_router, prefix="/api/v1", dependencies=[Depends(require_api_key)])
app.include_router(sessions_router, prefix="/api/v1", dependencies=[Depends(require_api_key)])
