"""
post_clean.py  —  Post-extraction cleaner for clr.org.pk text files
=====================================================================
Run AFTER pdf_extraction2.py, BEFORE ingest2.py.

The extraction script already applied clean_gazette_text2().
This script catches what that pass misses:
  • OCR hyphenated line-breaks          ("provi-\\nsion" → "provision")
  • Running page headers / footers      (lines repeating 3+ times)
  • Consecutive duplicate lines         (page-boundary repeats)
  • Unicode ligatures & smart quotes    (ﬁ → fi, " " → " ")
  • Symbol / garbage lines              (high non-alphanumeric ratio)
  • Urdu / Arabic script lines          (non-Latin script fragments)
  • Table leader lines                  ("......   42", "- - - -")
  • Residual gazette boilerplate        (anything clean_gazette_text2 missed)
  • Tabs and multi-space runs

Reads  : data/extracted_text_clr/*.txt   (originals untouched)
Writes : data/cleaned_text_clr/*.txt     (new folder)

Usage:
    python post_clean.py                          # default folders
    python post_clean.py --in_dir my/input --out_dir my/output
    python post_clean.py --overwrite              # write back to same folder
    python post_clean.py --dry_run                # report stats, write nothing
"""

import os
import re
import unicodedata
import argparse
from collections import Counter

# ── CLI args ──────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--in_dir",   default="data/extracted_text_clr")
parser.add_argument("--out_dir",  default="data/cleaned_text_clr")
parser.add_argument("--overwrite", action="store_true",
                    help="Write cleaned files back to --in_dir instead of --out_dir")
parser.add_argument("--dry_run",  action="store_true",
                    help="Report stats only — do not write any files")
parser.add_argument("--min_chars", type=int, default=100,
                    help="Skip output files shorter than this after cleaning")
args = parser.parse_args()

IN_DIR  = args.in_dir
OUT_DIR = args.in_dir if args.overwrite else args.out_dir

if not args.dry_run and not args.overwrite:
    os.makedirs(OUT_DIR, exist_ok=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  PASS 1  —  Document-level transforms  (whole text at once)
# ═══════════════════════════════════════════════════════════════════════════════

# Unicode ligature map
_LIGATURES = str.maketrans({
    '\ufb01': 'fi',   # ﬁ
    '\ufb02': 'fl',   # ﬂ
    '\ufb03': 'ffi',  # ﬃ
    '\ufb04': 'ffl',  # ﬄ
    '\u2019': "'",    # right single quote
    '\u2018': "'",    # left single quote
    '\u201c': '"',    # left double quote
    '\u201d': '"',    # right double quote
    '\u2013': '-',    # en-dash
    '\u2014': '-',    # em-dash
    '\u00a0': ' ',    # non-breaking space
    '\u00ad': '',     # soft hyphen
    '\t':     ' ',    # tab → space
})

# Residual gazette boilerplate patterns not caught by clean_gazette_text2
_DOC_NOISE = re.compile(
    r'GAZETTE\s+OF\s+PAKISTAN'
    r'|PRINTED\s+BY\s+THE\s+MANAGER'
    r'|PUBLISHED\s+BY\s+AUTHORITY'
    r'|EXTRA\s*ORDINARY'
    r'|Price\s*:\s*Rs\.?\s*[\d\.]+'
    r'|\[[\d\w/\-]+\]'                   # [7056(2022)/Ex.Gaz.]
    r'|Registered\s+No\.\s+[A-Z0-9\-/]+'
    r'|Acts,\s+Ordinances,\s+President',
    re.IGNORECASE,
)

def _doc_level(text: str) -> str:
    """Whole-document transforms: ligatures, unicode, residual boilerplate."""
    # Normalize unicode (NFC) then apply ligature map
    text = unicodedata.normalize('NFC', text)
    text = text.translate(_LIGATURES)

    # Residual gazette noise (inline spans)
    text = _DOC_NOISE.sub('', text)

    # Rejoin OCR hyphenated line-breaks: "provi-\nsion" → "provision"
    # Only when the hyphen is at end of line and next line starts lowercase
    text = re.sub(r'-\n([a-z])', r'\1', text)

    # Collapse runs of 3+ newlines to 2
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text


# ═══════════════════════════════════════════════════════════════════════════════
#  PASS 2  —  Detect running headers / footers  (appear 3+ times verbatim)
# ═══════════════════════════════════════════════════════════════════════════════

def _find_repeating_lines(lines: list[str], threshold: int = 3) -> set[str]:
    """
    Return the set of non-trivial lines that appear >= threshold times.
    These are almost always running page headers or footers.
    """
    counts = Counter(l for l in lines if len(l) > 8)
    return {line for line, cnt in counts.items() if cnt >= threshold}


# ═══════════════════════════════════════════════════════════════════════════════
#  PASS 3  —  Line-level filters
# ═══════════════════════════════════════════════════════════════════════════════

# Urdu / Arabic Unicode ranges (rough but effective)
_URDU_ARABIC = re.compile(
    r'[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]'
)

# Table leader lines: "......  42", "- - - - -", "_ _ _ _", "· · · ·"
_TABLE_LEADER = re.compile(r'^[\s\.\-\_·•]{4,}\s*\d*\s*$')

# Residual gazette / metadata lines (line-level, beyond cleaner2)
_LINE_NOISE = re.compile(
    r'^(ISLAMABAD|KARACHI|LAHORE|RAWALPINDI|PESHAWAR|QUETTA)'
    r'[,\s]',
    re.IGNORECASE,
)
_ASSEMBLY_NOISE = re.compile(
    r'^(BY ORDER OF THE|PROVINCIAL ASSEMBLY|NATIONAL ASSEMBLY|SENATE SECRETARIAT'
    r'|No\.\s*[A-Z][\w/\.\-]+\s+dated)',
    re.IGNORECASE,
)

# Section-number-like patterns — protect these from the short-line filter
_SECTION_NUM = re.compile(r'^\d{1,3}[A-Z]?\.?$')

# A line is "garbage" if >50% of chars are non-alphanumeric and non-space
def _is_garbage(line: str) -> bool:
    if not line:
        return False
    alpha_num = sum(1 for c in line if c.isalnum() or c.isspace())
    return (alpha_num / len(line)) < 0.50

# A line is "urdu-dominant" if >30% of chars are Urdu/Arabic script
def _is_urdu_dominant(line: str) -> bool:
    urdu_chars = len(_URDU_ARABIC.findall(line))
    return len(line) > 0 and (urdu_chars / len(line)) > 0.30


def _filter_line(
    line: str,
    repeating: set[str],
    prev_line: str,
) -> bool:
    """
    Return True if this line should be DROPPED.
    """
    stripped = line.strip()

    # Blank lines are handled separately
    if not stripped:
        return False

    # Running header / footer
    if stripped in repeating:
        return True

    # Consecutive duplicate of previous non-blank line
    if stripped == prev_line:
        return True

    # City + date header lines
    if _LINE_NOISE.match(stripped):
        return True

    # Assembly boilerplate
    if _ASSEMBLY_NOISE.match(stripped):
        return True

    # Table leaders (dots, dashes, underscores)
    if _TABLE_LEADER.match(stripped):
        return True

    # Urdu / Arabic dominant lines
    if _is_urdu_dominant(stripped):
        return True

    # Garbage / symbol-heavy lines
    if _is_garbage(stripped):
        return True

    # Very short lines that aren't section numbers
    if len(stripped) < 4 and not _SECTION_NUM.match(stripped):
        return True

    # Lone page number (digit-only, 1–4 chars)
    if re.fullmatch(r'\d{1,4}', stripped):
        return True

    return False


# ═══════════════════════════════════════════════════════════════════════════════
#  PASS 4  —  Post-line normalisation
# ═══════════════════════════════════════════════════════════════════════════════

def _post_normalise(text: str) -> str:
    """Collapse multi-space runs, strip trailing whitespace per line."""
    lines = [re.sub(r' {2,}', ' ', l).rstrip() for l in text.split('\n')]
    text = '\n'.join(lines)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


# ═══════════════════════════════════════════════════════════════════════════════
#  MASTER CLEANER
# ═══════════════════════════════════════════════════════════════════════════════

def post_clean(text: str) -> tuple[str, dict]:
    """
    Full post-extraction cleaning pipeline.
    Returns (cleaned_text, stats_dict).
    """
    original_lines = len(text.split('\n'))
    original_chars = len(text)

    # Pass 1 — document level
    text = _doc_level(text)

    # Pass 2 — find repeating headers/footers
    lines = text.split('\n')
    repeating = _find_repeating_lines(lines, threshold=3)

    # Pass 3 — line-level filter
    cleaned   = []
    prev_blank = False
    prev_line  = ""

    for line in lines:
        stripped = line.strip()

        if not stripped:
            if not prev_blank:
                cleaned.append('')
            prev_blank = True
            continue

        prev_blank = False

        if _filter_line(stripped, repeating, prev_line):
            continue

        cleaned.append(stripped)
        prev_line = stripped

    text = '\n'.join(cleaned)

    # Pass 4 — post normalise
    text = _post_normalise(text)

    stats = {
        "original_lines": original_lines,
        "original_chars": original_chars,
        "cleaned_lines":  len(text.split('\n')),
        "cleaned_chars":  len(text),
        "repeating_hdrs": len(repeating),
        "lines_dropped":  original_lines - len(text.split('\n')),
    }

    return text, stats


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN LOOP
# ═══════════════════════════════════════════════════════════════════════════════

print(f"Post-cleaner starting")
print(f"  Input  : {IN_DIR}")
print(f"  Output : {'(dry run)' if args.dry_run else OUT_DIR}")
print()

total_files   = 0
skipped       = []
processed     = []

txt_files = sorted(f for f in os.listdir(IN_DIR) if f.endswith('.txt'))

for filename in txt_files:
    in_path = os.path.join(IN_DIR, filename)

    with open(in_path, 'r', encoding='utf-8') as f:
        raw = f.read()

    if len(raw.strip()) < args.min_chars:
        print(f"  ⚠️  SKIP (too short before clean): {filename}")
        skipped.append(filename)
        continue

    cleaned, stats = post_clean(raw)

    if len(cleaned.strip()) < args.min_chars:
        print(f"  ⚠️  SKIP (too short after clean): {filename}")
        skipped.append(filename)
        continue

    reduction_pct = round(100 * (1 - stats['cleaned_chars'] / stats['original_chars']), 1)

    if args.dry_run:
        print(
            f"  [dry] {filename[:55]:<55} "
            f"{stats['original_chars']:>6} → {stats['cleaned_chars']:>6} chars "
            f"({reduction_pct:>5}% removed) "
            f"| hdrs={stats['repeating_hdrs']} dropped={stats['lines_dropped']}"
        )
    else:
        out_path = os.path.join(OUT_DIR, filename)
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(cleaned)

        print(
            f"  ✅ {filename[:55]:<55} "
            f"{stats['original_chars']:>6} → {stats['cleaned_chars']:>6} chars "
            f"({reduction_pct:>5}% removed)"
        )

    processed.append(filename)
    total_files += 1


# ── Summary ───────────────────────────────────────────────────────────────────
print(f"\n{'='*65}")
print(f"  Files processed : {len(processed)}")
print(f"  Files skipped   : {len(skipped)}")
if not args.dry_run:
    print(f"  Output folder   : {OUT_DIR}")
if skipped:
    print(f"\n  Skipped files:")
    for f in skipped:
        print(f"    → {f}")
print(f"{'='*65}")