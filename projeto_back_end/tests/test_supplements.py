"""
Testes de integracao para suplementos (SU-01 a SU-05).
 
Cobre:
  CRUD do catalogo de suplementos
  Atribuicao a clientes + portal do cliente
  Multi-tenancy -- trainer nao ve suplementos de outro trainer
"""

import pytest
 
 
# ============================================================
# Catalogo de suplementos (CRUD)
# ============================================================
 
class TestCatalogoSuplementos:
 
    def test_create_supplement(self, client, trainer_user, trainer_headers):
        """POST /supplements cria suplemento e devolve 201."""
        resp = client.post(
            "/api/v1/supplements",
            json={"name": "Creatina", "serving_size": "5g", "timing": "Pos-treino"},
            headers=trainer_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Creatina"
        assert data["created_by_user_id"] == trainer_user.id

    def test_create_supplement_name_required(self, client, trainer_headers):
        """POST sem nome deve devolver 422 (Pydantic validation)."""
        resp = client.post(
            "/api/v1/supplements",
            json={"serving_size": "5g"},
            headers=trainer_headers,
        )
        assert resp.status_code == 422

    def test_listar_suplementos_proprios(self, client, trainer_headers, supplement_in_db):
        """GET /supplements lista apenas suplementos do trainer autenticado."""
        resp = client.get("/api/v1/supplements", headers=trainer_headers)
        assert resp.status_code == 200
        nomes = [s["name"] for s in resp.json()]
        assert "Creatina Monohidratada" in nomes
 
    def test_isolate_multi_tenant_list(
        self, client, trainer_headers, second_trainer_headers,
        supplement_in_db, db
    ):
        """
        Trainer B nao deve ver os suplementos criados por Trainer A.
        Verifica o requisito critico de multi-tenancy: nenhum dado cruza fronteiras de tenant.
        """
        # Trainer A (trainer_user) tem um suplemento criado pela fixture supplement_in_db
        resp_a = client.get("/api/v1/supplements", headers=trainer_headers)
        assert any(s["name"] == "Creatina Monohidratada" for s in resp_a.json())
 
        # Trainer B nao deve ver o suplemento do Trainer A
        resp_b = client.get("/api/v1/supplements", headers=second_trainer_headers)
        nomes_b = [s["name"] for s in resp_b.json()]
        assert "Creatina Monohidratada" not in nomes_b, (
            "Violacao de multi-tenancy: Trainer B nao deve ver suplementos do Trainer A"
        )

    def test_archive_supplement(self, client, trainer_headers, supplement_in_db):
        """POST /{id}/archive muda archived_at para nao-nulo."""
        resp = client.post(
            f"/api/v1/supplements/{supplement_in_db.id}/archive",
            headers=trainer_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["archived_at"] is not None
 
    def test_unarchive_supplement(self, client, trainer_headers, supplement_in_db):
        """Archive seguido de unarchive volta archived_at a null."""
        client.post(
            f"/api/v1/supplements/{supplement_in_db.id}/archive",
            headers=trainer_headers,
        )
        resp = client.post(
            f"/api/v1/supplements/{supplement_in_db.id}/unarchive",
            headers=trainer_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["archived_at"] is None

    def test_archive_idempotent(self, client, trainer_headers, supplement_in_db):
        """Arquivar duas vezes nao deve dar erro -- operacao idempotente."""
        client.post(
            f"/api/v1/supplements/{supplement_in_db.id}/archive",
            headers=trainer_headers,
        )
        resp = client.post(
            f"/api/v1/supplements/{supplement_in_db.id}/archive",
            headers=trainer_headers,
        )
        assert resp.status_code == 200
 
    def test_patch_supplement(self, client, trainer_headers, supplement_in_db):
        """PATCH actualiza apenas os campos enviados."""
        resp = client.patch(
            f"/api/v1/supplements/{supplement_in_db.id}",
            json={"timing": "Pre-treino"},
            headers=trainer_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["timing"] == "Pre-treino"
        # Campo nao enviado mantem valor original
        assert resp.json()["name"] == "Creatina Monohidratada"

    def test_another_trainer_cannot_edit(
        self, client, second_trainer_headers, supplement_in_db
    ):
        """
        Trainer B nao pode editar suplementos criados por Trainer A.
        Verifica a ownership check no endpoint PATCH.
        """
        resp = client.patch(
            f"/api/v1/supplements/{supplement_in_db.id}",
            json={"name": "Tentativa de edicao"},
            headers=second_trainer_headers,
        )
        assert resp.status_code == 403
 
    def test_another_trainer_cannot_archive(
        self, client, second_trainer_headers, supplement_in_db
    ):
        """Trainer B nao pode arquivar suplementos do Trainer A."""
        resp = client.post(
            f"/api/v1/supplements/{supplement_in_db.id}/archive",
            headers=second_trainer_headers,
        )
        assert resp.status_code == 403
 
    def test_delete_supplement(self, client, trainer_headers, db, trainer_user):
        """DELETE remove permanentemente o suplemento."""
        from app.db.models.supplement import Supplement
        supp = Supplement(
            name="Para Apagar",
            created_by_user_id=trainer_user.id,
        )
        db.add(supp)
        db.flush()
 
        resp = client.delete(
            f"/api/v1/supplements/{supp.id}",
            headers=trainer_headers,
        )
        assert resp.status_code == 204

    def test_client_cannot_see_trainer_notes(
        self, client, client_headers, supplement_in_db, db
    ):
        """
        Clientes não devem ver o campo trainer_notes (informacao interna do trainer).
        A função _to_response do router usa SupplementReadPublic para clientes.
        """
        # Adicionar trainer_notes ao suplemento
        supplement_in_db.trainer_notes = "Notas internas confidenciais"
        db.add(supplement_in_db)
        db.flush()
 
        resp = client.get(
            f"/api/v1/supplements/{supplement_in_db.id}",
            headers=client_headers,
        )
        assert resp.status_code == 200
        assert "trainer_notes" not in resp.json(), (
            "trainer_notes nao deve ser exposto a clientes"
        )

# ============================================================
# Atribuição de suplementos a clientes
# ============================================================
 
class TestSupplementAssignment:
 
    def test_assign_supplement_to_client(
        self, client, trainer_headers, client_record, supplement_in_db
    ):
        """POST /clients/{id}/supplements atribui suplemento e devolve 201."""
        resp = client.post(
            f"/api/v1/clients/{client_record.id}/supplements",
            json={
                "supplement_id": supplement_in_db.id,
                "dose": "10g",
                "timing_notes": "30 min antes do treino",
            },
            headers=trainer_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["supplement_id"] == supplement_in_db.id
        assert data["dose"] == "10g"
        assert data["supplement_name"] == "Creatina Monohidratada"

    def test_assign_duplicate_supplement_returns_409(
        self, client, trainer_headers, client_record, supplement_in_db
    ):
        """
        Atribuir o mesmo suplemento duas vezes ao mesmo cliente deve devolver 409.
        A restrição UNIQUE (client_id, supplement_id) na BD garante isto.
        """
        client.post(
            f"/api/v1/clients/{client_record.id}/supplements",
            json={"supplement_id": supplement_in_db.id},
            headers=trainer_headers,
        )
        resp = client.post(
            f"/api/v1/clients/{client_record.id}/supplements",
            json={"supplement_id": supplement_in_db.id},
            headers=trainer_headers,
        )
        assert resp.status_code == 409

    def test_list_client_supplements(
        self, client, trainer_headers, client_record, supplement_in_db
    ):
        """GET /clients/{id}/supplements lista as atribuições do cliente."""
        client.post(
            f"/api/v1/clients/{client_record.id}/supplements",
            json={"supplement_id": supplement_in_db.id},
            headers=trainer_headers,
        )
        resp = client.get(
            f"/api/v1/clients/{client_record.id}/supplements",
            headers=trainer_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["supplement_name"] == "Creatina Monohidratada"
    
    def test_remove_assignment(
        self, client, trainer_headers, client_record, supplement_in_db
    ):
        """DELETE /clients/{id}/supplements/{assign_id} remove a atribuição."""
        create_resp = client.post(
            f"/api/v1/clients/{client_record.id}/supplements",
            json={"supplement_id": supplement_in_db.id},
            headers=trainer_headers,
        )
        assignment_id = create_resp.json()["id"]
 
        del_resp = client.delete(
            f"/api/v1/clients/{client_record.id}/supplements/{assignment_id}",
            headers=trainer_headers,
        )
        assert del_resp.status_code == 204
 
        # Confirmar que a lista fica vazia
        list_resp = client.get(
            f"/api/v1/clients/{client_record.id}/supplements",
            headers=trainer_headers,
        )
        assert list_resp.json() == []

    def test_trainer_b_dont_access_trainer_a_client(
        self, client, second_trainer_headers, client_record, supplement_in_db
    ):
        """
        Trainer B nao pode ver ou gerir suplementos de clientes do Trainer A.
        Verifica isolamento de tenant no endpoint de atribuicao.
        """
        resp = client.get(
            f"/api/v1/clients/{client_record.id}/supplements",
            headers=second_trainer_headers,
        )
        assert resp.status_code == 403
 
 
# ============================================================
# Portal do cliente -- my-supplements 
# ============================================================

class TestSupplementsPortal:
 
    def test_client_sees_their_supplements(
        self, client, trainer_headers, client_headers,
        client_record, supplement_in_db
    ):
        """
        GET /portal/my-supplements devolve os suplementos atribuidos ao cliente.
        O JWT identifica o cliente automaticamente -- sem parametros.
        """
        # Trainer atribui suplemento
        client.post(
            f"/api/v1/clients/{client_record.id}/supplements",
            json={
                "supplement_id": supplement_in_db.id,
                "dose": "5g",
                "timing_notes": "Ao acordar",
            },
            headers=trainer_headers,
        )
 
        # Cliente ve os seus suplementos
        resp = client.get("/api/v1/portal/my-supplements", headers=client_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["supplement_name"] == "Creatina Monohidratada"
        assert data[0]["dose"] == "5g"
        assert data[0]["timing_notes"] == "Ao acordar"

    def test_client_does_not_see_trainer_notes_in_portal(
        self, client, trainer_headers, client_headers,
        client_record, supplement_in_db, db
    ):
        """trainer_notes não deve aparecer na resposta do portal do cliente."""
        supplement_in_db.trainer_notes = "Confidencial"
        db.add(supplement_in_db)
        db.flush()
 
        client.post(
            f"/api/v1/clients/{client_record.id}/supplements",
            json={"supplement_id": supplement_in_db.id},
            headers=trainer_headers,
        )
 
        resp = client.get("/api/v1/portal/my-supplements", headers=client_headers)
        assert resp.status_code == 200
        for item in resp.json():
            assert "trainer_notes" not in item or item.get("trainer_notes") is None
 
    def test_portal_without_supplements_returns_empty_list(
        self, client, client_headers
    ):
        """Sem atribuições, o portal devolve lista vazia (não erro)."""
        resp = client.get("/api/v1/portal/my-supplements", headers=client_headers)
        assert resp.status_code == 200
        assert resp.json() == []