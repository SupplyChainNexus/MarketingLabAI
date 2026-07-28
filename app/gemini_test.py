import os

from dotenv import load_dotenv
from google import genai

# Load variables from the .env file
load_dotenv()

# Read the API key
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("No GEMINI_API_KEY found in the .env file.")

# Create the Gemini client
client = genai.Client(api_key=api_key)

# Ask Gemini a question
response = client.models.generate_content(
    model="gemini-3.6-flash",
    contents="Say hello to Delight and welcome him to building MarketingLabAI.",
)

print("\nGemini replied:\n")
print(response.text)
