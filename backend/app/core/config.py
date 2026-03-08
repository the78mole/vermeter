from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://rental:rental_secret@localhost:5432/rental_manager"

    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"

    # OIDC / Keycloak
    # Internal URL used by the backend container to fetch JWKS (Docker-internal)
    KEYCLOAK_INTERNAL_URL: str = "http://localhost/auth"
    KEYCLOAK_REALM: str = "rental"
    # Whether to strictly verify the 'iss' claim in access tokens.
    # Set to False when the public Keycloak URL (used in token iss) differs from
    # the internal Docker URL (used to fetch JWKS) – typical in development.
    KEYCLOAK_VERIFY_ISS: bool = False

    # Service account used by the backend to call the Keycloak Admin REST API
    # (create/manage user accounts on behalf of the platform admin).
    KEYCLOAK_ADMIN_CLIENT_ID: str = "rental-backend"
    KEYCLOAK_ADMIN_CLIENT_SECRET: str = "backend_service_secret"

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

    # S3-compatible object storage (RustFS / MinIO / AWS S3)
    S3_ENDPOINT_URL: str = "http://rustfs:9000"
    S3_ACCESS_KEY: str = "rustfsadmin"
    S3_SECRET_KEY: str = "rustfs_secret"
    S3_BUCKET_DOCUMENTS: str = "landlord-documents"
    S3_REGION: str = "us-east-1"

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


settings = Settings()
