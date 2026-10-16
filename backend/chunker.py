import re

# ── Fuzzy junk detection ──────────────────────────────────────────────────────
# OCR mangles exact strings, so use loose patterns instead of literals.

_JUNK_PATTERNS = [
    re.compile(r'gazette\s+of\s+pakistan',                          re.IGNORECASE),
    # datelines: "ISLAMABAD, TUESDAY" — OCR may drop comma
    re.compile(r'(islamabad|karachi|lahore|rawalpindi|peshawar).{0,3}'
               r'(monday|tuesday|wednesday|thursday|friday|saturday|sunday)', re.IGNORECASE),
    # gazette notice numbers: "No. F.22", "No. Leg", "No. Legis", "No. Leg,"
    re.compile(r'\bNo\.?\s{0,2}(F\.|Leg)',                          re.IGNORECASE),
    re.compile(r'assent\s+of\s+the\s+president',                    re.IGNORECASE),
    re.compile(r'hereby\s+published\s+for\s+general',               re.IGNORECASE),
    re.compile(r'Acts,?\s+Ordinances,?\s+President',                re.IGNORECASE),
    re.compile(r'Majlis.e.Shoora',                                   re.IGNORECASE),
    # preamble noise: "WHEREAS it is expedient" with no section content
    re.compile(r'^WHEREAS\s+it\s+is\s+expedient',                   re.IGNORECASE | re.MULTILINE),
    # martial law / administrator boilerplate
    re.compile(r'Administrator\s+of\s+Martial\s+Law',               re.IGNORECASE),
    re.compile(r'exercising\s+the\s+powers\s+of\s+the\s+Governor',  re.IGNORECASE),
]

def _is_junk_chunk(text: str) -> bool:
    head = text[:400]   # slightly wider window than before
    return any(p.search(head) for p in _JUNK_PATTERNS)


# ── OCR quality scoring ───────────────────────────────────────────────────────
_NON_ASCII_RE  = re.compile(r'[^\x00-\x7F]')
_GARBLED_RE    = re.compile(r'[a-z]{2,}[A-Z]{2,}|[A-Z]{2,}[a-z]{2,}[A-Z]')  # cAsEmix
_SHORT_WORD_RE = re.compile(r'\b[a-z]{1,2}\b')   # lots of "nt", "ck", "fk" = OCR noise

def ocr_quality_score(text: str) -> float:
    """
    Returns 0.0 (garbage) to 1.0 (clean).
    Anything below ~0.45 is likely bad OCR and should be flagged.
    """
    if not text:
        return 0.0
    words = text.split()
    if not words:
        return 0.0

    non_ascii_ratio  = len(_NON_ASCII_RE.findall(text)) / max(len(text), 1)
    garbled_ratio    = len(_GARBLED_RE.findall(text))   / max(len(words), 1)
    short_word_ratio = len(_SHORT_WORD_RE.findall(text)) / max(len(words), 1)

    # Weighted penalty
    score = 1.0 - (non_ascii_ratio * 2.0 + garbled_ratio * 1.5 + short_word_ratio * 0.5)
    return max(0.0, min(1.0, score))


OCR_QUALITY_THRESHOLD = 0.45   # chunks below this are marked low-quality


# ── Law name helpers ──────────────────────────────────────────────────────────
def law_name_from_pdf_filename(filename: str) -> str:
    name = filename.replace(".txt", "").replace(".pdf", "")
    name = re.sub(r'^[IVXLCDM\d]+[\.\-]+\s*', '', name).strip()
    name = name.replace("%20", " ").replace("%27", "'").replace("%2C", ",")
    name = re.sub(r'\s+', ' ', name).strip()
    return name if name else filename


def extract_law_name(text: str) -> str:
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines[:30]:
        line = line.strip()
        if not line:
            continue
        if re.match(r'^Page\s+\d+\s+of\s+\d+', line, re.IGNORECASE):
            continue
        if re.match(r'^(ISLAMABAD|KARACHI|LAHORE|RAWALPINDI|PESHAWAR),?\s+\w+,', line):
            continue
        if re.match(r'^THE GAZETTE OF PAKISTAN', line, re.IGNORECASE):
            continue
        if re.match(r'^\d{4}$', line):
            continue
        cleaned_lines.append(line)

    search_text = '\n'.join(cleaned_lines)
    match = re.search(
        r'(THE\s+[A-Z][A-Z\s\(\),\'\-\.]+?'
        r'(?:ACT|ORDINANCE|ORDER|RULES?|REGULATIONS?)'
        r'[\s,]*\d{4})',
        search_text
    )
    if match:
        return re.sub(r'\s+', ' ', match.group(0)).strip()
    for line in cleaned_lines:
        if len(line) > 15:
            return line[:120]
    return "Unknown Act"


def _clean_section_title(title: str) -> str:
    """Nullify any section title that looks like a gazette dateline or notice number."""
    if re.search(
        r'(islamabad|karachi|lahore|rawalpindi|peshawar).{0,3}'
        r'(monday|tuesday|wednesday|thursday|friday|saturday|sunday)',
        title, re.IGNORECASE
    ):
        return ""
    if re.search(r'\bNo\.?\s{0,2}(F\.|Leg)', title, re.IGNORECASE):
        return ""
    return title


# ── Main chunker ──────────────────────────────────────────────────────────────
def chunk_by_section(
    text: str,
    law_name: str,
    source_file: str,
    source_type: str,
    chunk_size: int = 800,
    overlap: int = 100,
) -> list[dict]:

    chunks = []

    section_pattern = re.compile(
        r'(?=(?:^|\n)\s*(?:'
        r'SECTION\s+\d+'
        r'|CHAPTER\s+[IVX\d]+'
        r'|\d+[A-Z]?\.\s+[A-Z]'
        r'|\d+\.\s{2,}'
        r'))',
        re.MULTILINE
    )

    raw_sections = section_pattern.split(text)
    sections = [s.strip() for s in raw_sections if s.strip()]

    def _make_chunk(text_block, sec_num, sec_title, idx):
        quality = ocr_quality_score(text_block)
        return {
            "text":           text_block,
            "law_name":       law_name,
            "section_number": sec_num,
            "section_title":  sec_title,
            "source_file":    source_file,
            "source_type":    source_type,
            "chunk_index":    idx,
            "ocr_quality":    round(quality, 3),
            "low_quality":    quality < OCR_QUALITY_THRESHOLD,
        }

    if len(sections) >= 3:
        for i, sec in enumerate(sections):
            if _is_junk_chunk(sec):
                continue

            first_line = sec.split('\n')[0].strip()
            sec_match  = re.match(
                r'^(?:SECTION\s+)?(\d+[A-Z]?\.?|CHAPTER\s+[IVX\d]+)\s*(.*)',
                first_line, re.IGNORECASE
            )
            if sec_match:
                sec_num   = sec_match.group(1).strip().rstrip('.')
                sec_title = _clean_section_title(sec_match.group(2).strip()[:80])
            else:
                sec_num   = str(i + 1)
                sec_title = _clean_section_title(first_line[:80])

            if len(sec) > chunk_size:
                for j in range(0, len(sec), chunk_size - overlap):
                    chunk_text = sec[j:j + chunk_size].strip()
                    if len(chunk_text) < 60 or _is_junk_chunk(chunk_text):
                        continue
                    chunks.append(_make_chunk(chunk_text, sec_num, sec_title, len(chunks)))
            else:
                chunks.append(_make_chunk(sec, sec_num, sec_title, len(chunks)))
    else:
        for i in range(0, len(text), chunk_size - overlap):
            chunk_text = text[i:i + chunk_size].strip()
            if len(chunk_text) < 60 or _is_junk_chunk(chunk_text):
                continue
            chunks.append(_make_chunk(chunk_text, "N/A", "N/A", len(chunks)))

    return chunks