from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "TFG API"
    env: str = "development"
    database_url: str = "postgresql+psycopg://tfg_user:tfg_password@localhost:5432/tfg_db"
    mattin_api_url: str
    mattin_api_key: str
    mattin_app_id: str
    mattin_document_writer_agent_id: int | None = None
    mattin_document_splitter_agent_id: int | None = None
    mattin_block_chat_agent_id: int | None = None
    mattin_block_impact_agent_id: int | None = None
    mattin_block_relationship_agent_id: int | None = None
    mattin_block_rewrite_agent_id: int | None = None
    mattin_document_wide_agent_id: int | None = None
    mattin_generation_timeout_seconds: int = 180
    mattin_generation_max_retries: int = 1
    mcp_server_name: str = "tfg-docs-tools"
    mcp_server_token: str | None = None
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator(
        "mattin_document_writer_agent_id",
        "mattin_document_splitter_agent_id",
        "mattin_block_chat_agent_id",
        "mattin_block_impact_agent_id",
        "mattin_block_relationship_agent_id",
        "mattin_block_rewrite_agent_id",
        "mattin_document_wide_agent_id",
        mode="before",
    )
    @classmethod
    def empty_string_to_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value


settings = Settings()
