from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):

    """
    Configurações da aplicação

    database_url:
    - SQlite local: "sqlite:///./pt_manager.db"
    - PostgreSQL: "postgresql+psycopg2://user:pass@host:5432/dbname"
    """

    #pydantic Settings v2
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive= False)

    database_url: str = "postgresql+psycopg2://pt_user:Leandro44@localhost:5432/pt_manager"
    api_key: str = "1234"

    #---Notificações---

    timezone: str = "Europe/Lisbon" #Definir o fuso horário para as notificações
    reminder_hour_local: int = 9 #Hora local para enviar as notificações (0-23)

    trainer_email: str | None = None #Email do treinador para receber notificações

    #---- Servidor de email ----

    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_use_tls: bool = True
    smtp_from_email: str | None = None

    #--- twilio Whatsapp ---
    twilio_account_sid: str | None = None
    twilio_auth_token: str | None = None
    twilio_whatsapp_from: str | None = None #Número do remetente no formato "whatsapp:+1234567890"

settings = Settings()