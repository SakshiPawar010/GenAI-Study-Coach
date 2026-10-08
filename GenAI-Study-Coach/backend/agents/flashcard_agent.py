import json
from service.document_processor import DocumentProcessor
from service.langchain_client import build_chain, invoke_chain

_PROMPT = """\
Generate exactly 8 flashcards from the following study notes.
Each flashcard should have a clear question on the front and a concise answer on the back.

Study Notes:
{text}

Return ONLY valid JSON in this exact format:
{{
  "flashcards": [
    {{
      "front": "Question or term here?",
      "back": "Clear, concise answer here"
    }}
  ]
}}

Generate 8 flashcards covering the most important concepts:\
"""


class FlashcardAgent:
    def __init__(self):
        self.doc_processor = DocumentProcessor()
        self._chain = build_chain(_PROMPT, max_tokens=1500, temperature=0.7)

    def generate_flashcards(self, text):
        if len(text) > 8000:
            chunks = self.doc_processor.chunk_text(text, max_chars=8000)
            text = chunks[0]

        response = invoke_chain(self._chain, {"text": text})

        try:
            return json.loads(response)
        except Exception:
            start, end = response.find("{"), response.rfind("}") + 1
            if start != -1 and end > start:
                return json.loads(response[start:end])
            raise ValueError("Failed to parse flashcards JSON")
