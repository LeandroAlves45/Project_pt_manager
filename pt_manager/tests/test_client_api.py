import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    # Testa o endpoint de health check para garantir que a API e o banco de dados estão funcionando.
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_create_client():
    # Testa a criação de um cliente para garantir que a rota de criação de clientes funciona.
    headers = {"X-API-Key": "1234"}

    new_client = {
        "full_name": "Leandro Alves",
        "phone": "351936064245",
        "email": "leandro06leo@hotmail.com",
        "birth_date": "1990-01-01"
    }

    response = client.post("/api/v1/clients", json=new_client, headers=headers)

    assert response.status_code == 201
    data = response.json()
    assert data["full_name"] == "Leandro Alves"
    assert "id" in data