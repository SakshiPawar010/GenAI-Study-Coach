import os
import hashlib
import time
import logging
import pickle
import numpy as np
from functools import lru_cache

from google import genai
from google.genai import types
import faiss
from langchain_core.prompts import PromptTemplate
from .config import GEMINI_API_KEY, MODEL_ID

logger = logging.getLogger(__name__)

FAISS_STORE_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "vector_store")
os.makedirs(FAISS_STORE_DIR, exist_ok=True)

_MAX_RETRIES   = 3
_RETRY_BACKOFF = 2.0

_client = genai.Client(api_key=GEMINI_API_KEY)


# ── LLM invoke ────────────────────────────────────────────────────────────────

def _invoke_llm(prompt: str, max_tokens: int = 500, temperature: float = 0.3) -> str:
    delay = _RETRY_BACKOFF
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            response = _client.models.generate_content(
                model=MODEL_ID,
                contents=prompt,
                config=types.GenerateContentConfig(
                    max_output_tokens=max_tokens,
                    temperature=temperature,
                )
            )
            return response.text
        except Exception as e:
            err = str(e)
            is_quota = "429" in err or "quota" in err.lower() or "rate" in err.lower()
            if is_quota and attempt < _MAX_RETRIES:
                logger.warning("Gemini attempt %d/%d throttled. Retrying in %.1fs…", attempt, _MAX_RETRIES, delay)
                time.sleep(delay)
                delay *= 2
                continue
            raise


def _stream_llm(prompt: str, max_tokens: int = 2000, temperature: float = 0.3):
    delay = _RETRY_BACKOFF
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            for chunk in _client.models.generate_content_stream(
                model=MODEL_ID,
                contents=prompt,
                config=types.GenerateContentConfig(
                    max_output_tokens=max_tokens,
                    temperature=temperature,
                )
            ):
                if chunk.text:
                    yield chunk.text
            return
        except Exception as e:
            err = str(e)
            is_quota = "429" in err or "quota" in err.lower()
            if is_quota and attempt < _MAX_RETRIES:
                logger.warning("Gemini stream attempt %d/%d throttled. Retrying in %.1fs…", attempt, _MAX_RETRIES, delay)
                time.sleep(delay)
                delay *= 2
                continue
            raise


# ── Embeddings ────────────────────────────────────────────────────────────────

def _embed(text: str) -> np.ndarray:
    response = _client.models.embed_content(
        model="models/text-embedding-004",
        contents=text,
    )
    return np.array(response.embeddings[0].values, dtype=np.float32)


# ── Chain-compatible wrappers ─────────────────────────────────────────────────

class _Chain:
    """Mimics LangChain chain interface using Gemini directly."""
    def __init__(self, prompt_template: str, max_tokens: int, temperature: float):
        self.prompt = PromptTemplate.from_template(prompt_template)
        self.max_tokens  = max_tokens
        self.temperature = temperature

    def invoke(self, inputs: dict) -> str:
        prompt_text = self.prompt.format(**inputs)
        return _invoke_llm(prompt_text, self.max_tokens, self.temperature)

    def stream(self, inputs: dict):
        prompt_text = self.prompt.format(**inputs)
        yield from _stream_llm(prompt_text, self.max_tokens, self.temperature)


def build_chain(prompt_template: str, max_tokens: int = 500, temperature: float = 0.3) -> _Chain:
    return _Chain(prompt_template, max_tokens, temperature)


def invoke_chain(chain: _Chain, inputs: dict) -> str:
    return chain.invoke(inputs)


def stream_chain(chain: _Chain, inputs: dict):
    yield from chain.stream(inputs)


# ── FAISS store ───────────────────────────────────────────────────────────────

class _SimpleStore:
    def __init__(self, chunks, index, embeddings_cache):
        self.chunks = chunks
        self.index  = index
        self._cache = embeddings_cache

    def similarity_search(self, query: str, k: int = 3):
        q_vec = _embed(query).reshape(1, -1)
        _, indices = self.index.search(q_vec, min(k, len(self.chunks)))

        class _Doc:
            def __init__(self, content):
                self.page_content = content

        return [_Doc(self.chunks[i]) for i in indices[0] if i < len(self.chunks)]


def build_faiss_store(chunks: list) -> _SimpleStore:
    doc_hash  = hashlib.md5("||".join(chunks).encode()).hexdigest()
    idx_path  = os.path.join(FAISS_STORE_DIR, f"{doc_hash}_gemini.faiss")
    meta_path = os.path.join(FAISS_STORE_DIR, f"{doc_hash}_gemini.pkl")

    if os.path.exists(idx_path) and os.path.exists(meta_path):
        try:
            index = faiss.read_index(idx_path)
            with open(meta_path, "rb") as f:
                meta = pickle.load(f)
            return _SimpleStore(meta["chunks"], index, {})
        except Exception as e:
            logger.warning("Failed to load FAISS from disk: %s — rebuilding.", e)

    embeddings = np.array([_embed(c) for c in chunks])
    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)

    try:
        faiss.write_index(index, idx_path)
        with open(meta_path, "wb") as f:
            pickle.dump({"chunks": chunks}, f)
    except Exception as e:
        logger.warning("Could not persist FAISS store: %s", e)

    return _SimpleStore(chunks, index, {})
