from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # extra="ignore": .env also holds POSTGRES_* vars used only by the db container
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    redis_url: str
    rate_limit_per_minute: int = 10
    stats_cache_ttl: int = 30


settings = Settings()
