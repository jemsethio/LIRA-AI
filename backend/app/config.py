from pydantic_settings import BaseSettings
from pathlib import Path
import yaml

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    app_name: str = "LIRA-AI: Landscape Intelligence for Regeneration and Adaptation"
    app_version: str = "0.1.0-mvp"
    debug: bool = True

    # Paths
    config_dir: Path = BASE_DIR / "config"
    data_dir: Path = BASE_DIR / "data"
    chroma_dir: Path = BASE_DIR / "data" / "chroma"

    # LLM (optional — used for explanation layer only)
    anthropic_api_key: str = ""
    llm_model: str = "claude-sonnet-4-6"
    llm_enabled: bool = False  # set True when API key is available

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()


def load_thresholds() -> dict:
    path = settings.config_dir / "thresholds.yaml"
    with open(path) as f:
        return yaml.safe_load(f)


def load_syndromes() -> dict:
    path = settings.config_dir / "syndromes.yaml"
    with open(path) as f:
        data = yaml.safe_load(f)
    return data.get("syndromes", {})


THRESHOLDS = load_thresholds()
SYNDROMES = load_syndromes()
