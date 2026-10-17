import os
import pdfplumber
import fitz
import pytesseract
from pdf2image import convert_from_path
from utils.cleaner import clean_gazette_text

pytesseract.pytesseract.tesseract_cmd = r'D:\tesseract\tesseract.exe'
POPPLER_PATH = r'D:\poppler\Release-25.12.0-0\poppler-25.12.0\Library\bin'
PDF_FOLDER = "data/raw_pdfs"
OUTPUT_FOLDER = "data/extracted_text"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def is_mirrored(text: str) -> bool:
    sample = text.replace(" ", "").replace("\n", "")[:300]
    if len(sample) == 0:
        return False
    doubled = sum(1 for i in range(len(sample)-1) if sample[i] == sample[i+1])
    return (doubled / len(sample)) > 0.15

def extract_text(pdf_path: str) -> tuple[str, str]:
    # Step 1 — try pdfplumber
    with pdfplumber.open(pdf_path) as pdf:
        raw = ""
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                raw += t + "\n"

    # Step 2 — if mirrored, try pymupdf
    if is_mirrored(raw):
        doc = fitz.open(pdf_path)
        raw = ""
        for page in doc:
            raw += page.get_text() + "\n"

    # Step 3 — if still empty, use OCR
    if len(raw.strip()) < 100:
        images = convert_from_path(pdf_path, dpi=300, poppler_path=POPPLER_PATH)
        raw = ""
        for img in images:
            raw += pytesseract.image_to_string(img) + "\n"
        if len(raw.strip()) < 100:
            return "", "failed"
        return raw, "ocr"

    if is_mirrored(raw):
        return raw, "pymupdf"
    return raw, "pdfplumber"

# Process all PDFs
summary = {"pdfplumber": [], "pymupdf": [], "ocr": [], "failed": []}

for filename in sorted(os.listdir(PDF_FOLDER)):
    if not filename.endswith(".pdf"):
        continue

    path = os.path.join(PDF_FOLDER, filename)
    print(f"Processing: {filename[:60]}...")

    text, method = extract_text(path)
    cleaned = clean_gazette_text(text)
    summary[method].append(filename)

    if method == "failed" or len(cleaned) < 100:
        print(f"  ❌ FAILED — skipping")
        continue

    # Save cleaned text
    out_name = filename.replace(".pdf", ".txt")
    with open(os.path.join(OUTPUT_FOLDER, out_name), "w", encoding="utf-8") as f:
        f.write(cleaned)

    print(f"  ✅ [{method}] {len(cleaned)} chars saved")

print("\n=== FINAL SUMMARY ===")
print(f"✅ pdfplumber : {len(summary['pdfplumber'])}")
print(f"🔧 pymupdf   : {len(summary['pymupdf'])}")
print(f"🔍 ocr       : {len(summary['ocr'])}")
print(f"❌ failed    : {len(summary['failed'])}")
for f in summary['failed']:
    print(f"   → {f}")