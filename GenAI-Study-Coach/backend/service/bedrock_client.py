from google import genai
from google.genai import types
from .config import GEMINI_API_KEY, MODEL_ID


class BedrockClient:
    """Drop-in replacement using Gemini — same invoke() interface as before."""

    def __init__(self):
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self.model  = MODEL_ID

    def invoke(self, prompt, max_tokens=500, temperature=1.0):
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                max_output_tokens=max_tokens,
                temperature=temperature,
            )
        )
        return response.text
