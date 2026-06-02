from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_DIR = BACKEND_DIR.parent
ENV_FILE = REPO_DIR / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = Field(default="MeetIQ", alias="APP_NAME")
    app_version: str = "0.1.0"
    app_env: str = Field(default="development", alias="APP_ENV")
    api_base_url: str = Field(default="http://localhost:8000", alias="API_BASE_URL")
    frontend_base_url: str = Field(default="http://localhost:3000", alias="FRONTEND_BASE_URL")
    teams_bot_base_url: str = Field(default="", alias="TEAMS_BOT_BASE_URL")
    cors_allowed_origins_raw: str = Field(
        default="http://localhost:3000",
        alias="CORS_ALLOWED_ORIGINS",
    )

    backend_secret_key: str = Field(default="", alias="BACKEND_SECRET_KEY")
    bot_internal_api_key: str = Field(default="", alias="BOT_INTERNAL_API_KEY")
    dev_user_id: str = Field(default="", alias="DEV_USER_ID")
    auth_required: bool = Field(default=False, alias="AUTH_REQUIRED")
    allow_dev_user_fallback: bool = Field(default=True, alias="ALLOW_DEV_USER_FALLBACK")
    enable_microsoft_onboarding: bool = Field(
        default=False,
        alias="ENABLE_MICROSOFT_ONBOARDING",
    )

    supabase_url: str = Field(default="", alias="SUPABASE_URL")
    supabase_anon_key: str = Field(default="", alias="SUPABASE_ANON_KEY")
    supabase_service_role_key: str = Field(default="", alias="SUPABASE_SERVICE_ROLE_KEY")
    supabase_jwt_secret: str = Field(default="", alias="SUPABASE_JWT_SECRET")
    database_url: str = Field(default="", alias="DATABASE_URL")

    enable_ai_summaries: bool = Field(default=False, alias="ENABLE_AI_SUMMARIES")
    enable_ai_chat: bool = Field(default=False, alias="ENABLE_AI_CHAT")
    enable_bot_internal_apis: bool = Field(default=True, alias="ENABLE_BOT_INTERNAL_APIS")
    azure_openai_api_key: str = Field(default="", alias="AZURE_OPENAI_API_KEY")
    azure_openai_endpoint: str = Field(default="", alias="AZURE_OPENAI_ENDPOINT")
    azure_openai_api_version: str = Field(default="2024-02-01", alias="AZURE_OPENAI_API_VERSION")
    azure_openai_deployment: str = Field(default="", alias="AZURE_OPENAI_DEPLOYMENT")
    azure_openai_embedding_deployment: str = Field(
        default="",
        alias="AZURE_OPENAI_EMBEDDING_DEPLOYMENT",
    )
    azure_speech_key: str = Field(default="", alias="AZURE_SPEECH_KEY")
    azure_speech_region: str = Field(default="", alias="AZURE_SPEECH_REGION")
    azure_speech_api_version: str = Field(
        default="2025-10-15",
        alias="AZURE_SPEECH_API_VERSION",
    )
    azure_speech_default_language: str = Field(
        default="en-IN",
        alias="AZURE_SPEECH_DEFAULT_LANGUAGE",
    )
    azure_ai_search_endpoint: str = Field(default="", alias="AZURE_AI_SEARCH_ENDPOINT")
    azure_ai_search_api_key: str = Field(default="", alias="AZURE_AI_SEARCH_API_KEY")
    azure_ai_search_index: str = Field(
        default="meeting-transcript-chunks",
        alias="AZURE_AI_SEARCH_INDEX",
    )
    azure_ai_search_api_version: str = Field(
        default="2025-09-01",
        alias="AZURE_AI_SEARCH_API_VERSION",
    )
    azure_storage_connection_string: str = Field(
        default="",
        alias="AZURE_STORAGE_CONNECTION_STRING",
    )
    azure_media_container: str = Field(
        default="meeting-transcripts",
        alias="AZURE_MEDIA_CONTAINER",
    )
    azure_media_prefix: str = Field(
        default="uploaded-media",
        alias="AZURE_MEDIA_PREFIX",
    )
    uploaded_recordings_dir: str = Field(
        default="uploaded_recordings",
        alias="UPLOADED_RECORDINGS_DIR",
    )
    azure_openai_embedding_dimensions: int = Field(
        default=1536,
        alias="AZURE_OPENAI_EMBEDDING_DIMENSIONS",
    )
    task_email_enabled: bool = Field(default=False, alias="TASK_EMAIL_ENABLED")
    task_smtp_host: str = Field(default="", alias="TASK_SMTP_HOST")
    task_smtp_port: int = Field(default=587, alias="TASK_SMTP_PORT")
    task_smtp_username: str = Field(default="", alias="TASK_SMTP_USERNAME")
    task_smtp_password: str = Field(default="", alias="TASK_SMTP_PASSWORD")
    task_smtp_from_address: str = Field(default="", alias="TASK_SMTP_FROM_ADDRESS")
    task_smtp_from_name: str = Field(default="MeetIQ", alias="TASK_SMTP_FROM_NAME")
    task_smtp_enable_tls: bool = Field(default=True, alias="TASK_SMTP_ENABLE_TLS")

    @property
    def enable_docs(self) -> bool:
        return self.app_env.lower() != "production"

    @property
    def cors_allowed_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_allowed_origins_raw.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
