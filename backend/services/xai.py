import math

from ..config import CONFIDENCE_HIGH, CONFIDENCE_MEDIUM, EXCERPT_LEN
from ..schemas import Citation, XAIInfo


def confidence_label(score: float) -> str:
    if score >= CONFIDENCE_HIGH:
        return "High"
    if score >= CONFIDENCE_MEDIUM:
        return "Medium"
    return "Low"


def confidence_score(score: float) -> float:
    """Sigmoid maps the raw cross-encoder logit to 0-1 for the frontend."""
    return round(1 / (1 + math.exp(-(score - 0.5) / 2.5)), 3)


def normalise_rerank(score: float, all_scores: list[float]) -> float:
    """Min-max normalise within the retrieved batch (per-citation relevance bar)."""
    mn, mx = min(all_scores), max(all_scores)
    return 1.0 if mx == mn else round((score - mn) / (mx - mn), 3)


def build_citations_and_xai(chunks: list[dict], why_map: dict[int, str]):
    if not chunks:
        return [], XAIInfo(
            confidence_label="Low", confidence_score=0.0,
            top_rerank_score=0.0, num_sources_used=0,
        )

    scores = [c["rerank_score"] for c in chunks]
    top = scores[0]  # chunks are already sorted descending

    xai = XAIInfo(
        confidence_label=confidence_label(top),
        confidence_score=confidence_score(top),
        top_rerank_score=round(top, 3),
        num_sources_used=len(chunks),
    )

    seen, citations = set(), []
    for i, c in enumerate(chunks, 1):
        key = f"{c['law_name']}_{c['section_number']}"
        if key in seen:
            continue
        seen.add(key)

        raw = c["text"][:EXCERPT_LEN]
        cut = raw.rfind(".")
        excerpt = raw[:cut + 1] if cut > 100 else raw

        citations.append(Citation(
            index=i,  # matches the [N] number given to the LLM in build_context
            law_name=c["law_name"],
            section_number=c["section_number"],
            section_title=c.get("section_title", ""),
            excerpt=excerpt,
            relevance_score=normalise_rerank(c["rerank_score"], scores),
            why_relevant=why_map.get(i, ""),
        ))

    return citations, xai