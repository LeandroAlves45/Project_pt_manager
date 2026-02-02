from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from sqlalchemy.exc import SQLAlchemyError

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
) -> TrainingSession:
    """
    Agenda uma nova sessão de treino para um cliente específico.
    """
    try:
        return SessionService.schedule_session(
            session = session,
            client_id=client_id,
            starts_at=payload.starts_at,
            duration_minutes=payload.duration_minutes,
            location=payload.location,
            notes=payload.notes,
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail="Erro ao agendar sessão.") from e  

@router.get("", response_model=list[TrainingSessionRead])
def list_sessions(session: Session = Depends(db_session)) -> list[TrainingSession]:
    """
    Lista todas as sessões de treino.
    """

    try:
        stmt = select(TrainingSession).order_by(TrainingSession.starts_at.desc()).limit(100)
        return list(session.exec(stmt).all())
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail="Erro ao listar sessões.") from e

@router.post("/{session_id}/complete", response_model=TrainingSessionRead)
def complete_session(session_id: str, session: Session = Depends(db_session)) -> TrainingSession:
    """
    Marca uma sessão como concluída e consome um pack do cliente.
    """
    try:
        return SessionService.complete_session_consuming_pack(session=session, session_id=session_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail="Erro ao completar sessão.") from e