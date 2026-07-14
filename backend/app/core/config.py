from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Gemini
    gemini_api_key: str

    # App
    app_env: str = "development"
    frontend_url: str = "http://localhost:5173"

    # Vector store
    vector_store: str = "chroma"
    pinecone_api_key: str = ""
    pinecone_index: str = "tubeassist"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()