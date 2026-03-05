from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://rental:rental_secret@localhost:5432/rental_manager"

    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"

    # OIDC / Keycloak
    # Internal URL used by the backend container to fetch JWKS (Docker-internal)
    KEYCLOAK_INTERNAL_URL: str = "http://localhost:8081"
    KEYCLOAK_REALM: str = "rental"
    # Whether to strictly verify the 'iss' claim in access tokens.
    # Set to False when the public Keycloak URL (used in token iss) differs from
    # the internal Docker URL (used to fetch JWKS) – typical in development.
    KEYCLOAK_VERIFY_ISS: bool = False

    @property
    def keycloak_jwks_url(self) -> str:
        return f"{self.KEYCLOAK_INTERNAL_URL}/realms/{self.KEYCLOAK_REALM}/protocol/openid-connect/certs"

    @property
    def keycloak_issuer_suffix(self) -> str:
        """Expected suffix of the 'iss' claim: /realms/<realm>"""
        return f"/realms/{self.KEYCLOAK_REALM}"

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
