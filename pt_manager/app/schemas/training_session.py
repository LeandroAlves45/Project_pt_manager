from typing import Optional
from pydantic import Field
from sqlmodel import SQLModel

class TrainingSessionCreate(SQLModel):
    """
    Agendar uma sessão de treino individual.
    """

    starts_at: str = Field(min_length = 10) #ISO UTC datetime string
    duration_minutes: int = Field(ge=15, le=240)
    location: Optional[str] = Field(default=None, max_length=200)
    notes: Optional[str] = Field(default=None)

class TrainingSessionRead(SQLModel):
    id: str
    client_id: str
    starts_at: str
    duration_minutes: int
    location: Optional[str]
    notes: Optional[str]
    status: str
    created_at: str
    updated_at: str