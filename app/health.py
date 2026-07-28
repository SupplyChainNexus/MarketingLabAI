"""MarketingLabAI system health check."""

from app.ai.gemini_client import get_gemini_client
from app.brands.brand_service import BrandService
from app.config import load_settings
from app.services.json_storage import JsonStorage


def run_health_check(include_api_test: bool = False) -> None:
    settings = load_settings()

    print("MarketingLabAI Health Check")
    print("---------------------------")
    print(f"Project root: {settings.project_root}")
    print(f"Gemini model: {settings.gemini_model}")
    print(f"API key loaded: {bool(settings.gemini_api_key)}")

    required_folders = (
        settings.database_folder,
        settings.output_folder,
        settings.assets_folder,
        settings.prompts_folder,
    )

    for folder in required_folders:
        print(f"Folder available: {folder}")

    JsonStorage(settings.database_folder / "health")
    BrandService(settings)

    print("Storage service: healthy")
    print("Brand service: healthy")

    if include_api_test:
        client = get_gemini_client()
        response = client.generate_text(
            "Reply with exactly: MarketingLabAI API healthy"
        )
        print(f"Gemini response: {response}")

    print("---------------------------")
    print("Core system healthy")


if __name__ == "__main__":
    run_health_check(include_api_test=False)
