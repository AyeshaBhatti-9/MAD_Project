import re

GAZETTE_ARTIFACTS = [
    "GAZETTE OF PAKISTAN",
    "PRINTED BY",
    "THE GAZETTE",
    "EXTRAORDINARY",
    "REGISTERED NO.",
    "MAJLIS-E-SHOORA",
    "ASSENT OF THE PRESIDENT",
    "HEREBY PUBLISHED FOR GENERAL",
    "NO. F.",
    "NO. LEGIS",
    "ISLAMABAD, THE",
    "LAHORE, THE",
    "KARACHI, THE",
    "RAWALPINDI, THE",
    "PESHAWAR, THE",
]

# Day/month patterns at line start — gazette datelines
_DATELINE = re.compile(
    r'^(ISLAMABAD|KARACHI|LAHORE|RAWALPINDI|PESHAWAR),?\s+'
    r'(MONDAY|TUESDAY|WEDNESDAY|THURSDAY|FRIDAY|SATURDAY|SUNDAY)',
    re.IGNORECASE
)

# "Rs. X" price artifacts
_RS = re.compile(r'\bRs\.?\s*\d')


def clean_gazette_text(text: str) -> str:
    lines = text.split("\n")
    cleaned = []

    for line in lines:
        line = line.strip()

        # Drop short lines
        if len(line.split()) < 5:
            continue

        # Drop gazette artifact lines
        upper = line.upper()
        if any(artifact in upper for artifact in GAZETTE_ARTIFACTS):
            continue

        # Drop dateline patterns
        if _DATELINE.match(line):
            continue

        # Drop Rs. price lines
        if _RS.search(line):
            continue

        # Drop standalone numbers / page numbers
        if re.fullmatch(r'[\d\s\.\-]+', line):
            continue

        cleaned.append(line)

    return "\n".join(cleaned)