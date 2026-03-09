from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    app_name: str = "landright-api"
    environment: str = "dev"
    
    # GCP Project (for Vertex AI, Secret Manager, etc.)
    gcp_project: str = ""
    
    # Database - supports both local and Cloud SQL
    database_url: str = ""
    database_host: str = "127.0.0.1"
    database_port: int = 5432
    database_name: str = "landright"
    database_user: str = "landright"
    database_password: str = "landright"
    
    # Redis
    redis_url: str = ""
    redis_host: str = "127.0.0.1"
    redis_port: int = 6379
    
    # Cloud Storage
    evidence_bucket: str = "local-evidence"
    
    # Observability
    enable_otlp: bool = False
    
    # CORS
    allowed_origins: list[str] = ["*"]
    
    # JWT Authentication
    jwt_secret: str = "dev-secret-change-in-production"
    jwt_audience: str = "landright"
    jwt_issuer: str = "https://auth.landright.local"
    
    # Session & Encryption
    session_secret: str = "dev-session-secret"
    encryption_key: str = "dev-encryption-key-32chars!!"
    
    # Vertex AI / Gemini Configuration
    gemini_model: str = "gemini-1.5-flash-001"
    gemini_location: str = "us-central1"
    gemini_enabled: bool = True
    gemini_max_output_tokens: int = 2048
    gemini_temperature: float = 0.2  # Low temp for legal documents
    
    # RAG / Vector Store Configuration
    rag_enabled: bool = True
    rag_collection_name: str = "landright_legal_kb"
    rag_persist_directory: str = "./chroma_db"
    rag_embedding_model: str = "text-embedding-004"
    rag_top_k: int = 5  # Number of documents to retrieve
    rag_min_relevance_score: float = 0.7  # Minimum similarity threshold
    
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

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }
    
    @property
    def effective_database_url(self) -> str:
        """Build database URL from components or use explicit URL."""
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+psycopg://{self.database_user}:{self.database_password}"
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
        return bool(self.sendgrid_api_key and not self.sendgrid_api_key.startswith("PLACEHOLDER"))
    
    @property
    def twilio_configured(self) -> bool:
        """Check if Twilio is properly configured."""
        return bool(
            self.twilio_account_sid 
            and self.twilio_auth_token 
            and self.twilio_from_number
            and not self.twilio_account_sid.startswith("PLACEHOLDER")
        )
    
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
