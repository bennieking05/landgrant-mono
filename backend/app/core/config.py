from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional
from urllib.parse import quote_plus

# Sentinel values shipped for local development; if we ever see them outside
# of ``environment == "dev"`` we abort startup so we never leak a well-known
# secret into prod.  See ``Settings.validate_prod_secrets``.
_DEV_SENTINEL_SECRETS = {
    "dev-secret-change-in-production",
    "dev-session-secret",
    "dev-encryption-key-32chars!!",
}


class Settings(BaseSettings):
    app_name: str = "landgrant-api"
    environment: str = "dev"

    # GCP Project (for Vertex AI, Secret Manager, etc.)
    gcp_project: str = ""

    # Database - supports both local and Cloud SQL
    database_url: str = ""
    database_host: str = "127.0.0.1"
    database_port: int = 5432
    database_name: str = "landgrant"
    database_user: str = "landgrant"
    database_password: str = "landgrant"
    alembic_auto: bool = False
    database_required: bool = False

    # Redis
    redis_url: str = ""
    redis_host: str = "127.0.0.1"
    redis_port: int = 6379

    # Cloud Storage
    evidence_bucket: str = "local-evidence"

    # Observability
    enable_otlp: bool = False

    # CORS — restrict to known origins; override via ALLOWED_ORIGINS env var
    allowed_origins: list[str] = [
        "http://localhost:3050",
        "https://app.landgrantiq.com",
        "https://landgrantiq.com",
    ]

    # JWT Authentication
    jwt_secret: str = "dev-secret-change-in-production"
    jwt_audience: str = "landgrant"
    jwt_issuer: str = "https://auth.landgrant.local"
    jwt_algorithm: str = "HS256"
    # Seconds of clock drift we tolerate when validating JWT ``exp``/``nbf``.
    jwt_leeway_seconds: int = 30
    # Deprecated: persona is always derived from the JWT (see ``deps.py``).
    allow_persona_header: bool = False

    # Session & Encryption
    session_secret: str = "dev-session-secret"
    encryption_key: str = "dev-encryption-key-32chars!!"

    # Rate limiting (slowapi).  Expressed as a slowapi expression such as
    # ``"60/minute"``; empty string disables the middleware entirely.
    rate_limit_default: str = "120/minute"
    rate_limit_ai: str = "30/minute"
    rate_limit_enabled: bool = True

    # Vertex AI / Gemini Configuration
    gemini_model: str = "gemini-1.5-flash-001"
    gemini_location: str = "us-central1"
    gemini_enabled: bool = True
    gemini_max_output_tokens: int = 2048
    gemini_temperature: float = 0.2  # Low temp for legal documents

    # RAG / Vector Store Configuration
    rag_enabled: bool = True
    rag_collection_name: str = "landgrant_legal_kb"
    rag_persist_directory: str = "./chroma_db"
    rag_embedding_model: str = "text-embedding-004"
    rag_top_k: int = 5  # Number of documents to retrieve
    rag_min_relevance_score: float = 0.7  # Minimum similarity threshold
    # ChromaDB can run as a sidecar service (docker-compose) or as an
    # embedded persistent client.  ``rag_chroma_mode`` = "http" talks to
    # ``rag_chroma_host:rag_chroma_port`` so /chroma_db is durable across
    # restarts.  "persistent" uses PersistentClient in-process.
    rag_chroma_mode: str = "persistent"  # persistent | http
    rag_chroma_host: str = "chroma"
    rag_chroma_port: int = 8000

    # Notifications / integrations
    notifications_mode: str = "preview"  # preview | send

    # SendGrid (email)
    sendgrid_api_key: Optional[str] = None

    # Twilio (SMS)
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_from_number: Optional[str] = None

    # DocuSign (e-signatures)
    docusign_integration_key: Optional[str] = None
    docusign_secret_key: Optional[str] = None
    docusign_account_id: Optional[str] = None
    docusign_base_url: str = "https://demo.docusign.net/restapi"  # Use demo for testing

    # Jira
    jira_api_key: Optional[str] = None

    # Milestone 1 contract: ``projects.state`` CHECK (TX, IN) — single source for UI
    contract_jurisdiction_codes: list[str] = ["TX", "IN"]

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    @property
    def effective_database_url(self) -> str:
        """Build database URL from components or use explicit URL."""
        if self.database_url:
            return self.database_url
        user = quote_plus(self.database_user)
        password = quote_plus(self.database_password)
        return (
            f"postgresql+psycopg://{user}:{password}"
            f"@{self.database_host}:{self.database_port}/{self.database_name}"
        )

    @property
    def effective_redis_url(self) -> str:
        """Build Redis URL from components or use explicit URL."""
        if self.redis_url:
            return self.redis_url
        return f"redis://{self.redis_host}:{self.redis_port}/0"

    @property
    def sendgrid_configured(self) -> bool:
        """Check if SendGrid is properly configured."""
        return bool(
            self.sendgrid_api_key
            and not self.sendgrid_api_key.startswith("PLACEHOLDER")
        )

    @property
    def twilio_configured(self) -> bool:
        """Check if Twilio is properly configured."""
        return bool(
            self.twilio_account_sid
            and self.twilio_auth_token
            and self.twilio_from_number
            and not self.twilio_account_sid.startswith("PLACEHOLDER")
        )

    def validate_prod_secrets(self) -> list[str]:
        """Return a list of configuration problems for non-dev environments.

        Callers (currently :mod:`app.main`) treat a non-empty list as a fatal
        startup error so we never boot a prod container with the built-in
        development secrets still in place.
        """

        if self.environment == "dev":
            return []

        problems: list[str] = []
        if self.jwt_secret in _DEV_SENTINEL_SECRETS:
            problems.append("jwt_secret is set to a dev placeholder")
        if self.session_secret in _DEV_SENTINEL_SECRETS:
            problems.append("session_secret is set to a dev placeholder")
        if self.encryption_key in _DEV_SENTINEL_SECRETS:
            problems.append("encryption_key is set to a dev placeholder")
        if len(self.jwt_secret) < 32:
            problems.append("jwt_secret must be at least 32 characters in prod")
        return problems

    @property
    def docusign_configured(self) -> bool:
        """Check if DocuSign is properly configured."""
        return bool(
            self.docusign_integration_key
            and self.docusign_secret_key
            and not self.docusign_integration_key.startswith("PLACEHOLDER")
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
