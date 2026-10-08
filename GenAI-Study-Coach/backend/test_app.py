"""
Full Application Test Suite
============================
Tests every layer: services, LangChain client, all agents, LangGraph orchestrator, Flask API routes.
Run from the backend directory:
    python -m pytest test_app.py -v
"""

import sys
import os
import json
import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── Sample study text used across all tests ──────────────────────────────────
SAMPLE_TEXT = """
Machine Learning is a subset of Artificial Intelligence that enables systems to learn from data.

Supervised Learning uses labeled training data to learn a mapping from inputs to outputs.
Common algorithms include Linear Regression, Decision Trees, and Neural Networks.

Unsupervised Learning finds hidden patterns in unlabeled data.
Clustering algorithms like K-Means group similar data points together.

Reinforcement Learning trains agents to make decisions by rewarding correct actions.
It is widely used in robotics and game-playing AI systems.

Deep Learning uses multi-layered neural networks to learn complex representations.
Convolutional Neural Networks (CNNs) excel at image recognition tasks.
Recurrent Neural Networks (RNNs) are designed for sequential data like text and speech.

Overfitting occurs when a model learns noise in training data and performs poorly on new data.
Regularization techniques like Dropout and L2 help prevent overfitting.
"""


# ═══════════════════════════════════════════════════════════════════════════════
# 1. SERVICE LAYER
# ═══════════════════════════════════════════════════════════════════════════════

class TestDocumentProcessor:
    def setup_method(self):
        from service.document_processor import DocumentProcessor
        self.dp = DocumentProcessor()

    def test_chunk_text_short(self):
        chunks = self.dp.chunk_text("Short text", max_chars=8000)
        assert len(chunks) == 1
        assert chunks[0] == "Short text"

    def test_chunk_text_long(self):
        long_text = "paragraph\n\n" * 200
        chunks = self.dp.chunk_text(long_text, max_chars=500)
        assert len(chunks) > 1
        for c in chunks:
            assert len(c) <= 600  # allow slight overflow at paragraph boundary

    def test_chunk_text_overlap(self):
        text = ("word " * 100 + "\n\n") * 10
        chunks = self.dp.chunk_text(text, max_chars=300, overlap=50)
        assert len(chunks) > 1


class TestConfig:
    def test_config_loads(self):
        from service.config import AWS_REGION, MODEL_ID
        assert AWS_REGION is not None
        assert MODEL_ID is not None
        assert len(AWS_REGION) > 0
        assert len(MODEL_ID) > 0


class TestDocCache:
    def setup_method(self):
        from service.doc_cache import set_cached, get_cached, clear_cache
        self.set_cached = set_cached
        self.get_cached = get_cached
        self.clear_cache = clear_cache
        self.uid = "test-user-cache"

    def test_set_and_get(self):
        self.set_cached("key123", "summary", {"summary": "test summary"}, self.uid)
        result = self.get_cached("key123", "summary", self.uid)
        assert result is not None
        assert result["summary"] == "test summary"

    def test_cache_miss(self):
        result = self.get_cached("nonexistent_key_xyz", "summary", self.uid)
        assert result is None

    def test_clear_cache(self):
        self.set_cached("key_to_clear", "summary", {"summary": "data"}, self.uid)
        self.clear_cache(self.uid)
        result = self.get_cached("key_to_clear", "summary", self.uid)
        assert result is None


class TestProgressStore:
    def setup_method(self):
        from service.progress_store import init_db, record_quiz, get_history, clear_history
        init_db()
        self.record_quiz = record_quiz
        self.get_history = get_history
        self.clear_history = clear_history
        self.uid = "test-user-progress"
        clear_history(self.uid)

    def test_record_and_retrieve(self):
        self.record_quiz(self.uid, "Machine Learning", 4, 5, "medium")
        history = self.get_history(self.uid)
        assert len(history) >= 1
        assert history[0]["topic"] == "Machine Learning"
        assert history[0]["score"] == 4

    def test_clear_history(self):
        self.record_quiz(self.uid, "Python", 3, 5, "easy")
        self.clear_history(self.uid)
        history = self.get_history(self.uid)
        assert history == []


# ═══════════════════════════════════════════════════════════════════════════════
# 2. LANGCHAIN CLIENT
# ═══════════════════════════════════════════════════════════════════════════════

class TestLangChainClient:
    def test_get_llm(self):
        from service.langchain_client import get_llm
        llm = get_llm(max_tokens=100, temperature=0.5)
        assert llm is not None

    def test_get_embeddings(self):
        from service.langchain_client import get_embeddings
        embeddings = get_embeddings()
        assert embeddings is not None

    def test_build_chain(self):
        from service.langchain_client import build_chain
        chain = build_chain("Say hello to {name}.", max_tokens=50, temperature=0.1)
        assert chain is not None

    def test_chain_invoke(self):
        from service.langchain_client import build_chain
        chain = build_chain("In one word, what color is the sky? Answer: {hint}", max_tokens=20, temperature=0.0)
        result = chain.invoke({"hint": "think daytime"})
        assert isinstance(result, str)
        assert len(result) > 0

    def test_build_faiss_store(self):
        from service.langchain_client import build_faiss_store
        chunks = ["Machine learning uses data.", "Deep learning uses neural networks.", "Python is a programming language."]
        store = build_faiss_store(chunks)
        assert store is not None
        results = store.similarity_search("neural networks", k=1)
        assert len(results) == 1
        assert "neural" in results[0].page_content.lower() or "deep" in results[0].page_content.lower()


# ═══════════════════════════════════════════════════════════════════════════════
# 3. AGENTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestTopicDetector:
    def setup_method(self):
        from agents.topic_detector import TopicDetector
        self.agent = TopicDetector()

    def test_detect_returns_required_keys(self):
        result = self.agent.detect(SAMPLE_TEXT)
        assert "topic" in result
        assert "subtopic" in result
        assert "emoji" in result

    def test_detect_non_empty_values(self):
        result = self.agent.detect(SAMPLE_TEXT)
        assert len(result["topic"]) > 0
        assert len(result["emoji"]) > 0

    def test_detect_with_filename(self):
        result = self.agent.detect(SAMPLE_TEXT, filename="machine_learning_notes.pdf")
        assert "topic" in result

    def test_detect_fallback_on_empty(self):
        result = self.agent.detect("", filename="python_basics.pdf")
        # LLM may still respond or fall back — either way topic must be non-empty
        assert len(result["topic"]) > 0
        assert "emoji" in result


class TestSummarizerAgent:
    def setup_method(self):
        from agents.summarizer_agent import SummarizerAgent
        self.agent = SummarizerAgent()

    def test_summarize_returns_string(self):
        result = self.agent.summarize(SAMPLE_TEXT)
        assert isinstance(result, str)
        assert len(result) > 100

    def test_summarize_contains_bold_topics(self):
        result = self.agent.summarize(SAMPLE_TEXT)
        assert "**" in result

    def test_summarize_stream(self):
        chunks = list(self.agent.summarize_stream(SAMPLE_TEXT))
        assert len(chunks) > 0
        full = "".join(chunks)
        assert len(full) > 100

    def test_summarize_multi_doc(self):
        text2 = "Python is a high-level programming language.\nIt supports object-oriented and functional programming."
        combined = SAMPLE_TEXT + "\n\n[DOCUMENT BREAK]\n\n" + text2
        result = self.agent.summarize(combined, filenames=["ml_notes.pdf", "python_notes.pdf"])
        assert isinstance(result, str)
        assert len(result) > 100


class TestQuizAgent:
    def setup_method(self):
        from agents.quiz_agent import QuizAgent
        self.agent = QuizAgent()

    def test_generate_quiz_medium(self):
        result = self.agent.generate_quiz(SAMPLE_TEXT, difficulty="medium")
        assert "quiz" in result
        assert len(result["quiz"]) == 5
        assert result["difficulty"] == "medium"

    def test_generate_quiz_hard(self):
        result = self.agent.generate_quiz(SAMPLE_TEXT, difficulty="hard")
        assert "quiz" in result
        assert len(result["quiz"]) == 5
        assert result["difficulty"] == "hard"

    def test_generate_quiz_easy(self):
        result = self.agent.generate_quiz(SAMPLE_TEXT, difficulty="easy")
        assert "quiz" in result
        assert len(result["quiz"]) == 5

    def test_quiz_question_structure_mcq(self):
        result = self.agent.generate_quiz(SAMPLE_TEXT, difficulty="medium")
        for q in result["quiz"]:
            assert "question" in q
            assert "answer" in q
            assert "options" in q
            assert len(q["options"]) == 4

    def test_quiz_question_structure_hard(self):
        result = self.agent.generate_quiz(SAMPLE_TEXT, difficulty="hard")
        for q in result["quiz"]:
            assert "question" in q
            assert "answer" in q

    def test_explain_wrong_answers(self):
        quiz = self.agent.generate_quiz(SAMPLE_TEXT, difficulty="medium")
        questions = [{"index": i, **q} for i, q in enumerate(quiz["quiz"])]
        user_answers = {str(i): "wrong answer" for i in range(len(questions))}
        explanations = self.agent.explain_wrong_answers(questions, user_answers)
        assert isinstance(explanations, list)
        assert len(explanations) > 0

    def test_explain_no_wrong_answers(self):
        quiz = self.agent.generate_quiz(SAMPLE_TEXT, difficulty="medium")
        questions = [{"index": i, **q} for i, q in enumerate(quiz["quiz"])]
        user_answers = {str(i): q["answer"] for i, q in enumerate(quiz["quiz"])}
        explanations = self.agent.explain_wrong_answers(questions, user_answers)
        assert explanations == []


class TestFlashcardAgent:
    def setup_method(self):
        from agents.flashcard_agent import FlashcardAgent
        self.agent = FlashcardAgent()

    def test_generate_flashcards_returns_8(self):
        result = self.agent.generate_flashcards(SAMPLE_TEXT)
        assert "flashcards" in result
        assert len(result["flashcards"]) == 8

    def test_flashcard_structure(self):
        result = self.agent.generate_flashcards(SAMPLE_TEXT)
        for card in result["flashcards"]:
            assert "front" in card
            assert "back" in card
            assert len(card["front"]) > 0
            assert len(card["back"]) > 0


class TestRoadmapAgent:
    def setup_method(self):
        from agents.roadmap_agent import RoadmapAgent
        self.agent = RoadmapAgent()

    def test_roadmap_7_days(self):
        result = self.agent.create_roadmap(SAMPLE_TEXT, days=7)
        lines = [l for l in result.strip().split("\n") if l.strip()]
        assert len(lines) == 7

    def test_roadmap_5_days(self):
        result = self.agent.create_roadmap(SAMPLE_TEXT, days=5)
        lines = [l for l in result.strip().split("\n") if l.strip()]
        assert len(lines) == 5

    def test_roadmap_day_format(self):
        result = self.agent.create_roadmap(SAMPLE_TEXT, days=3)
        lines = [l for l in result.strip().split("\n") if l.strip()]
        for i, line in enumerate(lines, 1):
            assert line.startswith(f"Day {i}:")


class TestChatAgent:
    def setup_method(self):
        from agents.chat_agent import ChatAgent
        self.agent = ChatAgent()

    def test_ask_returns_answer(self):
        answer = self.agent.ask("What is supervised learning?", text=SAMPLE_TEXT)
        assert isinstance(answer, str)
        assert len(answer) > 20

    def test_ask_stream(self):
        chunks = list(self.agent.ask_stream("What is deep learning?", text=SAMPLE_TEXT))
        assert len(chunks) > 0
        full = "".join(chunks)
        assert len(full) > 20

    def test_conversation_history(self):
        self.agent.set_context(SAMPLE_TEXT)
        self.agent.ask("What is overfitting?")
        assert len(self.agent.history) == 2

    def test_history_trimmed_to_max(self):
        self.agent.set_context(SAMPLE_TEXT)
        for i in range(5):
            self.agent.ask(f"Question {i} about machine learning?")
        assert len(self.agent.history) <= 6  # MAX_HISTORY = 6

    def test_set_context_resets_history(self):
        self.agent.set_context(SAMPLE_TEXT)
        self.agent.ask("What is clustering?")
        self.agent.set_context("New document about Python.")
        assert self.agent.history == []

    def test_langchain_faiss_store_built(self):
        self.agent.set_context(SAMPLE_TEXT)
        self.agent._ensure_store()
        assert self.agent._store is not None


class TestComparisonAgent:
    def setup_method(self):
        from agents.comparison_agent import ComparisonAgent
        self.agent = ComparisonAgent()

    def test_compare_returns_string(self):
        text2 = "Python is a programming language used for data science and web development."
        result = self.agent.compare(SAMPLE_TEXT, text2, "ML Notes", "Python Notes")
        assert isinstance(result, str)
        assert len(result) > 100

    def test_compare_contains_sections(self):
        text2 = "Deep Learning is a subset of machine learning using neural networks."
        result = self.agent.compare(SAMPLE_TEXT, text2)
        assert "**" in result  # bold section headers


# ═══════════════════════════════════════════════════════════════════════════════
# 4. LANGGRAPH ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════════════════

class TestStudyOrchestrator:
    def test_phase1_returns_required_keys(self):
        from agents.study_orchestrator import run_phase1
        state = run_phase1(SAMPLE_TEXT, goal="Learn ML in 7 days")
        assert "topic" in state
        assert "summary" in state
        assert "diagnostic_quiz" in state
        assert len(state["summary"]) > 0
        assert "quiz" in state["diagnostic_quiz"]

    def test_phase1_steps_log(self):
        from agents.study_orchestrator import run_phase1
        state = run_phase1(SAMPLE_TEXT)
        # steps_log accumulates across all nodes via the Annotated reducer
        step_names = [s["step"] for s in state["steps_log"]]
        assert len(step_names) >= 3
        assert "diagnostic_quiz" in step_names

    def test_phase2a_high_score_no_remediation(self):
        from agents.study_orchestrator import run_phase1, run_phase2a
        state = run_phase1(SAMPLE_TEXT)
        questions = state["diagnostic_quiz"].get("quiz", [])
        # Answer all correctly
        correct_answers = {str(i): q["answer"] for i, q in enumerate(questions)}
        state2a = run_phase2a(state, correct_answers)
        assert state2a["score_pct"] >= 60
        assert state2a.get("targeted_quiz") == {} or state2a.get("targeted_quiz") is None or \
               state2a.get("flashcards") == {} or state2a.get("flashcards") is None

    def test_phase2a_low_score_triggers_remediation(self):
        from agents.study_orchestrator import run_phase1, run_phase2a
        state = run_phase1(SAMPLE_TEXT)
        # Answer all wrong
        wrong_answers = {str(i): "wrong answer xyz" for i in range(5)}
        state2a = run_phase2a(state, wrong_answers)
        assert state2a["score_pct"] < 60
        assert "flashcards" in state2a
        assert "targeted_quiz" in state2a

    def test_phase2b_compiles_report(self):
        from agents.study_orchestrator import run_phase1, run_phase2a, run_phase2b
        state = run_phase1(SAMPLE_TEXT)
        questions = state["diagnostic_quiz"].get("quiz", [])
        wrong_answers = {str(i): "wrong" for i in range(len(questions))}
        state2a = run_phase2a(state, wrong_answers)
        report = run_phase2b(state2a, targeted_quiz_answers={})
        assert "topic" in report
        assert "summary" in report
        assert "roadmap" in report
        assert "score_pct" in report
        assert "needs_remediation" in report

    def test_phase2b_report_needs_remediation_flag(self):
        from agents.study_orchestrator import run_phase1, run_phase2a, run_phase2b
        state = run_phase1(SAMPLE_TEXT)
        wrong_answers = {str(i): "wrong" for i in range(5)}
        state2a = run_phase2a(state, wrong_answers)
        report = run_phase2b(state2a)
        assert report["needs_remediation"] is True

    def test_graph_singletons_reused(self):
        from agents.study_orchestrator import get_phase1_graph, get_phase2a_graph, get_phase2b_graph
        g1a = get_phase1_graph()
        g1b = get_phase1_graph()
        assert g1a is g1b
        g2a = get_phase2a_graph()
        g2b = get_phase2a_graph()
        assert g2a is g2b


# ═══════════════════════════════════════════════════════════════════════════════
# 5. FLASK API ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def client():
    from app import app
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret"
    with app.test_client() as c:
        with app.app_context():
            yield c


class TestFlaskRoutes:
    def test_index(self, client):
        resp = client.get("/")
        assert resp.status_code == 200

    def test_summarize_no_input(self, client):
        resp = client.post("/summarize", json={})
        assert resp.status_code == 400

    def test_summarize_with_text(self, client):
        resp = client.post("/summarize", data={"text": SAMPLE_TEXT})
        assert resp.status_code == 200
        data = resp.get_json()
        assert "summary" in data
        assert len(data["summary"]) > 50

    def test_summarize_cached_on_second_call(self, client):
        client.post("/summarize", data={"text": SAMPLE_TEXT})
        resp = client.post("/summarize", data={"text": SAMPLE_TEXT})
        data = resp.get_json()
        assert data.get("cached") is True

    def test_quiz_with_text(self, client):
        resp = client.post("/quiz", data={"text": SAMPLE_TEXT, "difficulty": "medium"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert "quiz" in data
        assert len(data["quiz"]) == 5

    def test_quiz_no_input(self, client):
        resp = client.post("/quiz", json={})
        assert resp.status_code == 400

    def test_roadmap_with_text(self, client):
        resp = client.post("/roadmap", data={"text": SAMPLE_TEXT, "days": 5})
        assert resp.status_code == 200
        data = resp.get_json()
        assert "roadmap" in data
        lines = [l for l in data["roadmap"].split("\n") if l.strip()]
        assert len(lines) == 5

    def test_flashcards_with_text(self, client):
        resp = client.post("/flashcards", data={"text": SAMPLE_TEXT})
        assert resp.status_code == 200
        data = resp.get_json()
        assert "flashcards" in data
        assert len(data["flashcards"]) == 8

    def test_chat_with_text(self, client):
        resp = client.post("/chat", json={"question": "What is supervised learning?", "text": SAMPLE_TEXT})
        assert resp.status_code == 200
        data = resp.get_json()
        assert "answer" in data
        assert len(data["answer"]) > 10

    def test_chat_no_question(self, client):
        resp = client.post("/chat", json={"text": SAMPLE_TEXT})
        assert resp.status_code == 400

    def test_detect_topic(self, client):
        resp = client.post("/detect-topic", data={"text": SAMPLE_TEXT})
        assert resp.status_code == 200
        data = resp.get_json()
        assert "topic" in data
        assert "emoji" in data

    def test_progress_record_and_get(self, client):
        resp = client.post("/progress/record", json={"topic": "ML", "score": 4, "total": 5, "difficulty": "medium"})
        assert resp.status_code == 200
        resp2 = client.get("/progress")
        assert resp2.status_code == 200
        history = resp2.get_json()
        assert isinstance(history, list)

    def test_progress_clear(self, client):
        client.post("/progress/record", json={"topic": "Test", "score": 3, "total": 5, "difficulty": "easy"})
        resp = client.post("/progress/clear")
        assert resp.status_code == 200

    def test_cache_stats(self, client):
        resp = client.get("/cache/stats")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "doc_cache_entries" in data
        assert "vector_indexes" in data

    def test_cache_clear(self, client):
        resp = client.post("/cache/clear")
        assert resp.status_code == 200

    def test_quiz_explain(self, client):
        quiz_resp = client.post("/quiz", data={"text": SAMPLE_TEXT, "difficulty": "medium"})
        quiz_data = quiz_resp.get_json()
        questions = [{"index": i, **q} for i, q in enumerate(quiz_data["quiz"])]
        user_answers = {str(i): "wrong answer" for i in range(len(questions))}
        resp = client.post("/quiz/explain", json={"questions": questions, "user_answers": user_answers})
        assert resp.status_code == 200
        data = resp.get_json()
        assert "explanations" in data

    def test_summarize_stream(self, client):
        resp = client.post("/summarize/stream", data={"text": SAMPLE_TEXT})
        assert resp.status_code == 200
        assert "text/event-stream" in resp.content_type

    def test_chat_stream(self, client):
        resp = client.post("/chat/stream", json={"question": "What is deep learning?", "text": SAMPLE_TEXT})
        assert resp.status_code == 200
        assert "text/event-stream" in resp.content_type

    def test_export_summary_no_data(self, client):
        # Fresh session — no summary yet
        resp = client.get("/export/summary")
        # Either 400 (no summary) or 200 (if session has leftover data) — both valid
        assert resp.status_code in (200, 400)

    def test_export_summary_after_generate(self, client):
        client.post("/summarize", data={"text": SAMPLE_TEXT})
        resp = client.get("/export/summary")
        assert resp.status_code == 200
        assert resp.content_type == "application/pdf"

    def test_export_quiz_after_generate(self, client):
        client.post("/quiz", data={"text": SAMPLE_TEXT, "difficulty": "easy"})
        resp = client.get("/export/quiz")
        assert resp.status_code == 200
        assert resp.content_type == "application/pdf"

    def test_export_roadmap_after_generate(self, client):
        client.post("/roadmap", data={"text": SAMPLE_TEXT, "days": 3})
        resp = client.get("/export/roadmap")
        assert resp.status_code == 200
        assert resp.content_type == "application/pdf"

    def test_export_flashcards_after_generate(self, client):
        client.post("/flashcards", data={"text": SAMPLE_TEXT})
        resp = client.get("/export/flashcards")
        assert resp.status_code == 200
        assert resp.content_type == "application/pdf"

    def test_weak_areas(self, client):
        resp = client.get("/progress/weak-areas")
        assert resp.status_code == 200

    def test_record_wrong_answer(self, client):
        resp = client.post("/progress/record-wrong", json={
            "question": "What is overfitting?",
            "correct_answer": "When a model memorizes training data",
            "topic": "ML"
        })
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# 6. STUDY SESSION (LangGraph Phase Endpoints)
# ═══════════════════════════════════════════════════════════════════════════════

class TestStudySessionEndpoints:
    def test_phase1_endpoint(self, client):
        resp = client.post("/study-session/phase1", data={"text": SAMPLE_TEXT, "goal": "Learn ML in 7 days"})
        assert resp.status_code == 200
        assert "text/event-stream" in resp.content_type

    def test_phase2a_without_phase1(self, client):
        # New client session — no phase1 state
        from app import app
        with app.test_client() as fresh_client:
            resp = fresh_client.post("/study-session/phase2a", json={"user_answers": {"0": "a"}})
            assert resp.status_code == 400

    def test_phase2b_without_phase2a(self, client):
        from app import app
        with app.test_client() as fresh_client:
            resp = fresh_client.post("/study-session/phase2b", json={})
            assert resp.status_code == 400
