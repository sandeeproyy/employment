"""Direct test of the Gemini API from inside the container."""
import os
import sys
sys.path.insert(0, "/app")

import google.generativeai as genai

api_key = os.environ.get("GEMINI_API_KEY", "")
model_name = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

print(f"API Key (first 15 chars): {api_key[:15]}")
print(f"Model: {model_name}")

genai.configure(api_key=api_key)

try:
    model = genai.GenerativeModel(model_name)
    response = model.generate_content(
        "Say hello in one sentence.",
        generation_config=genai.GenerationConfig(
            temperature=0.3,
        )
    )
    print(f"SUCCESS: {response.text}")
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
