import os
import re
import pdfplumber
import fitz
import pytesseract
from pdf2image import convert_from_path
from utils.cleaner2 import clean_gazette_text2

pytesseract.pytesseract.tesseract_cmd = r'D:\tesseract\tesseract.exe'
POPPLER_PATH = r'D:\poppler\Release-25.12.0-0\poppler-25.12.0\Library\bin'

PDF_FOLDER = "data/raw_pdfs2"
OUTPUT_FOLDER = "data/extracted_text_clr"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


# ─────────────────────────────────────────────
# QUALITY SCORING (NEW)
# ─────────────────────────────────────────────

def score_text(text: str) -> float:
    if not text:
        return 0

    words = len(text.split())
    noise = len(re.findall(r'[^A-Za-z0-9\s\.\,\(\)\-\:\n]', text))

    return words / (noise + 1)


# ─────────────────────────────────────────────
# MIRROR DETECTION (IMPROVED)
# ─────────────────────────────────────────────

def is_mirrored(text: str) -> bool:
    sample = text.replace(" ", "").replace("\n", "")[:500]
    if len(sample) < 50:
        return True

    repeated = sum(
        1 for i in range(len(sample) - 1)
        if sample[i] == sample[i + 1]
    )

    return (repeated / len(sample)) > 0.10


# ─────────────────────────────────────────────
# PAGE CLEANER (NEW)
# ─────────────────────────────────────────────

def clean_page(text: str) -> str:
    lines = text.split("\n")
    cleaned = []

    for l in lines:
        l = l.strip()

        if not l:
            continue

        # remove page numbers
        if re.fullmatch(r'\d{1,4}', l):
            continue

        # remove extreme noise
        if len(re.findall(r'[A-Za-z]', l)) < 3:
            continue

        cleaned.append(l)

    return "\n".join(cleaned)


# ─────────────────────────────────────────────
# EXTRACTION ENGINE (FIXED)
# ─────────────────────────────────────────────

def extract_text(pdf_path: str) -> tuple[str, str]:

    candidates = []

    # ── PDFPLUMBER ──
    try:
        raw = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    raw += clean_page(t) + "\n"

        candidates.append((raw, "pdfplumber"))
    except:
        pass

    # ── PYMUPDF ──
    try:
        doc = fitz.open(pdf_path)
        raw2 = ""
        for page in doc:
            raw2 += clean_page(page.get_text()) + "\n"
        doc.close()

        candidates.append((raw2, "pymupdf"))
    except:
        pass

    # ── OCR ──
    try:
        images = convert_from_path(pdf_path, dpi=300, poppler_path=POPPLER_PATH)

        ocr = ""
        for img in images:
            ocr += pytesseract.image_to_string(img) + "\n"

        candidates.append((ocr, "ocr"))
    except:
        pass

    # ── choose best ──
    best_text, best_method = "", "failed"
    best_score = 0

    for text, method in candidates:

        if len(text.strip()) < 100:
            continue

        if is_mirrored(text):
            continue

        s = score_text(text)

        if s > best_score:
            best_score = s
            best_text = text
            best_method = method

    if best_text:
        return best_text, best_method

    return "", "failed"


# ─────────────────────────────────────────────
# PROCESS PIPELINE
# ─────────────────────────────────────────────

summary = {"pdfplumber": [], "pymupdf": [], "ocr": [], "failed": []}

for filename in sorted(os.listdir(PDF_FOLDER)):

    if not filename.endswith(".pdf"):
        continue

    path = os.path.join(PDF_FOLDER, filename)
    print(f"Processing: {filename[:60]}...")

    text, method = extract_text(path)
    summary[method].append(filename)

    if method == "failed":
        print("  ❌ FAILED")
        continue

    cleaned = clean_gazette_text2(text)

    if len(cleaned.strip()) < 100:
        print("  ⚠️ SKIP after cleaning")
        summary["failed"].append(filename)
        continue

    out_name = filename.replace(".pdf", ".txt")
    out_path = os.path.join(OUTPUT_FOLDER, out_name)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(cleaned)

    print(f"  ✅ [{method}] {len(cleaned)} chars → {out_name}")


# ── SUMMARY ──
print("\n=== FINAL SUMMARY ===")
for k, v in summary.items():
    print(f"{k}: {len(v)}")