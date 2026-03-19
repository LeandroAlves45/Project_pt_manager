"""
conftest.py - infraestrutura de testes para o PT Manager.
 
NOTA: variaveis de ambiente definidas ANTES de qualquer import da app.
"""
 
import os
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("API_KEY", "test_api_key_local")
os.environ.setdefault("SECRET_KEY", "test_secret_key_minimo_32_chars_xxxxxx")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:5173")
os.environ.setdefault("TRIAL_DAYS", "15")
os.environ.setdefault("SUPERUSER_EMAIL", "admin@test.pt")
os.environ.setdefault("SUPERUSER_PASSWORD", "Admin123!")
 
import pytest
from unittest.mock import patch
from datetime import date
from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
 
# Importar todos os modelos para registar o metadata
from app.db.models.user import User
from app.db.models.active_token import ActiveToken
from app.db.models.client import Client
from app.db.models.trainer_subscription import (
    TrainerSubscription, SubscriptionStatus, SubscriptionTier
)
from app.db.models.trainer_settings import TrainerSettings
from app.db.models.session import TrainingSession, PackConsumption
from app.db.models.pack import PackType, ClientPack
from app.db.models.training import (
    Exercise, TrainingPlan, TrainingPlanDay,
    PlanDayExercise, PlanExerciseSetLoad, ClientActivePlan,
)
from app.db.models.initial_assessment import InitialAssessment
from app.db.models.checkin import CheckIn
from app.db.models.nutrition import Food, MealPlan, MealPlanMeal, MealPlanItem
from app.db.models.supplement import Supplement
from app.db.models.client_supplement import ClientSupplement
from app.db.models.notification import Notification
 
from app.core.security import hash_password, create_access_token
from app.core.config import settings
from app.api.deps import db_session
from app.main import app

# =============================================================================
# ENGINE - criado uma vez por sessao de testes (scope=session)
# =============================================================================

@pytest.fixture()
def engine_in_memory():
    """
    Motor SQLite em memoria partilhado por toda a sessao de testes.
    As tabelas sao criadas aqui uma unica vez.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    yield engine

# =============================================================================
# SESSAO COM SAVEPOINTS - isolamento real entre testes
#
# Estrategia:
#   1. Abrir uma ligacao ao nivel do engine (connection)
#   2. Iniciar uma transacao externa (nunca committed)
#   3. Criar a sessao SQLModel ligada a esta connection
#   4. Cada operacao dentro do teste usa savepoints automaticamente
#   5. No teardown: rollback da transacao externa - tudo apagado
#
# Isto garante que mesmo os commit() feitos pelos handlers da API
# sao revertidos, porque estao dentro da transacao externa nao committed.
# =============================================================================

@pytest.fixture()
def db(engine_in_memory):
    """
    BD fresca por teste - engine criado com scope=function garante
    que cada teste tem o seu proprio SQLite em memoria, sem interferencias.
    """
    with Session(engine_in_memory) as session:
        yield session

# =============================================================================
# TESTCLIENT
# =============================================================================

@pytest.fixture()
def client(db):
    """
    TestClient com db_session substituida e startup sem migrations/seeds/scheduler.
    """
    def _override_db():
        yield db
 
    app.dependency_overrides[db_session] = _override_db
 
    with patch("app.db.init_db.run_migrations"), \
         patch("app.db.migrate.run_migrations"), \
         patch("app.main.seed_superuser"), \
         patch("app.main.seed_pack_types"), \
         patch("app.main.seed_demo_data"), \
         patch("app.main.start_scheduler"), \
         patch("app.main.shutdown_scheduler"):
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c
 
    app.dependency_overrides.clear()

# =============================================================================
# FIXTURES DE UTILIZADORES E DADOS
# =============================================================================
 
@pytest.fixture()
def trainer_user(db) -> User:
    """Trainer com subscricao activa."""
    user = User(
        email="trainer@teste.pt",
        hashed_password=hash_password("Trainer123!"),
        full_name="Trainer Teste",
        role="trainer",
        is_active=True,
    )
    db.add(user)
    db.flush()
 
    sub = TrainerSubscription(
        trainer_user_id=user.id,
        status=SubscriptionStatus.ACTIVE,
        tier=SubscriptionTier.FREE,
        active_clients_count=0,
    )
    db.add(sub)
    db.flush()
    return user
 
 
@pytest.fixture()
def second_trainer(db) -> User:
    """Segundo trainer para testes de isolamento multi-tenant."""
    user = User(
        email="trainer2@teste.pt",
        hashed_password=hash_password("Trainer123!"),
        full_name="Segundo Trainer",
        role="trainer",
        is_active=True,
    )
    db.add(user)
    db.flush()
 
    sub = TrainerSubscription(
        trainer_user_id=user.id,
        status=SubscriptionStatus.ACTIVE,
        tier=SubscriptionTier.FREE,
        active_clients_count=0,
    )
    db.add(sub)
    db.flush()
    return user
 
 
@pytest.fixture()
def client_record(db, trainer_user) -> Client:
    """Registo de cliente associado ao trainer_user."""
    c = Client(
        full_name="Cliente Teste",
        phone="912345678",
        email="cliente@teste.pt",
        birth_date=date(1995, 5, 15),
        owner_trainer_id=trainer_user.id,
    )
    db.add(c)
    db.flush()
    return c
 
 
@pytest.fixture()
def client_user(db, trainer_user, client_record) -> User:
    """Utilizador com role=client associado ao client_record."""
    user = User(
        email="clienteuser@teste.pt",
        hashed_password=hash_password("Cliente123!"),
        full_name="Cliente Teste",
        role="client",
        is_active=True,
        client_id=client_record.id,
    )
    db.add(user)
    db.flush()
    return user
 
 
@pytest.fixture()
def supplement_in_db(db, trainer_user) -> Supplement:
    """Suplemento no catalogo do trainer_user - pronto para testes de atribuicao."""
    s = Supplement(
        name="Creatina Monohidratada",
        description="Aumenta a forca e recuperacao",
        serving_size="5g",
        timing="Pos-treino",
        created_by_user_id=trainer_user.id,
    )
    db.add(s)
    db.flush()
    return s
 
 
# =============================================================================
# FIXTURES DE HEADERS HTTP
# =============================================================================
 
@pytest.fixture()
def trainer_headers(trainer_user, db) -> dict:
    """
    Headers autenticados como trainer.
    Persiste o token em active_tokens para que get_current_user o aceite.
    """
    from datetime import timedelta, timezone, datetime
    token = create_access_token(
        subject=trainer_user.id,
        role="trainer",
        full_name=trainer_user.full_name,
    )
    # Persistir na active_tokens -- necessario porque get_current_user
    # verifica a existencia do token na BD antes de autenticar
    active_token = ActiveToken(
        user_id=trainer_user.id,
        token=token,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=60),
    )
    db.add(active_token)
    db.flush()
    return {
        "Authorization": f"Bearer {token}",
        "X-API-Key": settings.api_key,
    }
 
 
@pytest.fixture()
def second_trainer_headers(second_trainer, db) -> dict:
    """Headers do segundo trainer - para testes de multi-tenancy."""
    from datetime import timedelta, timezone, datetime
    token = create_access_token(
        subject=second_trainer.id,
        role="trainer",
        full_name=second_trainer.full_name,
    )
    active_token = ActiveToken(
        user_id=second_trainer.id,
        token=token,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=60),
    )
    db.add(active_token)
    db.flush()
    return {
        "Authorization": f"Bearer {token}",
        "X-API-Key": settings.api_key,
    }
 
 
@pytest.fixture()
def client_headers(client_user, db) -> dict:
    """Headers autenticados como cliente."""
    from datetime import timedelta, timezone, datetime
    token = create_access_token(
        subject=client_user.id,
        role="client",
        full_name=client_user.full_name,
        client_id=client_user.client_id,
    )
    active_token = ActiveToken(
        user_id=client_user.id,
        token=token,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=60),
    )
    db.add(active_token)
    db.flush()
    return {
        "Authorization": f"Bearer {token}",
        "X-API-Key": settings.api_key,
    }
 
 
@pytest.fixture()
def api_key_headers() -> dict:
    """Apenas API Key - para endpoints publicos."""
    return {"X-API-Key": settings.api_key}
