from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.api.deps import db_session
from app.db.models.pack import PackType
from app.schemas.pack import PackTypeCreate, PackTypeRead 

router = APIRouter(prefix="/pack-types", tags=["Pack Types"])

@router.post("", response_model=PackTypeRead, status_code=status.HTTP_201_CREATED)
def create_pack_type(payload: PackTypeCreate, session: Session = Depends(db_session)) -> PackType:
    existing = session.exec(select(PackType).where(PackType.name == payload.name)).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Pack Type com este nome já existe: '{payload.name}'",
        )
    """
    Cria um novo tipo de pack.
    """
    pack_type = PackType(name = payload.name, sessions_total=payload.sessions_total)
    session.add(pack_type)
    session.commit()
    session.refresh(pack_type)
    return pack_type

@router.get("", response_model=list[PackTypeRead])
def list_pack_types(session: Session = Depends(db_session)) -> list[PackType]:
    """
    Lista todos os tipos de pack.
    """

    stmt = select(PackType).order_by(PackType.name)
    return list(session.exec(stmt).all())

@router.get("/{pack_type_id}", response_model=PackTypeRead)
def get_pack_type(pack_type_id: int, session: Session = Depends(db_session)) -> PackType:
    """
    Obtém um tipo de pack pelo ID.
    """
    pack_type = session.get(PackType, pack_type_id)
    if not pack_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pack Type não encontrado.",
        )
    return pack_type

@router.delete("/{pack_type_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pack_type(pack_type_id: int, session: Session = Depends(db_session)) -> None:
    """
    Elimina um tipo de pack pelo ID.
    """
    pack_type = session.get(PackType, pack_type_id)
    if not pack_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pack Type não encontrado.",
        )
    session.delete(pack_type)
    session.commit()
    return None