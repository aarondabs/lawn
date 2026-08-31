from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    database_url: str
    rachio_api_key: str | None = None

    # Phase 3 assistant (integrations/llm.py). The model is config, not code --
    # verify the current Sonnet model string when changing it. Defaults are
    # mirrored in docker-compose.yml's ${VAR:-default} fallbacks.
    anthropic_api_key: str | None = None
    llm_model: str = "claude-sonnet-5"
    # Response cap. Adaptive thinking spends from this budget too, so it must be
    # well above the visible answer length -- 2048 truncated a real answer
    # mid-sentence on the first live call.
    llm_max_tokens: int = 8192


settings = Settings()
