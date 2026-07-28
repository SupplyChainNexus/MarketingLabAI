"""Gemini client service for MarketingLabAI."""

from google import genai

from app.config import Settings, load_settings


class GeminiClient:
    """Central Gemini API client used by MarketingLabAI."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or load_settings()
        self.client = genai.Client(api_key=self.settings.gemini_api_key)

    def generate_text(self, prompt: str) -> str:
        """Generate text from Gemini."""

        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty.")

        response = self.client.models.generate_content(
            model=self.settings.gemini_model,
            contents=prompt.strip(),
        )

        text = getattr(response, "text", None)

        if not text:
            raise RuntimeError("Gemini returned no text.")

        return text.strip()


def get_gemini_client() -> GeminiClient:
    """Create and return a configured Gemini client."""

    return GeminiClient()
