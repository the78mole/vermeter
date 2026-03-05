from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://rental:rental_secret@localhost:5432/rental_manager"

    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security
    SECRET_KEY: str = "change_me_in_production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Application
    ENVIRONMENT: str = "development"
    PROJECT_NAME: str = "Rental Manager"
    API_V1_STR: str = "/api/v1"

    # Uploads
    UPLOAD_DIR: str = "uploads"

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


settings = Settings()
