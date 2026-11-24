"""Runtime settings (file locations), overridable with REPORT_GENERATOR_* env vars."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="REPORT_GENERATOR_")

    config_path: Path = PROJECT_ROOT / "config" / "config.json"
    database_path: Path = PROJECT_ROOT / "data" / "report_generator.db"
    host: str = "127.0.0.1"
    port: int = 8000

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.database_path.as_posix()}"
