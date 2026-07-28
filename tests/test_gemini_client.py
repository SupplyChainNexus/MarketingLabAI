"""Basic Gemini client health test."""

from app.ai.gemini_client import get_gemini_client


def main():
    client = get_gemini_client()

    response = client.generate_text(
        "Reply with exactly: MarketingLabAI Gemini client healthy"
    )

    print(response)


if __name__ == "__main__":
    main()
