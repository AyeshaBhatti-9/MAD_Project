# main.py  —  QanoonAI with Explainable AI layer
#
# XAI additions (zero extra API calls):
#   1. confidence score + label  — derived from rerank scores
#   2. inline [1][2] citation markers — via prompt instruction
#   3. why_relevant per citation — returned in same Groq call as JSON block
#   4. relevance_score per citation — rerank_score exposed to frontend

import os
import re
import json
import tempfile
import pdfplumber
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq
import chromadb
from sentence_transformers import SentenceTransformer, CrossEncoder
from dotenv import load_dotenv
load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
CHROMA_PATH       = "../data/chroma_db"
COLLECTION_NAME_1 = "qanoon_labour"
COLLECTION_NAME_2 = "qanoon_labour_clr"
EMBED_MODEL       = "BAAI/bge-small-en-v1.5"
RERANK_MODEL      = "cross-encoder/ms-marco-MiniLM-L-6-v2"
GROQ_MODEL        = "llama-3.3-70b-versatile"
TOP_K_RETRIEVE    = 12
TOP_K_FINAL       = 5
SCORE_THRESHOLD   = 0.70
EXCERPT_LEN       = 500

# ── XAI: confidence thresholds (based on cross-encoder rerank scores) ─────────
# ms-marco-MiniLM-L-6-v2 produces raw logit scores, typically in the range
# of about -10 to +10. Positive = relevant, negative = not relevant.
# Empirically on legal text:
#   > 2.0  → strong match (High)
#   -1 to 2.0 → partial match (Medium)
#   < -1.0 → weak match (Low)
CONFIDENCE_HIGH   =  2.0   # rerank_score ≥  2.0  → "High"
CONFIDENCE_MEDIUM = -1.0   # rerank_score ≥ -1.0  → "Medium"
                           # rerank_score <  -1.0  → "Low"

# Chunks whose rerank score is below this are excluded from the LLM prompt.
# Prevents irrelevant chunks from being cited (and confusing the model).
RERANK_NOISE_FLOOR = -3.0  # tune down if good results get filtered, up if noise persists

def _confidence_label(top_rerank_score: float) -> str:
    if top_rerank_score >= CONFIDENCE_HIGH:
        return "High"
    elif top_rerank_score >= CONFIDENCE_MEDIUM:
        return "Medium"
    else:
        return "Low"

def _confidence_score(top_rerank_score: float) -> float:
    """
    Maps rerank score to a 0–1 normalised confidence value for the frontend.
    Sigmoid centred at 0.5 (the neutral point for ms-marco logits),
    scale=2.5 so the curve spans the -10..+10 range comfortably.
    """
    import math
    val = 1 / (1 + math.exp(-(top_rerank_score - 0.5) / 2.5))
    return round(val, 3)


# ── Init ──────────────────────────────────────────────────────────────────────
print("Loading embedding model...")
embedder = SentenceTransformer(EMBED_MODEL)

print("Loading reranker...")
reranker = CrossEncoder(RERANK_MODEL)

chroma = chromadb.PersistentClient(path=CHROMA_PATH)
col1   = chroma.get_collection(COLLECTION_NAME_1)

try:
    col2 = chroma.get_collection(COLLECTION_NAME_2)
    print(f"✅ Both collections loaded ({col1.count()} + {col2.count()} chunks)")
except Exception:
    col2 = None
    print(f"⚠️  '{COLLECTION_NAME_2}' not found — using '{COLLECTION_NAME_1}' only")

groq_client = Groq(api_key=os.environ["GROQ_API_KEY"])

app = FastAPI(title="QanoonAI", version="3.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Schemas ───────────────────────────────────────────────────────────────────
class AskRequest(BaseModel):
    question: str
    session_document: str | None = None

class Citation(BaseModel):
    index:          int           # [1], [2] … matches inline markers in answer
    law_name:       str
    section_number: str
    section_title:  str
    excerpt:        str
    relevance_score: float        # XAI: normalised 0–1 rerank score
    why_relevant:   str           # XAI: one-sentence explanation from LLM

class XAIInfo(BaseModel):
    confidence_label: str         # "High" | "Medium" | "Low"
    confidence_score: float       # 0–1 normalised
    top_rerank_score: float       # raw cross-encoder score of best chunk
    num_sources_used: int

class AskResponse(BaseModel):
    answer:    str
    citations: list[Citation]
    xai:       XAIInfo | None     # None for conversational responses


# ── Junk filter ───────────────────────────────────────────────────────────────
_JUNK_RE = re.compile(
    r'(gazette of pakistan'
    r'|(ISLAMABAD|KARACHI|LAHORE|RAWALPINDI|PESHAWAR),?\s+'
    r'(MONDAY|TUESDAY|WEDNESDAY|THURSDAY|FRIDAY|SATURDAY|SUNDAY)'
    r'|No\.\s*(F\.|Legis)'
    r'|assent of the president'
    r'|hereby published for general)',
    re.IGNORECASE,
)

def _is_junk(text: str) -> bool:
    return bool(_JUNK_RE.search(text[:300]))


# ── Conversational intent detector ───────────────────────────────────────────
_CONVERSATIONAL_RE = re.compile(
    r'^\s*('
    r'hi+|hello+|hey+|salam|salaam|assalam|assalamualaikum'
    r'|how are you|how r u|how do you do'
    r'|good morning|good afternoon|good evening|good night'
    r'|thanks?|thank you|shukriya|jazakallah'
    r'|ok|okay|got it|understood|sure|great|nice|cool'
    r'|bye|goodbye|take care|see you'
    r'|who are you|what are you|what can you do|what is qanoon'
    r'|help|can you help'
    r')\s*[!\?\.]*\s*$',
    re.IGNORECASE,
)

def _is_conversational(question: str) -> bool:
    return bool(_CONVERSATIONAL_RE.match(question.strip()))


# ── Retrieval ─────────────────────────────────────────────────────────────────
def _query_collection(col, embedding: list[float], n: int) -> list[dict]:
    results = col.query(
        query_embeddings=[embedding],
        n_results=n,
        include=["documents", "metadatas", "distances"],
    )
    candidates = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        score = round(1 - dist, 3)
        if score < SCORE_THRESHOLD:
            continue
        if _is_junk(doc):
            continue
        if meta.get("ocr_quality", 1.0) < 0.45:
            continue
        candidates.append({
            "text":           doc,
            "law_name":       meta.get("law_name",       "Unknown Act"),
            "section_number": meta.get("section_number", ""),
            "section_title":  meta.get("section_title",  ""),
            "embed_score":    score,
        })
    return candidates


def retrieve(query: str) -> list[dict]:
    embedding = embedder.encode(query, normalize_embeddings=True).tolist()

    candidates = _query_collection(col1, embedding, TOP_K_RETRIEVE)
    if col2:
        candidates += _query_collection(col2, embedding, TOP_K_RETRIEVE)

    if not candidates:
        return []

    pairs  = [(query, c["text"]) for c in candidates]
    scores = reranker.predict(pairs)
    for c, s in zip(candidates, scores):
        c["rerank_score"] = float(s)

    candidates.sort(key=lambda x: x["rerank_score"], reverse=True)

    # Drop chunks below noise floor — they confuse the LLM and produce wrong citations.
    # Always keep at least 1 result so the LLM can still give a partial answer.
    filtered = [c for c in candidates if c["rerank_score"] >= RERANK_NOISE_FLOOR]
    if not filtered:
        filtered = candidates[:1]   # last resort: keep top chunk even if weak

    return filtered[:TOP_K_FINAL]


# ── Context builder ───────────────────────────────────────────────────────────
def build_context(chunks: list[dict], session_doc: str | None) -> str:
    parts = []

    if session_doc:
        parts.append(
            "=== UPLOADED EMPLOYMENT DOCUMENT ===\n"
            + session_doc[:3000]
            + "\n=== END OF DOCUMENT ===\n"
        )

    if chunks:
        parts.append("=== RELEVANT PAKISTANI LABOUR LAW PROVISIONS ===")
        for i, c in enumerate(chunks, 1):
            sec   = f"§ {c['section_number']}" if c["section_number"] not in ("", "N/A") else ""
            title = f"— {c['section_title']}"  if c.get("section_title") and c["section_title"] not in ("", "N/A") else ""
            parts.append(
                f"\n[{i}] {c['law_name']} {sec} {title}\n"
                f"{c['text']}\n"
            )

    return "\n".join(parts)


# ── System prompt ─────────────────────────────────────────────────────────────
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


# ── XAI response parser ───────────────────────────────────────────────────────
_XAI_BLOCK_RE = re.compile(r'<xai>\s*(.*?)\s*</xai>', re.DOTALL)

def _parse_xai_block(raw_response: str) -> tuple[str, dict]:
    """
    Splits the LLM response into (answer_text, xai_data).
    xai_data is the parsed JSON dict, or {} if missing/malformed.
    """
    match = _XAI_BLOCK_RE.search(raw_response)
    if not match:
        return raw_response.strip(), {}

    answer = raw_response[:match.start()].strip()
    try:
        xai_data = json.loads(match.group(1))
    except json.JSONDecodeError:
        xai_data = {}

    return answer, xai_data


def _why_relevant_map(xai_data: dict) -> dict[int, str]:
    """Returns {citation_index: why_relevant_text} from parsed XAI data."""
    result = {}
    for entry in xai_data.get("citations", []):
        idx = entry.get("index")
        why = entry.get("why_relevant", "")
        if idx and why:
            result[int(idx)] = why
    return result


# ── Groq call ─────────────────────────────────────────────────────────────────
def ask_groq(question: str, context: str, is_conversational: bool) -> str:
    if is_conversational:
        user_msg = question
    else:
        user_msg = (
            f"Pakistani labour law context:\n\n{context}\n\n"
            f"Worker's question: {question}\n\n"
            "Answer using inline citation markers [1], [2], etc. from the numbered provisions above. "
            "Then append the <xai> JSON block as instructed."
        )

    resp = groq_client.chat.completions.create(
        model    = GROQ_MODEL,
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_msg},
        ],
        temperature = 0.2 if is_conversational else 0.1,
        max_tokens  = 256  if is_conversational else 900,
    )
    return resp.choices[0].message.content.strip()


# ── Normalise rerank score to 0–1 for the frontend ───────────────────────────
def _normalise_rerank(score: float, all_scores: list[float]) -> float:
    """
    Min-max normalise a rerank score relative to the retrieved batch.
    Gives frontend a clean 0–1 relevance bar per citation.
    """
    mn, mx = min(all_scores), max(all_scores)
    if mx == mn:
        return 1.0
    return round((score - mn) / (mx - mn), 3)


# ── PDF extraction ────────────────────────────────────────────────────────────
def extract_pdf_text(file_bytes: bytes) -> str:
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name
    text = ""
    try:
        with pdfplumber.open(tmp_path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text += t + "\n"
    finally:
        os.unlink(tmp_path)
    return text.strip()


# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    counts = {"qanoon_labour": col1.count()}
    if col2:
        counts["qanoon_labour_clr"] = col2.count()
    return {"status": "ok", "collections": counts}


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    conversational = _is_conversational(question)

    if conversational:
        raw    = ask_groq(question, "", is_conversational=True)
        answer = raw  # no XAI block expected for greetings
        return AskResponse(answer=answer, citations=[], xai=None)

    # ── Legal question path ───────────────────────────────────────────────────
    chunks  = retrieve(question)
    context = build_context(chunks, req.session_document)
    raw     = ask_groq(question, context, is_conversational=False)

    # Parse answer + XAI block
    answer, xai_data  = _parse_xai_block(raw)
    why_relevant_map  = _why_relevant_map(xai_data)

    # ── XAI: confidence from top rerank score ─────────────────────────────────
    if chunks:
        all_rerank_scores = [c["rerank_score"] for c in chunks]
        top_score         = all_rerank_scores[0]   # already sorted descending
        xai_info = XAIInfo(
            confidence_label = _confidence_label(top_score),
            confidence_score = _confidence_score(top_score),
            top_rerank_score = round(top_score, 3),
            num_sources_used = len(chunks),
        )
    else:
        xai_info = XAIInfo(
            confidence_label = "Low",
            confidence_score = 0.0,
            top_rerank_score = 0.0,
            num_sources_used = 0,
        )

    # ── Build deduplicated citations with XAI fields ──────────────────────────
    seen, citations = set(), []
    all_rerank_scores = [c["rerank_score"] for c in chunks] if chunks else [0.0]

    for i, c in enumerate(chunks, 1):
        key = f"{c['law_name']}_{c['section_number']}"
        if key in seen:
            continue
        seen.add(key)

        raw_excerpt = c["text"][:EXCERPT_LEN]
        last_period = raw_excerpt.rfind('.')
        excerpt     = raw_excerpt[:last_period + 1] if last_period > 100 else raw_excerpt

        citations.append(Citation(
            index           = i,
            law_name        = c["law_name"],
            section_number  = c["section_number"],
            section_title   = c.get("section_title", ""),
            excerpt         = excerpt,
            relevance_score = _normalise_rerank(c["rerank_score"], all_rerank_scores),
            why_relevant    = why_relevant_map.get(i, ""),
        ))

    return AskResponse(answer=answer, citations=citations, xai=xai_info)


@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files accepted")
    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 5 MB)")
    text = extract_pdf_text(contents)
    if len(text.strip()) < 50:
        raise HTTPException(
            status_code=422,
            detail="Could not extract text from this PDF. It may be scanned/image-based.",
        )
    return {"filename": file.filename, "extracted_text": text, "char_count": len(text)}