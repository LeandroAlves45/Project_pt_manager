from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.api.deps import db_session
from app.db.models.session import TrainingSession
from app.schemas.training_session import TrainingSessionCreate, TrainingSessionRead
from app.services.session_service import SessionService

router = APIRouter(prefix="/sessions", tags=["Sessions"])

@router.post("/clients/{client_id}", response_model=TrainingSessionRead, status_code=status.HTTP_201_CREATED)
def schedule_session_for_client(
    client_id: str,
    payload: TrainingSessionCreate,
    session: Session = Depends(db_session),
):
    """
    Agenda uma nova sessão de treino para um cliente específico.
    """
    try:
        new_session = SessionService.schedule_session(
            session = session,
            client_id=client_id,
            starts_at=payload.starts_at,
            duration_minutes=payload.duration_minutes,
            location=payload.location,
            notes=payload.notes,
        )
        return new_session
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )   

@router.get("", response_model=list[TrainingSessionRead])
def list_sessions(session: Session = Depends(db_session)) -> list[TrainingSession]:
    """
    Lista todas as sessões de treino.
    """

    stmt = select(TrainingSession).order_by(TrainingSession.starts_at.desc().limit(100))
    return list(session.exec(stmt).all())

@router.post("/{session_id}/complete", response_model=TrainingSessionRead)
def complete_session(session_id: str, session: Session = Depends(db_session)):
    """
    Marca uma sessão como concluída e consome um pack do cliente.
    """
    try:
        updated_session = SessionService.complete_session_consuming_pack(
            session=session,
            session_id=session_id,
        )
        return updated_session
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )