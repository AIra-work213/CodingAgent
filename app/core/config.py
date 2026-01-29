"""Конфигурация приложения с использованием pydantic-settings"""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # API OpenRouter
    openrouter_api_key: str = Field(..., alias="OPENROUTER_API_KEY")
    openrouter_base_url: str = Field("https://openrouter.ai/api/v1", alias="OPENROUTER_BASE_URL")

    # GitHub
    github_token: str = Field(..., alias="GITHUB_TOKEN")
    github_repo: str = Field(..., alias="GITHUB_REPO")
    github_base_url: str = Field("https://api.github.com", alias="GITHUB_BASE_URL")

    # Базы данных
    redis_url: str = Field("redis://localhost:6379/0", alias="REDIS_URL")
    postgres_url: str = Field(
        "postgresql://user:password@localhost:5432/coding_agents",
        alias="POSTGRES_URL",
    )

    # API
    api_host: str = Field("0.0.0.0", alias="API_HOST")
    api_port: int = Field(8000, alias="API_PORT")
    debug: bool = Field(True, alias="DEBUG")

    # Конфигурация сервера
    public_url: str = Field("", alias="PUBLIC_URL")
    server_url: str = Field("http://localhost:8000", alias="SERVER_URL")

    # Настройки клиента (для CLI)
    client_server_url: str = Field("", alias="CODING_AGENT_SERVER")
    config_path: str = Field("~/.coding-agent", alias="CONFIG_PATH")

    # LangSmith (опционально)
    langchain_tracing_v2: bool = Field(False, alias="LANGCHAIN_TRACING_V2")
    langchain_api_key: str = Field("", alias="LANGCHAIN_API_KEY")
    langchain_project: str = Field("coding-agents", alias="LANGCHAIN_PROJECT")

    # Настройки агента
    max_iterations: int = Field(5, alias="MAX_ITERATIONS")
    agent_timeout: int = Field(120, alias="AGENT_TIMEOUT")
    code_quality_checks: bool = Field(True, alias="CODE_QUALITY_CHECKS")

    # Доступные модели
    default_model: Literal["gpt-4o-mini", "qwen-2.5-coder", "deepseek-coder"] = Field(
        "gpt-4o-mini", alias="DEFAULT_MODEL"
    )

    @property
    def owner(self) -> str:
        """Извлечь владельца репозитория GitHub"""
        return self.github_repo.split("/")[0]

    @property
    def repo_name(self) -> str:
        """Извлечь имя репозитория GitHub"""
        return self.github_repo.split("/")[1]


@lru_cache
def get_settings() -> Settings:
    """Получить кэшированный экземпляр настроек"""
    return Settings()
