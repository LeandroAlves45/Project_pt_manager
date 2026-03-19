"""
Testes de integracao para o fluxo de convite de clientes (AU-09).
 
Cobre o fluxo completo:
  1. Trainer gera link de convite
  2. Validacao do token (publica)
  3. Cliente define password via token
  4. Auto-login apos definicao de password
  5. Casos de erro: token invalido, expirado, re-uso
"""

import pytest
import hashlib
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
 
 
def _sha256(raw: str) -> str:
    """Helper identico ao da implementacao."""
    return hashlib.sha256(raw.encode()).hexdigest()
 
 
# ============================================================
# Geracao do link de convite (trainer)
# ============================================================

class TestGenerateInviteLink:
 
    def test_generate_invite_link_returns_link(
        self, client, trainer_headers, client_record, client_user
    ):
        """POST /clients/{id}/generate-invite devolve link e validade."""
        resp = client.post(
            f"/api/v1/clients/{client_record.id}/generate-invite",
            headers=trainer_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "invite_link" in data
        assert data["expires_in_days"] == 7
        # O link deve conter /invite/ seguido de um token
        assert "/invite/" in data["invite_link"]

    def test_generate_invite_link_persists_hash_in_db(
        self, client, trainer_headers, client_record, client_user, db
    ):
        """
        Após gerar o convite, o hash SHA-256 do token deve estar guardado
        no utilizador -- nunca o raw token.
        """
        resp = client.post(
            f"/api/v1/clients/{client_record.id}/generate-invite",
            headers=trainer_headers,
        )
        assert resp.status_code == 201
 
        # Extrair raw token do link
        invite_link = resp.json()["invite_link"]
        raw_token = invite_link.split("/invite/")[-1]
 
        # Verificar que o hash esta guardado (nao o raw token)
        db.refresh(client_user)
        assert client_user.invite_token_hash == _sha256(raw_token)
        assert client_user.invite_token_hash != raw_token  # nunca em plain text
 
    def test_generate_second_invite_invalidates_first(
        self, client, trainer_headers, client_record, client_user, db
    ):
        """
        Gerar dois convites consecutivos -- apenas o segundo deve ser valido.
        O hash do primeiro é substituído pelo do segundo.
        """
        resp1 = client.post(
            f"/api/v1/clients/{client_record.id}/generate-invite",
            headers=trainer_headers,
        )
        token1 = resp1.json()["invite_link"].split("/invite/")[-1]
 
        resp2 = client.post(
            f"/api/v1/clients/{client_record.id}/generate-invite",
            headers=trainer_headers,
        )
        assert resp2.status_code == 201
 
        # O hash na BD deve corresponder ao segundo token, não ao primeiro
        db.refresh(client_user)
        assert client_user.invite_token_hash == _sha256(resp2.json()["invite_link"].split("/invite/")[-1])
        assert client_user.invite_token_hash != _sha256(token1)

    def test_trainer_cannot_invite_client_of_another_trainer(
        self, client, second_trainer_headers, client_record
    ):
        """Trainer B não pode gerar convite para cliente de Trainer A."""
        resp = client.post(
            f"/api/v1/clients/{client_record.id}/generate-invite",
            headers=second_trainer_headers,
        )
        assert resp.status_code == 403
 
    def test_client_without_user_account_returns_404(
        self, client, trainer_headers, db, trainer_user
    ):
        """
        Tentar gerar convite para cliente que ainda não tem conta User.
        O trainer deve criar a conta User primeiro (POST /auth/users).
        """
        from datetime import date
        from app.db.models.client import Client
        cliente_sem_conta = Client(
            full_name="Sem Conta",
            phone="913000000",
            birth_date=date(1990, 1, 1),
            owner_trainer_id=trainer_user.id,
        )
        db.add(cliente_sem_conta)
        db.flush()
 
        resp = client.post(
            f"/api/v1/clients/{cliente_sem_conta.id}/generate-invite",
            headers=trainer_headers,
        )
        assert resp.status_code == 404

# ============================================================
# Validação do token (pública)
# ============================================================
 
class TestValidateToken:
 
    def _create_token_in_db(self, client_user, db, expires_delta=None):
        """Auxiliar: cria token de convite directamente na BD."""
        import secrets
        raw = secrets.token_urlsafe(32)
        from app.utils.time import utc_now_datetime
        client_user.invite_token_hash = _sha256(raw)
        client_user.invite_token_expires_at = (
            utc_now_datetime() + (expires_delta or timedelta(days=7))
        )
        db.add(client_user)
        db.flush()
        return raw
 
    def test_validate_valid_token(self, client, client_user, db, api_key_headers):
        """GET /invite/validate/{token} com token valido devolve valid=True e nome."""
        raw = self._create_token_in_db(client_user, db)
 
        resp = client.get(
            f"/api/v1/invite/validate/{raw}",
            headers=api_key_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is True
        assert data["client_name"] == client_user.full_name

    def test_validate_invalid_token(self, client, api_key_headers):
        """Token que não existe na BD deve devolver valid=False."""
        resp = client.get(
            "/api/v1/invite/validate/token_completamente_invalido",
            headers=api_key_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is False
        assert len(data["message"]) > 0
 
    def test_validate_expired_token(self, client, client_user, db, api_key_headers):
        """Token com expires_at no passado deve devolver valid=False."""
        raw = self._create_token_in_db(
            client_user, db, expires_delta=timedelta(days=-1)
        )
        resp = client.get(
            f"/api/v1/invite/validate/{raw}",
            headers=api_key_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["valid"] is False

# ============================================================
# Definir password via convite e auto-login
# ============================================================
 
class TestDefinePasswordAndAutoLogin:
 
    def _create_valid_token(self, client_user, db):
        """Cria token valido na BD e devolve o raw token."""
        import secrets
        from app.utils.time import utc_now_datetime
        raw = secrets.token_urlsafe(32)
        client_user.invite_token_hash = _sha256(raw)
        client_user.invite_token_expires_at = utc_now_datetime() + timedelta(days=7)
        db.add(client_user)
        db.flush()
        return raw
    
    def test_set_password_returns_jwt(self, client, client_user, db, api_key_headers):
        """
        POST /invite/set-password/{token} com password valida deve:
        - Devolver access_token, role=client, user_id
        - O cliente fica autenticado sem necessitar de login separado
        """
        raw = self._create_valid_token(client_user, db)
 
        resp = client.post(
            f"/api/v1/invite/set-password/{raw}",
            json={"new_password": "NovaPassword123!"},
            headers=api_key_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["role"] == "client"
        assert data["user_id"] == client_user.id
 
    def test_set_invalid_password_after_use_token(
        self, client, client_user, db, api_key_headers
    ):
        """
        Após usar o token para definir a password, o token deve ser invalidado.
        Re-usar o mesmo link deve ser rejeitado (one-time use).
        """
        raw = self._create_valid_token(client_user, db)
 
        # Usar uma vez -- sucesso
        resp1 = client.post(
            f"/api/v1/invite/set-password/{raw}",
            json={"new_password": "NovaPassword123!"},
            headers=api_key_headers,
        )
        assert resp1.status_code == 200
 
        # Usar o mesmo token outra vez -- deve falhar
        resp2 = client.post(
            f"/api/v1/invite/set-password/{raw}",
            json={"new_password": "OutraPassword!"},
            headers=api_key_headers,
        )
        assert resp2.status_code == 400

    def test_set_password_hash_in_db_updated(
        self, client, client_user, db, api_key_headers
    ):
        """
        Após set-password, a password guardada na BD deve corresponder
        a nova password (verificado com verify_password).
        """
        from app.core.security import verify_password
        raw = self._create_valid_token(client_user, db)
 
        client.post(
            f"/api/v1/invite/set-password/{raw}",
            json={"new_password": "PasswordDefinida456!"},
            headers=api_key_headers,
        )
 
        db.refresh(client_user)
        assert verify_password("PasswordDefinida456!", client_user.hashed_password)
 
    def test_set_password_token_invalid_returns_400(
        self, client, api_key_headers
    ):
        """Token que nao existe na BD deve devolver 400."""
        resp = client.post(
            "/api/v1/invite/set-password/token_que_nao_existe",
            json={"new_password": "Qualquer123!"},
            headers=api_key_headers,
        )
        assert resp.status_code == 400

    def test_set_password_expired_token_returns_400(
        self, client, client_user, db, api_key_headers
    ):
        """Token expirado nao pode ser usado para definir password."""
        import secrets
        from app.utils.time import utc_now_datetime
        raw = secrets.token_urlsafe(32)
        client_user.invite_token_hash = _sha256(raw)
        client_user.invite_token_expires_at = utc_now_datetime() - timedelta(days=1)
        db.add(client_user)
        db.flush()
 
        resp = client.post(
            f"/api/v1/invite/set-password/{raw}",
            json={"new_password": "Qualquer123!"},
            headers=api_key_headers,
        )
        assert resp.status_code == 400
 
    def test_set_password_short_returns_422(
        self, client, client_user, db, api_key_headers
    ):
        """Password com menos de 6 caracteres deve ser rejeitada pela validação Pydantic."""
        raw = self._create_valid_token(client_user, db)
 
        resp = client.post(
            f"/api/v1/invite/set-password/{raw}",
            json={"new_password": "123"},
            headers=api_key_headers,
        )
        assert resp.status_code == 422