"""
Study Orchestrator — LangGraph Three-Phase Human-in-the-Loop
=============================================================

PHASE 1   detect_topic → summarize → diagnostic_quiz
          PAUSE → user answers diagnostic quiz

PHASE 2.a  evaluate_quiz → [score < 60?]
              YES → generate_flashcards → targeted_quiz
              NO  → (skip)
          PAUSE → if remediation: user answers targeted quiz

PHASE 2.b  build_roadmap → compile_report
          Uses targeted_quiz_answers if available
"""

import re
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END

from agents.topic_detector import TopicDetector
from agents.summarizer_agent import SummarizerAgent
from agents.quiz_agent import QuizAgent
from agents.flashcard_agent import FlashcardAgent
from agents.roadmap_agent import RoadmapAgent


# ── Agent singletons — created once, reused across all node calls 

_topic_detector  = TopicDetector()
_summarizer      = SummarizerAgent()
_quiz_agent      = QuizAgent()
_flashcard_agent = FlashcardAgent()
_roadmap_agent   = RoadmapAgent()


# ── State 

class StudyState(TypedDict):
    text: str
    goal: str
    days: int
    topic: str
    subtopic: str
    emoji: str
    summary: str
    diagnostic_quiz: dict
    user_answers: dict
    score_pct: int
    weak_topics: list[str]
    flashcards: dict
    targeted_quiz: dict
    targeted_quiz_answers: dict
    targeted_score_pct: int
    roadmap: str
    report: dict
    steps_log: Annotated[list, lambda a, b: a + b]


# ── Nodes — use singletons, never instantiate agents inline 

def node_detect_topic(state: StudyState) -> dict:
    result = _topic_detector.detect(state["text"])
    return {
        "topic":     result.get("topic", "General"),
        "subtopic":  result.get("subtopic", ""),
        "emoji":     result.get("emoji", "📚"),
        "steps_log": [{"step": "detect_topic", "result": result}],
    }


def node_summarize(state: StudyState) -> dict:
    summary = _summarizer.summarize(state["text"])
    return {
        "summary":   summary,
        "steps_log": [{"step": "summarize", "chars": len(summary)}],
    }


def node_diagnostic_quiz(state: StudyState) -> dict:
    quiz = _quiz_agent.generate_quiz(state["text"], difficulty="medium")
    return {
        "diagnostic_quiz": quiz,
        "steps_log": [{"step": "diagnostic_quiz", "questions": len(quiz.get("quiz", []))}],
    }


def node_evaluate_quiz(state: StudyState) -> dict:
    questions    = state.get("diagnostic_quiz", {}).get("quiz", [])
    user_answers = state.get("user_answers", {})
    correct = sum(
        1 for i, q in enumerate(questions)
        if user_answers.get(str(i), "").strip().lower() == q["answer"].strip().lower()
    )
    score_pct = round(correct / len(questions) * 100) if questions else 0
    wrong_qs  = [
        q["question"] for i, q in enumerate(questions)
        if user_answers.get(str(i), "").strip().lower() != q["answer"].strip().lower()
    ]
    return {
        "score_pct":   score_pct,
        "weak_topics": wrong_qs,
        "steps_log":   [{"step": "evaluate_quiz", "score_pct": score_pct, "weak_count": len(wrong_qs)}],
    }


def node_generate_flashcards(state: StudyState) -> dict:
    weak_context = "Focus on these weak areas:\n" + "\n".join(state["weak_topics"])
    flashcards = _flashcard_agent.generate_flashcards(weak_context + "\n\n" + state["text"])
    return {
        "flashcards": flashcards,
        "steps_log":  [{"step": "generate_flashcards", "count": len(flashcards.get("flashcards", []))}],
    }


def node_targeted_quiz(state: StudyState) -> dict:
    weak_context = "Focus ONLY on these topics:\n" + "\n".join(state["weak_topics"])
    quiz = _quiz_agent.generate_quiz(weak_context + "\n\n" + state["text"], difficulty="hard")
    return {
        "targeted_quiz": quiz,
        "steps_log":     [{"step": "targeted_quiz", "questions": len(quiz.get("quiz", []))}],
    }


def node_evaluate_targeted_quiz(state: StudyState) -> dict:
    questions = state.get("targeted_quiz", {}).get("quiz", [])
    answers   = state.get("targeted_quiz_answers", {})
    if not questions or not answers:
        return {"targeted_score_pct": 0, "steps_log": [{"step": "evaluate_targeted_quiz", "skipped": True}]}
    correct = sum(
        1 for i, q in enumerate(questions)
        if answers.get(str(i), "").strip().lower() == q["answer"].strip().lower()
    )
    score = round(correct / len(questions) * 100)
    return {
        "targeted_score_pct": score,
        "steps_log": [{"step": "evaluate_targeted_quiz", "targeted_score_pct": score}],
    }


def node_build_roadmap(state: StudyState) -> dict:
    days = state.get("days", 7)
    goal = state.get("goal", "")
    if goal:
        match = re.search(r'(\d+)\s*day', goal, re.IGNORECASE)
        if match:
            days = int(match.group(1))
    weak_prefix = ""
    if state.get("weak_topics"):
        weak_prefix = "Prioritise these weak areas in the early days:\n" + \
                      "\n".join(state["weak_topics"]) + "\n\n"
    roadmap = _roadmap_agent.create_roadmap(weak_prefix + state["text"], days)
    return {
        "roadmap":   roadmap,
        "steps_log": [{"step": "build_roadmap", "days": days}],
    }


def node_compile_report(state: StudyState) -> dict:
    score          = state.get("score_pct", 0)
    targeted_score = state.get("targeted_score_pct", 0)
    report = {
        "topic":                 state.get("topic", "General"),
        "subtopic":              state.get("subtopic", ""),
        "emoji":                 state.get("emoji", "📚"),
        "goal":                  state.get("goal", ""),
        "summary":               state.get("summary", ""),
        "diagnostic_quiz":       state.get("diagnostic_quiz", {}),
        "user_answers":          state.get("user_answers", {}),
        "score_pct":             score,
        "weak_topics":           state.get("weak_topics", []),
        "flashcards":            state.get("flashcards", {}),
        "targeted_quiz":         state.get("targeted_quiz", {}),
        "targeted_quiz_answers": state.get("targeted_quiz_answers", {}),
        "targeted_score_pct":    targeted_score,
        "roadmap":               state.get("roadmap", ""),
        "steps_log":             state.get("steps_log", []),
        "needs_remediation":     score < 60,
    }
    return {"report": report, "steps_log": [{"step": "compile_report", "done": True}]}


# ── Conditional edges

def should_remediate(state: StudyState) -> str:
    return "remediate" if state.get("score_pct", 100) < 60 else "skip_remediation"


# ── Graph builders

def build_phase1_graph():
    g = StateGraph(StudyState)
    g.add_node("detect_topic",    node_detect_topic)
    g.add_node("summarize",       node_summarize)
    g.add_node("diagnostic_quiz", node_diagnostic_quiz)
    g.set_entry_point("detect_topic")
    g.add_edge("detect_topic",    "summarize")
    g.add_edge("summarize",       "diagnostic_quiz")
    g.add_edge("diagnostic_quiz", END)
    return g.compile()


def build_phase2a_graph():
    g = StateGraph(StudyState)
    g.add_node("evaluate_quiz",       node_evaluate_quiz)
    g.add_node("generate_flashcards", node_generate_flashcards)
    g.add_node("targeted_quiz",       node_targeted_quiz)
    g.set_entry_point("evaluate_quiz")
    g.add_conditional_edges(
        "evaluate_quiz",
        should_remediate,
        {"remediate": "generate_flashcards", "skip_remediation": END},
    )
    g.add_edge("generate_flashcards", "targeted_quiz")
    g.add_edge("targeted_quiz",       END)
    return g.compile()


def build_phase2b_graph():
    g = StateGraph(StudyState)
    g.add_node("evaluate_targeted_quiz", node_evaluate_targeted_quiz)
    g.add_node("build_roadmap",          node_build_roadmap)
    g.add_node("compile_report",         node_compile_report)
    g.set_entry_point("evaluate_targeted_quiz")
    g.add_edge("evaluate_targeted_quiz", "build_roadmap")
    g.add_edge("build_roadmap",          "compile_report")
    g.add_edge("compile_report",         END)
    return g.compile()


# ── Singletons ────────────────────────────────────────────────────────────────

_p1 = _p2a = _p2b = None

def get_phase1_graph():
    global _p1
    if _p1 is None: _p1 = build_phase1_graph()
    return _p1

def get_phase2a_graph():
    global _p2a
    if _p2a is None: _p2a = build_phase2a_graph()
    return _p2a

def get_phase2b_graph():
    global _p2b
    if _p2b is None: _p2b = build_phase2b_graph()
    return _p2b


# ── Helpers ───────────────────────────────────────────────────────────────────

def _empty_state(text, goal, days=7) -> StudyState:
    return {
        "text": text, "goal": goal, "days": days,
        "topic": "", "subtopic": "", "emoji": "",
        "summary": "", "diagnostic_quiz": {}, "user_answers": {},
        "score_pct": 0, "weak_topics": [], "flashcards": {},
        "targeted_quiz": {}, "targeted_quiz_answers": {},
        "targeted_score_pct": 0, "roadmap": "", "report": {}, "steps_log": [],
    }


def _stream_graph(graph, state, progress_cb):
    """
    Stream the graph and return the fully accumulated final state.

    LangGraph streams per-node partial dicts. The steps_log field uses an
    Annotated reducer (list concat), so we must accumulate it manually here
    rather than blindly overwriting with each chunk — otherwise only the last
    node's steps_log entry survives.
    """
    final = dict(state)
    accumulated_steps: list = list(state.get("steps_log", []))

    for chunk in graph.stream(state):
        for node_name, node_state in chunk.items():
            # Accumulate steps_log separately before merging the rest
            new_steps = node_state.pop("steps_log", [])
            accumulated_steps.extend(new_steps)
            final.update(node_state)
            if progress_cb:
                progress_cb(node_name, {**node_state, "steps_log": new_steps})

    final["steps_log"] = accumulated_steps
    return final


# ── Public API ────────────────────────────────────────────────────────────────

def run_phase1(text: str, goal: str = "", days: int = 7, progress_cb=None) -> dict:
    state = _empty_state(text, goal, days)
    return _stream_graph(get_phase1_graph(), state, progress_cb)


def run_phase2a(saved_state: dict, user_answers: dict, progress_cb=None) -> dict:
    state = {**saved_state, "user_answers": user_answers}
    return _stream_graph(get_phase2a_graph(), state, progress_cb)


def run_phase2b(saved_state: dict, targeted_quiz_answers: dict = None, progress_cb=None) -> dict:
    state = {**saved_state, "targeted_quiz_answers": targeted_quiz_answers or {}}
    final = _stream_graph(get_phase2b_graph(), state, progress_cb)
    return final.get("report", {})
