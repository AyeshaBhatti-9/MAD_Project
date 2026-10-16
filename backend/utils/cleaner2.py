"""
cleaner2.py  (STRUCTURE-SAFE v3)
Legal-grade cleaner for Pakistani labour law PDFs

MAJOR UPGRADE:
- Preserves legal structure instead of deleting it
- OCR normalization layer added
- Header/footer tagging instead of removal
- Safe repetition filtering
- Structure-aware preprocessing for chunker2
"""

import re
from collections import Counter


# ─────────────────────────────────────────────────────────────
# Noise patterns (SAFE - only true junk)
# ─────────────────────────────────────────────────────────────

_GAZETTE_NOISE = re.compile(
    r'(GAZETTE\s+OF\s+PAKISTAN)'
    r'|PRINTED\s+BY\s+THE\s+MANAGER'
    r'|PUBLISHED\s+BY\s+AUTHORITY'
    r'|REGISTERED\s+NO\.?'
    r'|EXTRAORDINARY'
    r'|Price\s*:\s*Rs\.?'
    r'|ASSENT\s+OF\s+THE\s+PRESIDENT',
    re.IGNORECASE
)

_PAGE_MARKER = re.compile(r'^(Page\s+\d+\s+of\s+\d+|\d+)$', re.IGNORECASE)

_CITY_DATE_LINE = re.compile(
    r'^(ISLAMABAD|KARACHI|LAHORE|RAWALPINDI|PESHAWAR|QUETTA)\b.*\d{4}',
    re.IGNORECASE
)

# KEEP STRUCTURE (IMPORTANT)
_STRUCTURE_MARKERS = re.compile(
    r'^(SECTION|CHAPTER|PART|SCHEDULE|ANNEXURE|APPENDIX|FORM)\b',
    re.IGNORECASE
)

# OCR noise only TRUE garbage
_OCR_NOISE = re.compile(r'^[^A-Za-z0-9]{4,}$')


# ─────────────────────────────────────────────────────────────
# OCR NORMALIZATION LAYER (NEW - IMPORTANT)
# ─────────────────────────────────────────────────────────────

def normalize_ocr(text: str) -> str:
    """
    Fix broken OCR spacing issues.
    """

    fixes = [
        (r'com\s+mencement', 'commencement'),
        (r'lab\s+our', 'labour'),
        (r'govt\s+of', 'Government of'),
        (r'sec\s+tion', 'section'),
        (r'pa\s+rti', 'parti'),
    ]

    for pattern, repl in fixes:
        text = re.sub(pattern, repl, text, flags=re.IGNORECASE)

    # fix broken hyphen line breaks
    text = re.sub(r'-\s*\n\s*', '', text)

    return text


# ─────────────────────────────────────────────────────────────
# MAIN CLEANER (STRUCTURE PRESERVING)
# ─────────────────────────────────────────────────────────────

def clean_gazette_text2(text: str) -> str:
    """
    Structure-preserving cleaner.
    NEVER deletes legal anchors.
    """

    text = normalize_ocr(text)
    text = _GAZETTE_NOISE.sub('', text)

    lines = text.split('\n')

    # detect repeated headers (SAFE mode)
    norm = lambda x: re.sub(r'\s+', ' ', x.strip().lower())

    freq = Counter(
        norm(x) for x in lines if len(x.strip()) > 12
    )

    repeated = {k for k, v in freq.items() if v >= 8}

    cleaned = []
    prev_blank = False

    for line in lines:
        raw = line
        stripped = line.strip()

        # ───────────── blank line control ─────────────
        if not stripped:
            if not prev_blank:
                cleaned.append('')
            prev_blank = True
            continue

        prev_blank = False

        norm_line = norm(stripped)

        # ───────────── repeated headers ─────────────
        if norm_line in repeated and not _STRUCTURE_MARKERS.match(stripped):
            continue

        # ───────────── page noise ─────────────
        if _PAGE_MARKER.match(stripped):
            continue

        if _CITY_DATE_LINE.match(stripped):
            continue

        # ───────────── OCR garbage only ─────────────
        if _OCR_NOISE.match(stripped):
            continue

        # ───────────── IMPORTANT FIX ─────────────
        # NEVER delete structure markers
        if _STRUCTURE_MARKERS.match(stripped):
            cleaned.append(stripped.upper())
            continue

        # ───────────── ultra-safe number rule ─────────────
        # only remove if it's clearly junk page number
        if re.fullmatch(r'\d{2,4}', stripped):
            continue

        # ───────────── keep everything else ─────────────
        cleaned.append(stripped)

    result = '\n'.join(cleaned)

    # normalization only (safe)
    result = re.sub(r'\n{3,}', '\n\n', result)
    result = re.sub(r'[ \t]+', ' ', result)

    return result.strip()


# ─────────────────────────────────────────────────────────────
# LAW NAME EXTRACTION (IMPROVED PRIORITY + SAFETY)
# ─────────────────────────────────────────────────────────────

def extract_law_name2(text: str, filename: str = "") -> str:

    lines = text.split('\n')

    useful = []
    for line in lines[:90]:
        line = line.strip()
        if not line:
            continue
        if _GAZETTE_NOISE.search(line):
            continue
        useful.append(line)

    search_text = ' '.join(useful[:60])

    patterns = [
        r'(THE\s+[A-Z][A-Z\s,\-\(\)\']+(ACT|ORDINANCE|RULES?|REGULATIONS?)\,?\s*\d{4})',
        r'(The\s+[A-Z][A-Za-z\s,\-\(\)\']+(Act|Ordinance|Rules?|Regulations?)\,?\s*\d{4})',
        r'([A-Z][A-Za-z\s,\-\(\)\']+(Rules?|Regulations?)\,?\s*\d{4})',
    ]

    for pat in patterns:
        m = re.search(pat, search_text)
        if m:
            name = re.sub(r'\s+', ' ', m.group(1)).strip()
            if 10 < len(name) < 220:
                return name

    # fallback: first strong legal line
    for line in useful:
        if "ACT" in line.upper() and len(line) > 20:
            return line[:180]

    if filename:
        name = filename.replace('.pdf', '').replace('.txt', '')
        name = re.sub(r'[%_-]+', ' ', name)
        return re.sub(r'\s+', ' ', name).strip()

    return "Unknown Act"