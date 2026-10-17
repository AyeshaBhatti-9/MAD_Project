import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent   # Backend/
load_dotenv(BASE_DIR / ".env")

# Paths (absolute, so it no longer matters where you run from)
CHROMA_PATH = str(BASE_DIR / "data" / "chroma_db")
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'app.db'}")

# Secrets
GROQ_API_KEY = os.environ["GROQ_API_KEY"]
SECRET_KEY = os.environ["SECRET_KEY"]
JWT_ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = 60 * 24 * 7   # 7 days

# RAG (copied from your old main.py)
COLLECTION_NAME_1 = "qanoon_labour"
COLLECTION_NAME_2 = "qanoon_labour_clr"
EMBED_MODEL = "BAAI/bge-small-en-v1.5"
RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
GROQ_MODEL = "fake"
#"openai/gpt-oss-120b"
TOP_K_RETRIEVE = 12
TOP_K_FINAL = 5
SCORE_THRESHOLD = 0.70
EXCERPT_LEN = 500
CONFIDENCE_HIGH = 2.0
CONFIDENCE_MEDIUM = -1.0
RERANK_NOISE_FLOOR = -3.0

# Chat
HISTORY_LIMIT = 6   # previous messages sent to the LLM for follow-ups
# Limits
MAX_DOC_CHARS = 8000              # contract text sent to the LLM
ASK_RATE_LIMIT = "10/minute"      # per IP
UPLOAD_RATE_LIMIT = "5/minute"
LOGIN_RATE_LIMIT = "10/minute"
SIGNUP_RATE_LIMIT = "5/minute"

# CORS: comma-separated list in .env, "*" while developing
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",")]