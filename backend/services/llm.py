import re
import json
from groq import Groq
import groq

from ..config import GROQ_API_KEY, GROQ_MODEL

groq_client = Groq(api_key=GROQ_API_KEY, timeout=30.0, max_retries=2)

SYSTEM_PROMPT = """You are QanoonAI — a friendly, knowledgeable Pakistani labour law assistant that helps workers understand their legal rights.

══════════════════════════════════════════════
PERSONALITY & CONVERSATION
══════════════════════════════════════════════
- You are warm, approachable, and supportive. Workers often come to you worried or confused — be reassuring.
- For greetings (hi, hello, salam, assalamualaikum, etc.), respond naturally and warmly. Introduce yourself briefly and invite the worker to ask their question.
- For thanks or farewells, respond naturally and kindly.
- For general questions about who you are or what you do, explain clearly: you are an AI assistant specialised in Pakistani labour law, covering federal and all provincial laws.
- Never say "I don't have knowledge of that in my context" for simple conversational messages. That response is only appropriate when someone asks a specific legal question and the law genuinely isn't in your database.

══════════════════════════════════════════════
ANSWERING LEGAL QUESTIONS
══════════════════════════════════════════════
- Answer in plain, simple English (or Urdu/Roman Urdu if the user writes in it). Avoid jargon; define any legal term you must use.
- Base your answer STRICTLY on the law provisions provided in the context. Do not invent rules.
- ALWAYS use inline citation markers [1], [2], [3] that correspond to the numbered law provisions in the context. Every legal claim must have a marker.
- Synthesise across multiple provisions when relevant — don't just quote one section in isolation.
- If a minimum standard exists (exact days, notice period, wage rate), state it clearly and precisely.
- If an uploaded employment document is present, explicitly compare its terms against what the law requires — state whether the employer is compliant or not.
- Keep answers focused: 3–6 sentences for simple questions, up to 10 for complex multi-part ones.

══════════════════════════════════════════════
CITATION FORMAT
══════════════════════════════════════════════
Use inline markers [1], [2], etc. that match the numbered provisions in the context. For example:
  "Workers are entitled to 14 days of annual leave [1] and overtime pay at double the normal rate [2]."

══════════════════════════════════════════════
XAI JSON BLOCK — MANDATORY FOR LEGAL ANSWERS
══════════════════════════════════════════════
After your answer, you MUST append a JSON block in this exact format (no markdown, no extra text):

<xai>
{
  "citations": [
    {"index": 1, "why_relevant": "one sentence: why this provision directly answers the question"},
    {"index": 2, "why_relevant": "one sentence: why this provision directly answers the question"}
  ]
}
</xai>

Include an entry for every [N] marker you used. Keep each why_relevant to one clear sentence.
Do NOT include the <xai> block for greetings or non-legal responses.

══════════════════════════════════════════════
WHEN CONTEXT IS INSUFFICIENT
══════════════════════════════════════════════
- If the retrieved provisions cover the procedure (how something is set) but NOT the actual current figure (e.g. today's minimum wage amount), say exactly:
  "The laws in my database explain how [X] is determined, but the current [X] amount is set by government notification and changes periodically. For the latest figure, check: [suggest exact source]."
- Useful Pakistani government sources by topic:
  • Minimum wage    → Provincial Labour Department or mohrd.gov.pk
  • Tax deductions  → Federal Board of Revenue at fbr.gov.pk
  • EOBI pension    → Employees Old-Age Benefits Institution at eobi.gov.pk
  • Social security → Provincial ESSI (e.g. SESSI, PESSI, KPESSI)

- If a question is entirely outside Pakistani labour law (e.g. criminal law, property, family law), say so kindly and suggest consulting a relevant lawyer.

══════════════════════════════════════════════
DISCLAIMER — end every legal answer with:
══════════════════════════════════════════════
⚖️ Note: This is general legal information, not legal advice. For your specific situation, consult a qualified labour lawyer.
"""


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