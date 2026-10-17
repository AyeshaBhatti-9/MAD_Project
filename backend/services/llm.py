import re
import json
from groq import Groq
import groq

from ..config import GROQ_API_KEY, GROQ_MODEL

groq_client = Groq(api_key=GROQ_API_KEY, timeout=30.0, max_retries=2)

SYSTEM_PROMPT = """PASTE YOUR EXISTING SYSTEM_PROMPT TEXT HERE (everything between the triple quotes in your old main.py)"""


# ── XAI response parser ──────────────────────────────────────────────────────
_XAI_BLOCK_RE = re.compile(r'<xai>\s*(.*?)\s*</xai>', re.DOTALL)

class LLMUnavailable(Exception):
    """Raised when the LLM call fails or returns nothing."""

def parse_xai_block(raw_response: str) -> tuple[str, dict]:
    """Split the LLM response into (answer_text, xai_data). Never raises."""
    match = _XAI_BLOCK_RE.search(raw_response)
    if not match:
        return raw_response.strip(), {}

    answer = raw_response[:match.start()].strip()
    body = match.group(1).strip()
    body = re.sub(r"^```(?:json)?|```$", "", body, flags=re.MULTILINE).strip()  # strip code fences
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return answer, {}
    return answer, data if isinstance(data, dict) else {}


def why_relevant_map(xai_data: dict) -> dict[int, str]:
    """Return {citation_index: why_relevant_text}. Accepts several shapes."""
    result = {}
    cites = xai_data.get("citations", []) if isinstance(xai_data, dict) else []

    # Shape A: {"1": "reason", "2": "reason"}
    if isinstance(cites, dict):
        for k, v in cites.items():
            if str(k).isdigit() and isinstance(v, str):
                result[int(k)] = v
        return result

    if not isinstance(cites, list):
        return result

    for pos, entry in enumerate(cites, 1):
        # Shape B (expected): {"index": 1, "why_relevant": "..."}
        if isinstance(entry, dict):
            idx = entry.get("index", pos)
            why = entry.get("why_relevant", "")
            if why and str(idx).isdigit():
                result[int(idx)] = str(why)
        # Shape C: plain strings, e.g. "[1] reason" or just "reason"
        elif isinstance(entry, str) and entry.strip():
            m = re.match(r"^\s*\[?(\d+)\]?[\s:.\-]*(.*)$", entry)
            if m and m.group(2):
                result[int(m.group(1))] = m.group(2).strip()
            else:
                result[pos] = entry.strip()
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

    try:
        resp = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            temperature=0.2 if is_conversational else 0.1,
            max_tokens=1024 if is_conversational else 3000,
            reasoning_effort="low",
        )
    except groq.APIError as e:          # covers connection, timeout, rate limit, bad model
        raise LLMUnavailable(str(e)) from e

    content = (resp.choices[0].message.content or "").strip()
    if not content:                     # reasoning models can burn the whole token budget
        raise LLMUnavailable("Empty response from model")
    return content