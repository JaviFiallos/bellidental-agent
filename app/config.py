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
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""
    llm_timeout_seconds: float = 8.0
    wa_reminder_template: str = "recordatorio_cita"
    wa_template_language: str = "es"
    reminder_interval_seconds: int = 300
    reminders_enabled: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
