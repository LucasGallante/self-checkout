from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = (
        "postgresql+psycopg2://selfcheckout:selfcheckout@localhost:5432/selfcheckout"
    )


settings = Settings()
