"""Application configuration for MarketingLabAI."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"

DATABASE_FOLDER = PROJECT_ROOT / "database"
OUTPUT_FOLDER = PROJECT_ROOT / "outputs"
ASSETS_FOLDER = PROJECT_ROOT / "assets"
PROMPTS_FOLDER = PROJECT_ROOT / "prompts"


@dataclass(frozen=True)
class Settings:
    project_root: Path
    gemini_api_key: str
    gemini_model: str
    database_folder: Path
    output_folder: Path
    assets_folder: Path
    prompts_folder: Path


def create_required_folders():
    for folder in (
        DATABASE_FOLDER,
        OUTPUT_FOLDER,
        ASSETS_FOLDER,
        PROMPTS_FOLDER,
    ):
        folder.mkdir(parents=True, exist_ok=True)


def load_settings():
    # Local development may use .env. Hosted environments supply the same
    # contract through Secret Manager and environment variables, so a container
    # must never require a source-tree .env file.
    if ENV_FILE.exists():
        load_dotenv(ENV_FILE)

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    model = os.getenv("GEMINI_MODEL", "gemini-3.6-flash").strip()

    if not api_key:
        raise ValueError("GEMINI_API_KEY is missing.")

    create_required_folders()

    return Settings(
        project_root=PROJECT_ROOT,
        gemini_api_key=api_key,
        gemini_model=model,
        database_folder=DATABASE_FOLDER,
        output_folder=OUTPUT_FOLDER,
        assets_folder=ASSETS_FOLDER,
        prompts_folder=PROMPTS_FOLDER,
    )
