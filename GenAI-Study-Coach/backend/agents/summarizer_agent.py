from service.document_processor import DocumentProcessor
from service.langchain_client import build_chain, invoke_chain, stream_chain

DOC_BREAK = '[DOCUMENT BREAK]'

# _CHUNK_PROMPT and _SINGLE_PROMPT shared the same structure — merged into one.
_SUMMARIZE_PROMPT = """\
You are an expert study assistant. Summarize every topic from the content below.
Write each topic name in bold followed by a 2-3 line explanation.

{label}Content:
{text}

Format:
**Topic Name**
2-3 line explanation — complete sentences only.

RULES:
- Bold every topic heading
- Cover ALL topics, do not skip any
- Do NOT use bullet points or numbered lists
- Do NOT leave any sentence incomplete\
"""

_REDUCE_PROMPT = """\
Combine these section summaries into one clean complete summary for {label}.

{combined}

Format:
**Topic Name**
2-3 line explanation - complete sentences only.

Cover EVERY topic without skipping any. Do not truncate.\
"""

_FINAL_PROMPT = """\
You are an expert study assistant. Create a clean, well-structured summary of the following notes.

Content:
{text}

Format the summary EXACTLY like this:

**[Main Topic/Concept Name]**
[2-3 line explanation of this topic as mentioned in the notes]

**[Next Topic/Concept Name]**
[2-3 line explanation]

(Continue for ALL topics in the document)

---
COMPARISON TABLE (only if document has comparisons):
| Feature | [Item A] | [Item B] |
|---------|----------|----------|
| [row]   | [value]  | [value]  |

RULES:
- Every main topic/concept from the document must appear in bold
- Under each bold heading write a clear 2-3 line explanation
- Do NOT use bullet points, numbered lists, or section headers
- Only add the comparison table if the document explicitly compares things
- Do NOT leave any sentence incomplete
- Cover ALL topics from the document\
"""

_MULTI_PROMPT = """\
You are an expert study assistant. You have summaries of {n} documents: {labels_str}.

Your task has 3 steps:
STEP 1 - Understand: Identify the MAIN PURPOSE of each document individually.
STEP 2 - Group: Cluster all topics by theme. Merge topics that appear in multiple documents.
STEP 3 - Write: Produce the final unified summary in the format below.

Document Summaries:
{docs_text}

Format EXACTLY like this:

**Overview**
[3-4 sentences describing each document and what they collectively teach]

**[Topic Name]**
[2-3 line explanation combining what all documents say about this topic]

(Repeat for every unique topic across all documents)

---
COMPARISON TABLE (include if documents compare or contrast things):
| Feature | [Item A] | [Item B] |
|---------|----------|----------|
| [row]   | [value]  | [value]  |

STRICT RULES:
- Overview MUST name each document and describe its individual purpose
- Merge duplicate topics into ONE entry
- Bold every topic heading
- Complete sentences only
- No bullet points, no numbered lists
- Cover every topic from all documents\
"""


class SummarizerAgent:
    def __init__(self):
        self.doc_processor  = DocumentProcessor()
        self._summarize_chain = build_chain(_SUMMARIZE_PROMPT, max_tokens=2000, temperature=0.3)
        self._reduce_chain    = build_chain(_REDUCE_PROMPT,    max_tokens=3000, temperature=0.3)
        self._final_chain     = build_chain(_FINAL_PROMPT,     max_tokens=4000, temperature=0.3)
        self._multi_chain     = build_chain(_MULTI_PROMPT,     max_tokens=4096, temperature=0.3)

    def _summarize_one(self, text: str, label: str = "") -> str:
        prefix = f"[{label}] " if label else ""
        if len(text) <= 6000:
            return invoke_chain(self._summarize_chain, {"label": prefix, "text": text})
        chunks = self.doc_processor.chunk_text(text, max_chars=6000)
        chunk_summaries = [invoke_chain(self._summarize_chain, {"label": prefix, "text": c}) for c in chunks]
        return invoke_chain(self._reduce_chain, {"label": prefix or "this document", "combined": "\n\n".join(chunk_summaries)})

    def summarize(self, text: str, filenames=None) -> str:
        docs = [d.strip() for d in text.split(DOC_BREAK) if d.strip()]
        if len(docs) == 1:
            content = self._summarize_one(docs[0]) if len(docs[0]) > 6000 else docs[0]
            return invoke_chain(self._final_chain, {"text": content})

        doc_summaries = []
        for i, doc in enumerate(docs):
            label = filenames[i].rsplit(".", 1)[0] if filenames and i < len(filenames) else f"Document {i+1}"
            doc_summaries.append((label, self._summarize_one(doc, label)))

        labels_str = " and ".join(f'"{l}"' for l, _ in doc_summaries)
        docs_text  = "\n\n".join(f"=== {l} ===\n{s}" for l, s in doc_summaries)
        return invoke_chain(self._multi_chain, {"n": len(doc_summaries), "labels_str": labels_str, "docs_text": docs_text})

    def summarize_stream(self, text: str, filenames=None):
        docs = [d.strip() for d in text.split(DOC_BREAK) if d.strip()]
        if len(docs) == 1:
            content = self._summarize_one(docs[0]) if len(docs[0]) > 6000 else docs[0]
            yield from stream_chain(self._final_chain, {"text": content})
            return

        doc_summaries = []
        for i, doc in enumerate(docs):
            label = filenames[i].rsplit(".", 1)[0] if filenames and i < len(filenames) else f"Document {i+1}"
            doc_summaries.append((label, self._summarize_one(doc, label)))

        labels_str = " and ".join(f'"{l}"' for l, _ in doc_summaries)
        docs_text  = "\n\n".join(f"=== {l} ===\n{s}" for l, s in doc_summaries)
        yield from stream_chain(self._multi_chain, {"n": len(doc_summaries), "labels_str": labels_str, "docs_text": docs_text})
