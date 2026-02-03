from typing import Optional
from datetime import datetime
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
    purchase_at: Optional[datetime] = None  #data da compra, se não for fornecida, usa a data atual


class ClientPackRead(SQLModel):
    """
    Schema para leitura de dados do pack do cliente.
    usado em respostas de API
    """

    id: str
    client_id: str
    client_name: Optional[str] = None
    pack_type_id: str
    purchase_at: datetime
    sessions_total_snapshot: int
    sessions_used: int
    cancelled_at: Optional[datetime] = None
    archived_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

