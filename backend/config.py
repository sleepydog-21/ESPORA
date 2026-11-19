import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql://espora_user:espora_password@localhost:5432/espora_db"
    secret_key: str = "supersecretkey_change_in_production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24
    mail_server: str = "localhost"
    mail_port: int = 1025
    mail_sender: str = "noreply@espora.unam.mx"

    # LimeSurvey Connector Settings (C3 Infra or Direct)
    limesurvey_api_url: str = "https://lsapi.c3.unam.mx"
    limesurvey_api_key: str = ""
    limesurvey_rpc_url: str = "https://ls-test.c3.unam.mx/admin/remotecontrol"
    limesurvey_username: str = "tabare"
    limesurvey_password: str = ""
    limesurvey_default_sid: str = "118334"
    limesurvey_webhook_secret: str = "supersecret123"

    class Config:
        env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")

settings = Settings()
