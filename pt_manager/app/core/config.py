from pydantic_settings import BaseSettings

class Settings(BaseSettings):

    """
    Configurações da aplicação

    database_url:
    - SQlite local: "sqlite:///./pt_manager.db"
    - Futuro PostgreSQL: "postgresql+asyncpg://user:pass@host:5432/dbname"
    """
    database_url: str = "sqlite:///./pt_manager.db"
    api_key: str = "infoapirequestmanager258634"
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()