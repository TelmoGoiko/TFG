from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "TFG API"
    env: str = "development"
    database_url: str = "postgresql+psycopg://tfg_user:tfg_password@localhost:5432/tfg_db"
    mattin_api_url: str 
    mattin_api_key: str
    mattin_app_id: str 
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
