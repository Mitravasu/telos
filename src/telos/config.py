"""Environment-backed application settings."""

from dataclasses import dataclass
import os


DEFAULT_DATABASE_URL = "postgresql+psycopg://telos:telos@localhost:5432/telos"


def database_url_from_env() -> str:
    return os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)


@dataclass(frozen=True)
class Settings:
    database_url: str
    ollama_base_url: str
    ollama_model: str
    ollama_api_key: str | None = None

    @property
    def checkpoint_database_url(self) -> str:
        """Psycopg connection URL used exclusively by PostgresSaver."""
        return self.database_url.replace("postgresql+psycopg://", "postgresql://", 1)

    @classmethod
    def from_env(cls) -> "Settings":
        model = os.environ.get("OLLAMA_MODEL")
        if not model:
            raise RuntimeError("OLLAMA_MODEL must be set")
        return cls(
            database_url=database_url_from_env(),
            ollama_base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
            ollama_model=model,
            ollama_api_key=os.environ.get("OLLAMA_API_KEY") or None,
        )
