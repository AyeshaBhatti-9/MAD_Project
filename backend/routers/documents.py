from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user, get_optional_user
from ..models import User, Document
from ..schemas import DocumentOut, DocumentDetail, UploadResponse
from ..services.pdf import extract_pdf_text
from ..config import UPLOAD_RATE_LIMIT
from ..limiter import limiter

router = APIRouter(prefix="/documents", tags=["documents"])

MAX_SIZE = 5 * 1024 * 1024
MAX_DOCS_PER_USER = 20


def _get_owned_document(db: Session, doc_id: int, user: User) -> Document:
    doc = db.query(Document).filter_by(id=doc_id, user_id=user.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.post("/upload", response_model=UploadResponse)
@limiter.limit(UPLOAD_RATE_LIMIT)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user),
):
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files accepted")

    contents = await file.read()
    if len(contents) > MAX_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 5 MB)")

    text = extract_pdf_text(contents)
    if len(text.strip()) < 50:
        raise HTTPException(
            status_code=422,
            detail="Could not extract text from this PDF. It may be scanned/image-based.",
        )

    # Guest: return the text only, nothing is stored
    if user is None:
        return UploadResponse(id=None, filename=file.filename, extracted_text=text,
                              char_count=len(text), saved=False)

    # Signed in: enforce a cap, then save
    count = db.query(Document).filter_by(user_id=user.id).count()
    if count >= MAX_DOCS_PER_USER:
        raise HTTPException(status_code=409,
            detail=f"Document limit reached ({MAX_DOCS_PER_USER}). Delete one to upload more.")

    doc = Document(user_id=user.id, filename=file.filename,
                   extracted_text=text, char_count=len(text))
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return UploadResponse(id=doc.id, filename=doc.filename, extracted_text=text,
                          char_count=doc.char_count, saved=True)


@router.get("", response_model=list[DocumentOut])
def list_documents(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return (db.query(Document).filter_by(user_id=user.id)
              .order_by(Document.created_at.desc()).all())


@router.get("/{doc_id}", response_model=DocumentDetail)
def get_document(doc_id: int, db: Session = Depends(get_db),
                 user: User = Depends(get_current_user)):
    return _get_owned_document(db, doc_id, user)


@router.delete("/{doc_id}", status_code=204)
def delete_document(doc_id: int, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    db.delete(_get_owned_document(db, doc_id, user))
    db.commit()