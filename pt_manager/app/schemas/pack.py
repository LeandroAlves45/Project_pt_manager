from typing import Optional
from sqlmodel import SQLModel, Field

# =========================
# Client Pack (purchase)
# =========================

class ClientPackPurchase(SQLModel):
    """
        Compra de pack para um cliente:
        -escolhe o pack_type_id 
     """

    pack_type_id: str
    purchase_at: Optional[str] = None  #data da compra, se não for fornecida, usa a data atual


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

