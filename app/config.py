from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    wa_verify_token: str = ""
    wa_app_secret: str = ""
    wa_access_token: str = ""
    wa_phone_number_id: str = ""
    wa_graph_version: str = "v23.0"
    backend_url: str = "http://localhost:8080"
    bot_api_key: str = ""
    clinic_zone: str = "America/Guayaquil"
    conversation_ttl_minutes: int = 30

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
