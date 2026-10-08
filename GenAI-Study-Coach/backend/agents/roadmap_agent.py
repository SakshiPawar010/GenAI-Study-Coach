from service.document_processor import DocumentProcessor
from service.langchain_client import build_chain, invoke_chain

_TOPIC_PROMPT = """\
List the main topics covered in this text in 2-3 bullet points:
{text}\
"""

_ROADMAP_PROMPT = """\
You are a study planner. Create a study roadmap for EXACTLY {days} days. No more, no less.

STRICT RULES:
- Output EXACTLY {days} lines
- Each line MUST start with "Day X:" where X goes from 1 to {days}
- Do NOT output Day {next_day} or beyond
- Do NOT add any intro text, headers, or extra lines

Study Notes:
{text}

Output EXACTLY {days} lines now:
{day_lines}\
"""


class RoadmapAgent:
    def __init__(self):
        self.doc_processor = DocumentProcessor()
        self._topic_chain   = build_chain(_TOPIC_PROMPT,   max_tokens=150,  temperature=0.3)
        self._roadmap_chain = build_chain(_ROADMAP_PROMPT, max_tokens=2000, temperature=0.3)

    def create_roadmap(self, text, days=7):
        days = int(days)

        if len(text) > 8000:
            chunks = self.doc_processor.chunk_text(text, max_chars=8000)
            topics = [invoke_chain(self._topic_chain, {"text": c}) for c in chunks]
            text = "Main topics to cover:\n" + "\n".join(topics)

        response = invoke_chain(self._roadmap_chain, {
            "days":     days,
            "next_day": days + 1,
            "text":     text,
            "day_lines": "\n".join(f"Day {i}: " for i in range(1, days + 1)),
        })

        lines = [l for l in response.strip().split("\n") if l.strip().startswith("Day ")]
        return "\n".join(lines[:days])
