from app.core.security import require_api_key 

import uuid
from typing import Optional

from sqlmodel import Field, SQLModel

class TrainingSession (SQLModel, table = True):
    """
    Aulas / sessões de treino individuais.

    Status:
    - scheduled: agendada
    - completed: concluída
    - canceled: cancelada
    -no-show: não compareceu
    """

    __tablename__ = "sessions"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True, index=True)
    client_id: str = Field(index = True, foreign_key="clients.id")

    starts_at: str = Field(index =True)
    duration_minutes: int = Field(ge=15, le=240)

    location: Optional[str] = Field(default=None, max_length=200)
    notes: Optional[str] = Field(default=None)

    status: str = Field(default="scheduled", index=True, max_length=20)
    created_at: str = Field(default_factory=lambda: _utc_now_iso())
    updated_at: str = Field(default_factory=lambda: _utc_now_iso())

class PackConsumption(SQLModel, table=True):
    """
    Registo de consumo de packs por sessões de treino.
    """

    __tablename__ = "pack_consumptions"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True, index=True)
    session_id: str = Field(index=True, foreign_key="sessions.id")
    client_pack_id: str = Field(index=True, foreign_key="client_packs.id")

    created_at: str = Field(default_factory=lambda: _utc_now_iso())

def _utc_now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()