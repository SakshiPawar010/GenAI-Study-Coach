from service.langchain_client import build_chain, invoke_chain

_PROMPT = """\
You are an expert study assistant. Compare the two documents below in detail.

{label1}:
{text1}

{label2}:
{text2}

Provide a structured comparison using EXACTLY this format:

**Overview**
One paragraph summarizing what each document is about.

**Common Topics**
List topics, concepts, or ideas that appear in BOTH documents. Use bullet points.

**Unique to {label1}**
List topics or concepts found ONLY in {label1}. Use bullet points.

**Unique to {label2}**
List topics or concepts found ONLY in {label2}. Use bullet points.

**Key Differences**
List the most important differences in approach, depth, or content between the two documents. Use bullet points.

**Which to Study First**
One clear recommendation on which document to read first and why.

Be specific and reference actual content from the documents.\
"""


class ComparisonAgent:
    def __init__(self):
        self._chain = build_chain(_PROMPT, max_tokens=2000, temperature=0.3)

    def compare(self, text1, text2, label1="Document 1", label2="Document 2"):
        return invoke_chain(self._chain, {
            "label1": label1,
            "label2": label2,
            "text1":  text1[:5000],
            "text2":  text2[:5000],
        })
