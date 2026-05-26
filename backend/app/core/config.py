from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    project_name: str = "ML-RainOps API"
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60
    cors_origins: list[str] = ["http://localhost:5173"]
    demo_username: str = "operador"
    demo_password: str = "rainops-dev"
    demo_full_name: str = "Operador CEML"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
