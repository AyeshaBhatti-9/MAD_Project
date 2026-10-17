from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..config import HISTORY_LIMIT
from ..database import get_db
from ..models import User, Conversation, Message, utcnow
from ..services.intent import is_conversational
from ..services.retrieval import retrieve, build_context
from ..services.llm import ask_groq, parse_xai_block, why_relevant_map
from ..services.xai import build_citations_and_xai
from ..deps import get_current_user, get_optional_user
from ..schemas import (AskRequest, AskResponse, ConversationOut, ConversationDetail)

router = APIRouter(prefix="/chat", tags=["chat"])


def _get_owned_conversation(db: Session, convo_id: int, user: User) -> Conversation:
    convo = db.query(Conversation).filter_by(id=convo_id, user_id=user.id).first()
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return convo


MAX_GUEST_HISTORY = HISTORY_LIMIT


def _answer(question: str, history: list[dict], session_document: str | None):
    """Shared RAG pipeline for guests and signed-in users."""
    if is_conversational(question):
        return ask_groq(question, "", True, history), [], None

    # Short follow-ups retrieve badly alone, so prepend the last user question.
    last_q = next((m["content"] for m in reversed(history) if m["role"] == "user"), "")
    search_query = f"{last_q} {question}" if last_q and len(question.split()) < 8 else question

    chunks = retrieve(search_query)
    context = build_context(chunks, session_document)
    raw = ask_groq(question, context, False, history)
    answer, xai_data = parse_xai_block(raw)
    citations, xai = build_citations_and_xai(chunks, why_relevant_map(xai_data))
    return answer, citations, xai


@router.post("/ask", response_model=AskResponse)
def ask(req: AskRequest, db: Session = Depends(get_db),
        user: User | None = Depends(get_optional_user)):
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    # ── Guest: answer only, store nothing ──
    if user is None:
        history = [t.model_dump() for t in (req.history or [])
                   if t.role in ("user", "assistant")][-MAX_GUEST_HISTORY:]
        answer, citations, xai = _answer(question, history, req.session_document)
        return AskResponse(conversation_id=None, answer=answer, citations=citations, xai=xai)

    # ── Signed in: answer and save ──
    if req.conversation_id:
        convo = _get_owned_conversation(db, req.conversation_id, user)
    else:
        convo = Conversation(user_id=user.id, title=question[:60])
        db.add(convo)
        db.flush()

    previous = convo.messages[-HISTORY_LIMIT:]
    history = [{"role": m.role, "content": m.content} for m in previous]
    answer, citations, xai = _answer(question, history, req.session_document)

    db.add(Message(conversation_id=convo.id, role="user", content=question))
    db.add(Message(
        conversation_id=convo.id, role="assistant", content=answer,
        citations=[c.model_dump() for c in citations],
        xai=xai.model_dump() if xai else None,
    ))
    convo.updated_at = utcnow()
    db.commit()

    return AskResponse(conversation_id=convo.id, answer=answer, citations=citations, xai=xai)


@router.get("/conversations", response_model=list[ConversationOut])
def list_conversations(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return (db.query(Conversation).filter_by(user_id=user.id)
              .order_by(Conversation.updated_at.desc()).all())


@router.get("/conversations/{convo_id}", response_model=ConversationDetail)
def get_conversation(convo_id: int, db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    return _get_owned_conversation(db, convo_id, user)


@router.delete("/conversations/{convo_id}", status_code=204)
def delete_conversation(convo_id: int, db: Session = Depends(get_db),
                        user: User = Depends(get_current_user)):
    db.delete(_get_owned_conversation(db, convo_id, user))
    db.commit()