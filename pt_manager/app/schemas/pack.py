from typing import Optional
from pydantic import Field
from sqlmodel import SQLModel

class PackTypeCreate(SQLModel):
    """
    Payload para criação de um novo tipo de pacote.
    """

    name: str = Field(min_length=1, max_length=100)
    session_total: int = Field(ge=1, le=500)

class PackTypeRead(SQLModel):
    """
    Schema para leitura de dados do tipo de pacote.
    usado em respostas de API
    """

    id: int
    name: str
    session_total: int
    created_at: str
    updated_at: str

class ClientPackPurchase(SQLModel):
    """
        Compra de pack para um cliente:
        -escolhe o pack_type_id 
     """

    pack_type_id: str
    purchase_date: Optional[str] = None  #data da compra, se não for fornecida, usa a data atual


class ClientPackRead(SQLModel):
    """
    Schema para leitura de dados do pack do cliente.
    usado em respostas de API
    """

    id: int
    client_id: str
    pack_type_id: str
    purchase_date: str
    sessions_total: int
    sessions_used: int
    canceled_at: Optional[str] = None
    archived_at: Optional[str] = None
    created_at: str
    updated_at: str