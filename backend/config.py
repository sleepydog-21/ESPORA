from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql://espora_user:espora_password@localhost:5432/espora_db"
    secret_key: str = "supersecretkey_change_in_production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24
    mail_server: str = "localhost"
    mail_port: int = 1025
    mail_sender: str = "noreply@espora.unam.mx"

    class Config:
        env_file = ".env"

settings = Settings()
