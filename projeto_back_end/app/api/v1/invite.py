"""
Router do fluxo de convite de clientes (AU-09).
 
Este router tem dois grupos de endpoints com niveis de acesso distintos:
 
  PROTEGIDOS (require_active_subscription):
    POST /clients/{client_id}/generate-invite
      — trainer gera o link de convite para um cliente
 
  PUBLICOS (apenas API-Key, sem JWT):
    GET  /invite/validate/{token}
      — valida o token e devolve o nome do cliente (para a pagina /invite/:token)
    POST /invite/set-password/{token}
      — cliente define a sua password e recebe um JWT imediatamente
 
Seguranca do token:
    1. Backend gera 32 bytes aleatorios via secrets.token_urlsafe(32)
    2. Armazena SHA-256(token) na BD — nunca o raw token
    3. O raw token viaja apenas no URL de convite (HTTPS)
    4. Na validacao, o backend recalcula SHA-256(token_recebido) e compara com o hash guardado
    5. Apos utilizacao, o hash e apagado da BD (one-time use)
    6. Tokens expiram ao fim de 7 dias
"""

import secrets
import hashlib
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.api.deps import db_session
from app.core.security import (
    require_active_subscription,
    create_access_token,
    hash_password,
)
from app.core.config import settings
from app.core.db_errors import commit_or_rollback
from app.db.models.user import User
from app.db.models.client import Client
from app.db.models.active_token import ActiveToken
from app.schemas.invite import (
    InviteGenerateResponse,
    InviteValidateResponse,
    InviteSetPassword,
    InviteLoginResponse,
)
from app.utils.time import utc_now_datetime
 
router = APIRouter(tags=["Invite"])

# Validade do token de convite em dias
INVITE_EXPIRY_DAYS = 7

def _sha256(raw_token: str) -> str:
    """Calcula o hash SHA-256 do token."""
    return hashlib.sha256(raw_token.encode()).hexdigest()

def _get_frontend_base_url() -> str:
    """Obtém a URL base do frontend a partir das configurações."""
    origins = settings.cors_origins.split(",")
    return origins[0].strip().rstrip("/")

# ============================================================
# ENDPOINT PROTEGIDO — apenas trainers com subscricao activa
# ============================================================

@router.post("/clients/{client_id}/generate-invite", response_model=InviteGenerateResponse, status_code=status.HTTP_201_CREATED)
async def generate_invite(
    client_id: str,
    session: Session = Depends(db_session),
    current_user: User = Depends(require_active_subscription),
):
    # Endpoint para trainers gerarem um link de convite para um cliente específico.
    # O link é enviado ao cliente via WhatsApp/SMS pelo trainer.
    try:
        # Verificar se o cliente existe e pertence ao trainer
        client = session.get(Client, client_id)
        if not client or client.archived_at is not None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado")
        if client.owner_trainer_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado ao cliente")
        
        # Verifica que o cliente tem uma conta User associada
        user = session.exec(
            select(User).where(User.client_id == client_id)
        ).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Este cliente ainda nao tem conta de utilizador. Cria a conta primeiro.")

        # Gerar token de convite
        raw_token = secrets.token_urlsafe(32)

        # Armazenar hash do token e data de expiração na BD
        user.invite_token_hash = _sha256(raw_token)
        user.invite_token_expires_at = utc_now_datetime() + timedelta(days=INVITE_EXPIRY_DAYS)
        user.updated_at = utc_now_datetime()
        session.add(user)
        commit_or_rollback(session)

        # Construir link de convite para o frontend
        base = _get_frontend_base_url()
        invite_link = f"{base}/invite/{raw_token}"

        return InviteGenerateResponse(invite_link=invite_link, expires_in_days=INVITE_EXPIRY_DAYS)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erro ao gerar convite") from e
    
# ============================================================
# ENDPOINTS PUBLICOS — sem JWT, apenas API-Key
# ============================================================

@router.get("/invite/validate/{token}", response_model=InviteValidateResponse)
async def validate_invite_token(token: str, session: Session = Depends(db_session)) -> InviteValidateResponse:
    # Endpoint público para validar o token de convite.
    # Usado na página /invite/:token para mostrar o nome do cliente e personalizar a experiência.
    try:
        token_hash = _sha256(token)

        user = session.exec(
            select(User).where(User.invite_token_hash == token_hash)
        ).first()

        if not user or not user.client_id:
            return InviteValidateResponse(valid=False, client_name="", message="Token inválido ou já utilizado.")
        now = utc_now_datetime()
        if user.invite_token_expires_at is None or now > user.invite_token_expires_at.replace(tzinfo=timezone.utc):
            return InviteValidateResponse(valid=False, client_name="", message="Token expirado. Por favor peça um novo convite ao seu trainer.")
        

        client = session.get(Client, user.client_id)
        client_name = client.full_name if client else ""
        return InviteValidateResponse(valid=True, client_name=client_name)
    
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erro ao validar token") from e
    
@router.post("/invite/set-password/{token}", response_model=InviteLoginResponse)
async def set_password_via_invite(
    token: str,
    payload: InviteSetPassword,
    session: Session = Depends(db_session),
) -> InviteLoginResponse:
    # Endpoint público para o cliente definir a sua password usando o token de convite.
    # Após definir a password, o cliente recebe um JWT para acesso imediato ao dashboard.
    try:
        token_hash = _sha256(token)

        user = session.exec(
            select(User).where(User.invite_token_hash == token_hash)
        ).first()

        if not user or not user.client_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token inválido ou já utilizado.")
        
        now = utc_now_datetime()
        if user.invite_token_expires_at is None or now > user.invite_token_expires_at.replace(tzinfo=timezone.utc):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token expirado. Por favor peça um novo convite ao seu trainer.")
        
        # Atualizar a password do usuário e limpar os campos de convite
        user.hashed_password = hash_password(payload.new_password)

        # Invalida o token de convite para uso único
        user.invite_token_hash = None
        user.invite_token_expires_at = None
        user.is_active = True  # Ativa a conta do cliente ao definir a password
        user.updated_at = utc_now_datetime()
        session.add(user)
      
        # Cria sessão JWT para o cliente
        expire_delta = timedelta(minutes=settings.access_token_expire_minutes)
        jwt_token = create_access_token(
            subject=user.id,
            role=user.role,
            full_name=user.full_name,
            client_id=user.client_id,
            expires_delta=expire_delta,
        )

        # Remove token existente e insere o novo
        existing = session.exec(
            select(ActiveToken).where(ActiveToken.user_id == user.id)
        ).first()
        if existing:
            session.delete(existing)
            session.flush()

        expires_at = utc_now_datetime() + expire_delta
        session.add(ActiveToken(user_id=user.id, token=jwt_token, expires_at=expires_at))
        commit_or_rollback(session)
       

        return InviteLoginResponse(
            access_token=jwt_token,
            role=user.role,
            user_id=user.id,
            full_name=user.full_name,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erro ao definir password") from e
    
