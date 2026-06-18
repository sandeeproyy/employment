import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path="/app/.env")
api_key = os.getenv("GEMINI_API_KEY")
print(f"Loaded API key: {api_key[:10]}...{api_key[-10:] if api_key else ''}")
genai.configure(api_key=api_key)

models_to_try = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash"
]

for model_name in models_to_try:
    try:
        print(f"\nTrying generate content with {model_name}...")
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Hello, respond with 'Success' if you read this.")
        print(f"Result for {model_name}: {response.text.strip()}")
    except Exception as e:
        print(f"Result for {model_name} failed: {e}")
