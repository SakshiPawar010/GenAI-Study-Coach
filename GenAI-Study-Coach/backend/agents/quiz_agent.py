import json
import random
import time
from service.document_processor import DocumentProcessor
from service.langchain_client import build_chain, invoke_chain

_HARD_PROMPT = """\
Generate exactly 5 HARD fill-in-the-blank questions STRICTLY based ONLY on the content in the study notes below.

Study Notes:
{text}

RULES:
- Questions MUST be based ONLY on topics present in the notes
- Answers MUST be short: 1-3 words only (a term, name, or keyword from the notes)
- Questions should test deep understanding of concepts IN the notes
- Make questions tricky by asking about specific details, terms, or definitions
- Variation Seed: {seed}

Return ONLY valid JSON:
{{
  "quiz": [
    {{
      "question": "The architectural style that breaks an app into small independent services is called ___?",
      "options": [],
      "answer": "Microservices"
    }}
  ]
}}

Generate 5 hard fill-in-the-blank questions with 1-3 word answers now:\
"""

_MCQ_PROMPT = """\
Generate exactly 5 multiple-choice questions based on the following study notes.

Study Notes:
{text}

Difficulty: {difficulty_instruction}
Question Style: {style}
Variation Seed: {seed}

IMPORTANT: Generate DIFFERENT questions every time. Vary difficulty and topics.

Return ONLY valid JSON:
{{
  "quiz": [
    {{
      "question": "Question text here?",
      "options": ["Option 1", "Option 2", "Option 3", "Option 4"],
      "answer": "Option 1"
    }}
  ]
}}

Do NOT include A), B), C), D) prefixes.
Generate 5 unique questions now:\
"""

_EXPLAIN_CORRECT_PROMPT = """\
For each question below, explain in 2-3 sentences WHY the correct answer is right.
Be concise and educational.

{items}

Return ONLY valid JSON:
{{"explanations": [
  {{"index": 0, "explanation": "..."}}
]}}\
"""

_EXPLAIN_WRONG_PROMPT = """\
For each question below, explain in 2-3 sentences WHY the correct answer is right and why the user's answer is wrong.
Be concise, clear, and educational.

{items}

Return ONLY valid JSON where each object has the exact 'index' value from the question (0-based integer):
{{"explanations": [
  {{"index": 0, "explanation": "..."}}
]}}\
"""


class QuizAgent:
    QUESTION_STYLES = [
        "Focus on definitions and meanings of key terms.",
        "Focus on how things work and their purposes.",
        "Focus on differences and comparisons between concepts.",
        "Focus on practical use cases and real-world examples.",
        "Focus on characteristics, features, and properties.",
        "Focus on advantages, disadvantages, and trade-offs.",
        "Focus on steps, processes, and workflows.",
        "Focus on relationships and dependencies between concepts.",
    ]

    DIFFICULTY_INSTRUCTIONS = {
        "easy":   "Generate EASY questions. Focus on basic definitions, simple facts, and straightforward concepts. Wrong options should be clearly different from the correct answer.",
        "medium": "Generate MEDIUM difficulty questions. Mix conceptual understanding with application. Wrong options should be plausible but clearly incorrect on reflection.",
        "hard":   "Generate HARD questions. Focus on deep understanding, edge cases, comparisons, and nuanced differences. Wrong options should be very similar to the correct answer and require careful thought.",
    }

    def __init__(self):
        self.doc_processor = DocumentProcessor()
        self._hard_chain           = build_chain(_HARD_PROMPT,           max_tokens=1500, temperature=0.8)
        self._mcq_chain            = build_chain(_MCQ_PROMPT,            max_tokens=1500, temperature=0.8)
        self._explain_correct_chain = build_chain(_EXPLAIN_CORRECT_PROMPT, max_tokens=1000, temperature=0.3)
        self._explain_wrong_chain   = build_chain(_EXPLAIN_WRONG_PROMPT,   max_tokens=1000, temperature=0.3)

    def generate_quiz(self, text, difficulty="medium"):
        random.seed(int(time.time()))
        style = random.choice(self.QUESTION_STYLES)
        seed  = random.randint(1, 1000)

        if len(text) > 8000:
            chunks = self.doc_processor.chunk_text(text, max_chars=8000)
            random.shuffle(chunks)
            text = chunks[0]

        if difficulty == "hard":
            response = invoke_chain(self._hard_chain, {"text": text, "seed": seed})
        else:
            response = invoke_chain(self._mcq_chain, {
                "text": text,
                "difficulty_instruction": self.DIFFICULTY_INSTRUCTIONS.get(difficulty, self.DIFFICULTY_INSTRUCTIONS["medium"]),
                "style": style,
                "seed": seed,
            })

        data = self._parse_json(response)

        # Filter out malformed questions missing required keys
        data["quiz"] = [q for q in data["quiz"] if "question" in q and "answer" in q]

        for q in data["quiz"]:
            if difficulty != "hard" and q.get("options"):
                options = [opt.split(") ", 1)[-1] if ") " in opt else opt for opt in q["options"]]
                correct = q["answer"].split(") ", 1)[-1] if ") " in q["answer"] else q["answer"]
                random.shuffle(options)
                q["options"] = [f"{chr(65+i)}) {opt}" for i, opt in enumerate(options)]
                if correct in options:
                    q["answer"] = f"{chr(65+options.index(correct))}) {correct}"

        data["difficulty"] = difficulty
        return data

    def explain_wrong_answers(self, questions, user_answers, explain_correct=False):
        if explain_correct:
            items = "\n\n".join(
                f"Q{q['index']+1}: {q['question']}\nCorrect Answer: {q['answer']}"
                for q in questions
            )
            response = invoke_chain(self._explain_correct_chain, {"items": items})
            target_qs = questions
        else:
            wrong = [q for q in questions if user_answers.get(str(q["index"])) != q["answer"]]
            if not wrong:
                return []
            items = "\n\n".join(
                f"Q{q['index']+1}: {q['question']}\nCorrect Answer: {q['answer']}\nUser answered: {user_answers.get(str(q['index']), 'No answer')}"
                for q in wrong
            )
            response = invoke_chain(self._explain_wrong_chain, {"items": items})
            target_qs = wrong

        try:
            data = self._parse_json(response)
            result = []
            for exp in data.get("explanations", []):
                if any(q["index"] == exp["index"] for q in target_qs):
                    result.append(exp)
                else:
                    result.append({"index": target_qs[len(result)]["index"], "explanation": exp["explanation"]})
            return result
        except Exception:
            return []

    def _parse_json(self, response):
        try:
            return json.loads(response)
        except Exception:
            start, end = response.find("{"), response.rfind("}") + 1
            if start != -1 and end > start:
                return json.loads(response[start:end])
            raise ValueError("Failed to parse quiz JSON")
