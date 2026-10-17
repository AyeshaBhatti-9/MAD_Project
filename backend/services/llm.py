import re
import json
from groq import Groq

from ..config import GROQ_API_KEY, GROQ_MODEL

groq_client = Groq(api_key=GROQ_API_KEY)

SYSTEM_PROMPT = """PASTE YOUR EXISTING SYSTEM_PROMPT TEXT HERE (everything between the triple quotes in your old main.py)"""


# ── XAI response parser ──────────────────────────────────────────────────────
_XAI_BLOCK_RE = re.compile(r'<xai>\s*(.*?)\s*</xai>', re.DOTALL)


def parse_xai_block(raw_response: str) -> tuple[str, dict]:
    """Split the LLM response into (answer_text, xai_data)."""
    match = _XAI_BLOCK_RE.search(raw_response)
    if not match:
        return raw_response.strip(), {}

    answer = raw_response[:match.start()].strip()
    try:
        xai_data = json.loads(match.group(1))
    except json.JSONDecodeError:
        xai_data = {}
    return answer, xai_data


def why_relevant_map(xai_data: dict) -> dict[int, str]:
    """Return {citation_index: why_relevant_text}."""
    result = {}
    for entry in xai_data.get("citations", []):
        idx = entry.get("index")
        why = entry.get("why_relevant", "")
        if idx and why:
            result[int(idx)] = why
    return result


# ── Groq call ────────────────────────────────────────────────────────────────
def ask_groq(question: str, context: str, is_conversational: bool,
             history: list[dict] | None = None) -> str:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages += history or []   # [{"role": "user"|"assistant", "content": "..."}]

    if is_conversational:
        user_msg = question
    else:
        user_msg = (
            f"Pakistani labour law context:\n\n{context}\n\n"
            f"Worker's question: {question}\n\n"
            "Answer using inline citation markers [1], [2], etc. from the numbered provisions above. "
            "Then append the <xai> JSON block as instructed."
        )
    messages.append({"role": "user", "content": user_msg})

    resp = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        temperature=0.2 if is_conversational else 0.1,
        max_tokens=256 if is_conversational else 900,
    )
    return resp.choices[0].message.content.strip()