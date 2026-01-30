from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.api.deps import db_session
from app.schemas.pack import ClientPackPurchase, ClientPackRead
from app.services.pack_service import PackService

router = APIRouter(prefix="/packs", tags=["packs"])

@router.post("/clients/{client_id}/purchase", response_model=ClientPackRead, status_code=status.HTTP_201_CREATED)
def purchase_pack_for_client(
    client_id: str,
    payload: ClientPackPurchase,
    session: Session = Depends(db_session),
):
    
    """
    Compra um pack para um cliente, com snapshot de sessions_total do pack_type.
    """

    try:
        pack= PackService.purchase_pack(
            session=session,
            client_id=client_id,
            pack_type_id=payload.pack_type_id
        )
        return pack
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))