from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .config import CORS_ORIGINS
from .database import Base, engine
from . import models  # noqa: F401  (registers the tables)
from .limiter import limiter
from .routers import auth, chat, documents
from .services.llm import LLMUnavailable
from .services.retrieval import col1, col2

Base.metadata.create_all(bind=engine)

app = FastAPI(title="QanoonAI", version="4.1")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.exception_handler(LLMUnavailable)
async def llm_unavailable_handler(request: Request, exc: LLMUnavailable):
    return JSONResponse(
        status_code=503,
        content={"detail": "The assistant is temporarily unavailable. Please try again in a moment."},
    )

app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS,
                   allow_methods=["*"], allow_headers=["*"])

app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(documents.router)

@app.get("/health")
def health():
    counts = {"qanoon_labour": col1.count()}
    if col2:
        counts["qanoon_labour_clr"] = col2.count()
    return {"status": "ok", "collections": counts}