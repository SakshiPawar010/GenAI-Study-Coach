import json
from service.langchain_client import build_chain, invoke_chain

_PROMPT = """\
Analyze this study content and return a JSON object with exactly these fields:
- "topic": short subject name (e.g. "AWS", "Python", "Jenkins", "Machine Learning", "Biology")
- "subtopic": more specific area (e.g. "CI/CD Pipelines", "Data Structures", "Neural Networks")
- "emoji": one relevant emoji for the topic
{filename_hint}
Return ONLY valid JSON, no extra text:
{{"topic": "...", "subtopic": "...", "emoji": "..."}}

Content:
{text}\
"""


class TopicDetector:
    def __init__(self):
        self._chain = build_chain(_PROMPT, max_tokens=100, temperature=0.2)

    def detect(self, text, filename=None):
        try:
            response = invoke_chain(self._chain, {
                "text": text[:4000],
                "filename_hint": f'\nFilename hint: "{filename}"' if filename else "",
            })
            start, end = response.find("{"), response.rfind("}") + 1
            result = json.loads(response[start:end])
            if result.get("topic", "").lower() in ("general", "study notes", "") and filename:
                result["topic"] = filename.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").title()
            return result
        except Exception:
            if filename:
                return {"topic": filename.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").title(), "subtopic": "Study Notes", "emoji": "📚"}
            return {"topic": "General", "subtopic": "Study Notes", "emoji": "📚"}
