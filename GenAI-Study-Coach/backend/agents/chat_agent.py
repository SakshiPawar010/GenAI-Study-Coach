from service.document_processor import DocumentProcessor
from service.langchain_client import build_chain, invoke_chain, stream_chain, build_faiss_store

MAX_HISTORY = 6

_PROMPT = """\
You are an expert study assistant. Answer the question based ONLY on the provided study notes.
If the answer is not in the notes, say "This topic is not covered in the provided notes."

Study Notes:
{context}
{history}
Current Question: {question}

Provide a clear, detailed answer based on the notes above. Include relevant examples if mentioned in the notes.\
"""


class ChatAgent:
    def __init__(self):
        self.doc_processor = DocumentProcessor()
        self.chain = build_chain(_PROMPT, max_tokens=600, temperature=0.3)
        self.context = ""
        self._store = None
        self.history = []

    def set_context(self, text):
        self.context = text
        self._store = None
        self.history = []

    def _ensure_store(self):
        if self._store is None and self.context:
            chunks = self.doc_processor.chunk_text(self.context, max_chars=3000, overlap=200)
            self._store = build_faiss_store(chunks)

    def _retrieve(self, question):
        if self._store:
            docs = self._store.similarity_search(question, k=3)
            return "\n\n".join(d.page_content for d in docs)
        return self.context[:4000]

    def _history_text(self):
        if not self.history:
            return ""
        lines = [f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content']}" for m in self.history]
        return "\nPrevious conversation:\n" + "\n".join(lines) + "\n"

    def _save(self, question, answer):
        self.history.extend([{"role": "user", "content": question}, {"role": "assistant", "content": answer}])
        if len(self.history) > MAX_HISTORY:
            self.history = self.history[-MAX_HISTORY:]

    def ask(self, question, text=None):
        if text:
            self.set_context(text)
        self._ensure_store()
        answer = invoke_chain(self.chain, {
            "context": self._retrieve(question),
            "history": self._history_text(),
            "question": question,
        })
        self._save(question, answer)
        return answer

    def ask_stream(self, question, text=None):
        if text:
            self.set_context(text)
        self._ensure_store()
        inputs = {
            "context": self._retrieve(question),
            "history": self._history_text(),
            "question": question,
        }
        full_answer = []
        for chunk in stream_chain(self.chain, inputs):
            full_answer.append(chunk)
            yield chunk
        self._save(question, "".join(full_answer))
