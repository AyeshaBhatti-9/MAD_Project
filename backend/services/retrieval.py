import re
import chromadb
from sentence_transformers import SentenceTransformer, CrossEncoder

from ..config import (
    CHROMA_PATH, COLLECTION_NAME_1, COLLECTION_NAME_2,
    EMBED_MODEL, RERANK_MODEL,
    TOP_K_RETRIEVE, TOP_K_FINAL, SCORE_THRESHOLD, RERANK_NOISE_FLOOR,
    MAX_DOC_CHARS,
)

# ── Init (runs once, when the module is first imported) ──────────────────────
print("Loading embedding model...")
embedder = SentenceTransformer(EMBED_MODEL)

print("Loading reranker...")
reranker = CrossEncoder(RERANK_MODEL)

chroma = chromadb.PersistentClient(path=CHROMA_PATH)
col1 = chroma.get_collection(COLLECTION_NAME_1)

try:
    col2 = chroma.get_collection(COLLECTION_NAME_2)
    print(f"✅ Both collections loaded ({col1.count()} + {col2.count()} chunks)")
except Exception:
    col2 = None
    print(f"⚠️  '{COLLECTION_NAME_2}' not found, using '{COLLECTION_NAME_1}' only")


# ── Junk filter ──────────────────────────────────────────────────────────────
_JUNK_RE = re.compile(
    r'(gazette of pakistan'
    r'|(ISLAMABAD|KARACHI|LAHORE|RAWALPINDI|PESHAWAR),?\s+'
    r'(MONDAY|TUESDAY|WEDNESDAY|THURSDAY|FRIDAY|SATURDAY|SUNDAY)'
    r'|No\.\s*(F\.|Legis)'
    r'|assent of the president'
    r'|hereby published for general)',
    re.IGNORECASE,
)

def is_junk(text: str) -> bool:
    return bool(_JUNK_RE.search(text[:300]))


# ── Retrieval ────────────────────────────────────────────────────────────────
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
        if is_junk(doc):
            continue
        if meta.get("ocr_quality", 1.0) < 0.45:
            continue
        candidates.append({
            "text":           doc,
            "law_name":       meta.get("law_name", "Unknown Act"),
            "section_number": meta.get("section_number", ""),
            "section_title":  meta.get("section_title", ""),
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

    scores = reranker.predict([(query, c["text"]) for c in candidates])
    for c, s in zip(candidates, scores):
        c["rerank_score"] = float(s)

    candidates.sort(key=lambda x: x["rerank_score"], reverse=True)

    # Drop weak chunks, but always keep at least the best one
    filtered = [c for c in candidates if c["rerank_score"] >= RERANK_NOISE_FLOOR]
    if not filtered:
        filtered = candidates[:1]

    return filtered[:TOP_K_FINAL]


# ── Context builder ──────────────────────────────────────────────────────────
def build_context(chunks: list[dict], session_doc: str | None) -> str:
    parts = []

    if session_doc:
        parts.append(
            "=== UPLOADED EMPLOYMENT DOCUMENT ===\n"
            + session_doc[:MAX_DOC_CHARS]
            + "\n=== END OF DOCUMENT ===\n"
        )

    if chunks:
        parts.append("=== RELEVANT PAKISTANI LABOUR LAW PROVISIONS ===")
        for i, c in enumerate(chunks, 1):
            sec = f"§ {c['section_number']}" if c["section_number"] not in ("", "N/A") else ""
            title = (f"— {c['section_title']}"
                     if c.get("section_title") and c["section_title"] not in ("", "N/A") else "")
            parts.append(f"\n[{i}] {c['law_name']} {sec} {title}\n{c['text']}\n")

    return "\n".join(parts)