"""
Testes de integracao para o sistema de active tokens (migration 006).
 
Principio de cada teste:
  Cada teste parte de um estado limpo (rollback via fixture db).
  Nao ha dependencias entre testes.
"""

import pytest
from sqlmodel import select
from app.db.models.active_token import ActiveToken
from app.core.config import settings

# ============================================================
# Login
# ============================================================

class TestLogin:

    def test_login_sucessful_return_token(self, client, trainer_user, api_key_headers):
        """
        POST /auth/login com credenciais validas deve devolver access_token,
        role, user_id e full_name.
        """
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "trainer@teste.pt", "password": "Trainer123!"},
            headers=api_key_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["role"] == "trainer"
        assert data["user_id"] == trainer_user.id
        assert data["full_name"] == "Trainer Teste"

    def test_login_persists_token_in_database(self, client, trainer_user, db, api_key_headers):
        """
        Apos login, deve existir exactamente uma linha em active_tokens
        com o user_id do trainer.
        Este e o requisito central do sistema de active tokens:
        sem esta linha, o get_current_user rejeita todos os pedidos.
        """
        client.post(
            "/api/v1/auth/login",
            json={"email": "trainer@teste.pt", "password": "Trainer123!"},
            headers=api_key_headers,
        )
        tokens = db.exec(
            select(ActiveToken).where(ActiveToken.user_id == trainer_user.id)
        ).all()
        assert len(tokens) == 1, "Deve existir exactamente um token activo por utilizador"   

    def test_login_second_login_replaces_previous_token(self, client, trainer_user, db, api_key_headers):
        """
        Fazer login duas vezes nao deve acumular tokens.
        O segundo login deve apagar o primeiro e criar um novo.
        Garante que nunca ha mais de uma sessao activa por utilizador.
        """
        client.post(
            "/api/v1/auth/login",
            json={"email": "trainer@teste.pt", "password": "Trainer123!"},
            headers=api_key_headers,
        )
        client.post(
            "/api/v1/auth/login",
            json={"email": "trainer@teste.pt", "password": "Trainer123!"},
            headers=api_key_headers,
        )
        tokens = db.exec(
            select(ActiveToken).where(ActiveToken.user_id == trainer_user.id)
        ).all()
        assert len(tokens) == 1, "Dois logins consecutivos devem resultar num unico token activo"

    def test_login_wrong_password_returns_401(self, client, trainer_user, api_key_headers):
        """
        Credenciais erradas devem devolver 401.
        A mensagem de erro nao deve distinguir entre 'email nao existe'
        e 'password errada' (evita user enumeration).
        """
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "trainer@teste.pt", "password": "passworderrada"},
            headers=api_key_headers,
        )
        assert resp.status_code == 401

    def test_login_nonexistent_email_returns_401(self, client, api_key_headers):
        """Email que nao existe na BD deve devolver 401 (igual a password errada)."""
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "naoexiste@teste.pt", "password": "qualquercoisa"},
            headers=api_key_headers,
        )
        assert resp.status_code == 401

    def test_login_without_api_key_returns_401(self, client, trainer_user):
        """
        Pedidos sem X-API-Key devem ser rejeitados com 401,
        mesmo que as credenciais sejam validas.
        """
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "trainer@teste.pt", "password": "Trainer123!"},
        )
        assert resp.status_code == 401

    def test_login_inactive_account_returns_401(self, client, trainer_user, db, api_key_headers):
        """Trainer suspenso (is_active=False) nao deve conseguir fazer login."""
        trainer_user.is_active = False
        db.add(trainer_user)
        db.flush()
 
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "trainer@teste.pt", "password": "Trainer123!"},
            headers=api_key_headers,
        )
        assert resp.status_code == 401

# ============================================================
# Logout
# ============================================================
 
class TestLogout:
 
    def _login(self, client, api_key_headers):
        """Auxiliar: faz login e devolve os headers de autenticacao."""
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "trainer@teste.pt", "password": "Trainer123!"},
            headers=api_key_headers,
        )
        token = resp.json()["access_token"]
        return {
            "Authorization": f"Bearer {token}",
            "X-API-Key": settings.api_key,
        }
    
    def test_logout_remove_token_from_database(self, client, trainer_user, db, api_key_headers):
        """
        Apos POST /auth/logout, a linha em active_tokens deve ser apagada.
        """
        headers = self._login(client, api_key_headers)
 
        # Confirma que o token existe antes do logout
        before_token = db.exec(
            select(ActiveToken).where(ActiveToken.user_id == trainer_user.id)
        ).all()
        assert len(before_token) == 1
 
        # Logout
        resp = client.post("/api/v1/auth/logout", headers=headers)
        assert resp.status_code == 200

        # Confirma que o token foi apagado
        db.expire_all()  # limpa o cache da sessao para ver o estado actual da BD
        after_token = db.exec(
            select(ActiveToken).where(ActiveToken.user_id == trainer_user.id)
        ).all()
        assert len(after_token) == 0, "Token deve ser apagado apos logout"

    def test_after_request_logout_returns_401(self, client, trainer_user, db, api_key_headers):
        """
        Usar o token apos logout deve devolver 401.
        Verifica que a invalidação é imediata - o JWT em si ainda seria válido
        (não expirou) mas a linha na BD foi apagada.
        """
        headers = self._login(client, api_key_headers)
 
        # Logout invalida o token
        client.post("/api/v1/auth/logout", headers=headers)
 
        # Tentar usar o mesmo token depois do logout
        resp = client.get("/api/v1/auth/users/me", headers=headers)
        assert resp.status_code == 401, (
            "Token deve ser rejeitado apos logout, mesmo que o JWT ainda não tenha expirado"
        )

    def test_invalid_token_returns_401(self, client, api_key_headers):
        """Token JWT fabricado (não existe na BD) deve ser rejeitado com 401."""
        headers = {
            "Authorization": "Bearer token.completamente.falso",
            "X-API-Key": settings.api_key,
        }
        resp = client.get("/api/v1/auth/users/me", headers=headers)
        assert resp.status_code == 401