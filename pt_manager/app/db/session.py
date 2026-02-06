from sqlmodel import Session, create_engine
from app.core.config import settings


#Postgre SQL com Dbeaver para visualizar
engine = create_engine(settings.database_url, echo=False, connect_args={"check_same_thread" : False} if settings.database_url.startswith("sqlite") else {})

def get_session():
    """
    Dependency FastAPI that will return a database session
    Garante uma sessão por request
    """
    with Session(engine) as session:
        yield session