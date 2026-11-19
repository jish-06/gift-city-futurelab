from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "FXNexus"
    app_env: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:5173"
    database_url: str = "sqlite:///./fxnexus.db"
    seed_demo_data: bool = True
    zoho_client_id: str = ""
    zoho_client_secret: str = ""
    zoho_refresh_token: str = ""
    zoho_organization_id: str = ""
    zoho_accounts_url: str = "https://accounts.zoho.in"
    zoho_api_base_url: str = "https://www.zohoapis.in/books/v3"
    zoho_redirect_uri: str = "http://localhost:8000/api/integrations/zoho/callback"
    twelve_data_api_key: str = ""
    twelve_data_base_url: str = "https://api.twelvedata.com"
    openai_api_key: str = ""
    openai_model: str = "gpt-6-mini"
    demo_maker_email: str = "maker@fxnexus.local"
    demo_maker_password: str = "Maker-Demo-2026!"
    demo_checker_email: str = "checker@fxnexus.local"
    demo_checker_password: str = "Checker-Demo-2026!"
    demo_session_hours: int = 8
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_list(self):
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]

settings = Settings()
