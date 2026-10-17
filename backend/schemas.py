from datetime import datetime
from pydantic import BaseModel, EmailStr, Field

# ── Auth ──
class SignupRequest(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8, max_length=72)   # bcrypt limit is 72 bytes

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    email: str
    name: str
    model_config = {"from_attributes": True}

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

# ── Chat ──
class ChatTurn(BaseModel):
    role: str          # "user" | "assistant"
    content: str

class AskRequest(BaseModel):
    question: str
    conversation_id: int | None = None
    session_document: str | None = None
    history: list[ChatTurn] | None = None   # guests only: last few turns kept in the app

class Citation(BaseModel):
    index: int
    law_name: str
    section_number: str
    section_title: str
    excerpt: str
    relevance_score: float
    why_relevant: str

class XAIInfo(BaseModel):
    confidence_label: str
    confidence_score: float
    top_rerank_score: float
    num_sources_used: int

class AskResponse(BaseModel):
    conversation_id: int | None      # None for guests
    answer: str
    citations: list[Citation]
    xai: XAIInfo | None

# ── History ──
class ConversationOut(BaseModel):
    id: int
    title: str
    updated_at: datetime
    model_config = {"from_attributes": True}

class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    citations: list[dict] | None
    xai: dict | None
    created_at: datetime
    model_config = {"from_attributes": True}

class ConversationDetail(BaseModel):
    id: int
    title: str
    messages: list[MessageOut]
    model_config = {"from_attributes": True}