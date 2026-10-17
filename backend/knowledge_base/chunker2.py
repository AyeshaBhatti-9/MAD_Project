"""
chunker2.py  —  for clr.org.pk PDFs
Handles the diverse document structures found across Pakistani labour law PDFs:
  - Federal/provincial gazette acts (numbered sections)
  - Notification documents (numbered list format)
  - Amendment acts (short, single operative clause)
  - Provincial acts with left-margin labels (Balochistan style)
  - Standard federal acts with CONTENTS tables
"""
import re
from utils.cleaner2 import extract_law_name2


# ── Section detection patterns (ordered by priority) ─────────────────────────

# Matches: "1.", "2.", "3A.", "10.", "SECTION 1", "SECTION 2A"
_NUMBERED_SECTION = re.compile(
    r'^(?:'
    r'(?:SECTION|SEC\.?)\s+\d+[A-Z]?'      # "SECTION 1", "SEC. 2A"
    r'|\d{1,3}[A-Z]?\.\s'                   # "1. ", "10A. "
    r'|\d{1,3}[A-Z]?\.\s*$'                 # "1." alone on line
    r')',
    re.IGNORECASE,
)

# Matches chapter headers: "CHAPTER I", "CHAPTER 1", "CHAPTER ONE"
_CHAPTER = re.compile(
    r'^CHAPTER\s+([IVX\d]+|ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE|TEN)',
    re.IGNORECASE,
)

# Matches schedule/annexure headers
_SCHEDULE = re.compile(
    r'^(SCHEDULE|ANNEXURE|APPENDIX|FORM)\s*[–\-:IVX\d]*',
    re.IGNORECASE,
)

# Split pattern: any of the above at the start of a line
_SPLIT_PATTERN = re.compile(
    r'(?=(?:^|\n)\s*(?:'
    r'(?:SECTION|SEC\.?)\s+\d+[A-Z]?'
    r'|CHAPTER\s+(?:[IVX\d]+|ONE|TWO|THREE|FOUR|FIVE)'
    r'|\d{1,3}[A-Z]?\.\s+\S'               # "1. Something" — needs char after space
    r'|SCHEDULE\s*[–\-:IVX\d]*'
    r'))',
    re.MULTILINE,
)


def _parse_section_header(line: str) -> tuple[str, str]:
    """
    Given the first line of a section, return (section_number, section_title).
    E.g. "1. Short title and commencement." → ("1", "Short title and commencement.")
         "SECTION 12A Powers of Ombudsperson" → ("12A", "Powers of Ombudsperson")
         "CHAPTER IV  Penalties"              → ("IV", "Penalties")
    """
    line = line.strip()

    # CHAPTER first — prevents "CHAPTER" being mis-parsed by numbered patterns
    m = _CHAPTER.match(line)
    if m:
        remainder = line[m.end():].strip()
        return m.group(1), remainder[:100]

    # "SECTION 12A ..." or "SEC. 12A ..."
    m = re.match(r'^(?:SECTION|SEC\.?)\s+(\d+[A-Z]?)\s*(.*)', line, re.IGNORECASE)
    if m:
        return m.group(1), m.group(2).strip()[:100]

    # "12A. Title text" or "12. Title text"
    m = re.match(r'^(\d+[A-Z]?)\.\s+(.*)', line)
    if m:
        return m.group(1), m.group(2).strip()[:100]

    # "12." alone on line
    m = re.match(r'^(\d+[A-Z]?)\.\s*$', line)
    if m:
        return m.group(1), ""

    # "SCHEDULE I", "SCHEDULE –", etc.
    m = re.match(r'^(SCHEDULE\s*[–\-:IVX\d]*)\s*(.*)', line, re.IGNORECASE)
    if m:
        return m.group(1).strip(), m.group(2).strip()[:100]

    return "N/A", line[:100]


def _detect_doc_type(text: str) -> str:
    """
    Heuristic: what kind of document is this?
    Returns: 'act', 'notification', 'amendment', 'rules'
    """
    head = text[:1500].upper()

    # Short amendment acts — very few sections, mostly preamble
    if 'AMENDMENT' in head and len(text) < 3000:
        return 'amendment'

    # Notification format (numbered list, no act structure)
    if re.search(r'NOTIFICATION', head) and not re.search(r'\b(SECTION|CHAPTER)\b', head):
        return 'notification'

    # Rules/Regulations
    if re.search(r'\b(RULES|REGULATIONS)\b', head):
        return 'rules'

    return 'act'


def _has_structural_markers(text: str) -> bool:
    """
    True if the document contains section/chapter markers worth splitting on.
    Avoids running _SPLIT_PATTERN on pure notification / wage-table documents.
    """
    return bool(re.search(
        r'\b(SECTION\s+\d|CHAPTER\s+[IVX\d]|SCHEDULE\s*[IVX\d])\b',
        text[:5000],
        re.IGNORECASE,
    ))


def _make_chunk(text: str, law_name: str, sec_num: str, sec_title: str,
                source_file: str, source_type: str, index: int) -> dict:
    return {
        "text":           text,
        "law_name":       law_name,
        "section_number": sec_num,
        "section_title":  sec_title,
        "source_file":    source_file,
        "source_type":    source_type,
        "chunk_index":    index,
    }


def chunk_by_section2(
    text: str,
    law_name: str,
    source_file: str,
    source_type: str = "clr",
    chunk_size: int = 800,
    overlap: int = 100,
) -> list[dict]:
    """
    Smart chunker for clr.org.pk PDFs.

    Strategy:
    1. Only attempt section splitting if the document actually has structural
       markers (SECTION / CHAPTER / SCHEDULE) — avoids false splits on
       notification or wage-table documents.
    2. If splitting yields >= 3 sections, use section-based chunking.
    3. Otherwise fall back to sliding window (notifications, amendments, etc.).
    4. For each section exceeding chunk_size, sub-chunk with overlap.

    Returns list of chunk dicts compatible with ingest2.py's upsert_chunks().
    """
    chunks: list[dict] = []

    # ── Attempt section-based splitting ──────────────────────────────────────
    if _has_structural_markers(text):
        raw_sections = _SPLIT_PATTERN.split(text)
        sections = [s.strip() for s in raw_sections if s.strip()]
    else:
        sections = []   # skip to fallback immediately

    if len(sections) >= 3:
        # ── Section-based chunking ────────────────────────────────────────────
        for sec in sections:
            lines = sec.split('\n')
            first_line = lines[0].strip() if lines else ""

            sec_num, sec_title = _parse_section_header(first_line)

            # If first line had no marker, try second line
            # (blank line can precede the header after a split)
            if sec_num == "N/A" and len(lines) > 1:
                sec_num, sec_title = _parse_section_header(lines[1].strip())

            if len(sec) > chunk_size:
                # Sub-chunk long sections with overlap
                for j in range(0, len(sec), chunk_size - overlap):
                    chunk_text = sec[j : j + chunk_size].strip()
                    if len(chunk_text) < 60:
                        continue
                    chunks.append(_make_chunk(
                        chunk_text, law_name, sec_num, sec_title,
                        source_file, source_type, len(chunks),
                    ))
            else:
                if len(sec) >= 60:
                    chunks.append(_make_chunk(
                        sec, law_name, sec_num, sec_title,
                        source_file, source_type, len(chunks),
                    ))

    else:
        # ── Fallback: sliding window ──────────────────────────────────────────
        # Used for: notifications (list-based), short amendments, wage tables,
        # and any document where section splitting produced < 3 pieces.
        doc_type = _detect_doc_type(text)

        if doc_type == "notification":
            # Notifications are line/paragraph lists — group by blank-line
            # paragraphs first, then slide if a paragraph is still too long.
            paragraphs = [p.strip() for p in re.split(r'\n{2,}', text) if p.strip()]
            for para in paragraphs:
                if len(para) <= chunk_size:
                    if len(para) >= 60:
                        chunks.append(_make_chunk(
                            para, law_name, "N/A", doc_type,
                            source_file, source_type, len(chunks),
                        ))
                else:
                    for j in range(0, len(para), chunk_size - overlap):
                        chunk_text = para[j : j + chunk_size].strip()
                        if len(chunk_text) < 60:
                            continue
                        chunks.append(_make_chunk(
                            chunk_text, law_name, "N/A", doc_type,
                            source_file, source_type, len(chunks),
                        ))
        else:
            # Pure sliding window for amendments, rules without markers, etc.
            for i in range(0, len(text), chunk_size - overlap):
                chunk_text = text[i : i + chunk_size].strip()
                if len(chunk_text) < 60:
                    continue
                chunks.append(_make_chunk(
                    chunk_text, law_name, "N/A", doc_type,
                    source_file, source_type, len(chunks),
                ))

    return chunks


def law_name_from_clr_filename(filename: str) -> str:
    """
    clr.org.pk filenames are varied — try to extract a clean name.
    Examples:
      'factories-act-1934.txt'
      'payment-of-wages-act-1936.txt'
      'The-Punjab-Industrial-Relations-Act-2010.txt'
      'Bonded%20Labour%20System%20(Abolition)%20Act,%201992.txt'
    """
    name = filename.replace('.txt', '').replace('.pdf', '')
    # URL-decode common encodings
    name = name.replace('%20', ' ').replace('%27', "'").replace('%2C', ',').replace('%28', '(').replace('%29', ')')
    # Replace hyphens/underscores with spaces
    name = name.replace('-', ' ').replace('_', ' ')
    # Title case
    name = name.title()
    # Collapse whitespace
    name = re.sub(r'\s+', ' ', name).strip()
    return name if name else filename