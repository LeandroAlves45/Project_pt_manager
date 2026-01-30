from pydantic import Field
from sqlmodel import SQLModel

class PackTypeCreate(SQLModel):
    name: str = Field(min_lenght = 1, max_length=100)
    sessions_total: int = Field(ge=1, le=100)


class PackTypeRead(SQLModel):
    id: int
    name: str
    sessions_total: int
    created_at: str
    updated_at: str
    