from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from ..deps import get_current_user
from ..models import User
from ..services.pdf import extract_pdf_text
from ..deps import get_optional_user

router = APIRouter(prefix="/documents", tags=["documents"])

@router.post("/upload")
async def upload_document(file: UploadFile = File(...), user: User | None = Depends(get_optional_user)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files accepted")
    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 5 MB)")
    text = extract_pdf_text(contents)
    if len(text.strip()) < 50:
        raise HTTPException(status_code=422,
            detail="Could not extract text from this PDF. It may be scanned/image-based.")
    return {"filename": file.filename, "extracted_text": text, "char_count": len(text)}