import json
import re

with open("pdf_data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Acts already covered by your 33 PDFs — skip these
PDF_DUPLICATES = [
    "bonded labour system",
    "minimum wages ordinance",
    "road transport workers",
    "minimum wages for unskilled workers",
    "maternity and paternity leave",
    "companies profits",
    "west pakistan maternity benefit",
    "workers welfare fund",
    "coal mines",
    "fee-charging employment agencies",
    "dock workers",
    "employees cost of living",
    "control of employment",
    "islamabad capital territory domestic workers",
    "employees old-age benefits",
    "sacked employees",
]

# Acts unique to Kaggle — these are the ones you want
KAGGLE_UNIQUE_ACTS = [
    "trade dispute resolution",
    "industrial relations ordinance, 2002",
    "industrial relations act, 2008",
    "industrial relations act, 2012",
    "newspaper employees",
    "west pakistan shops and establishments",
    "excise duty on minerals",
    "pakistan essential services",
    "payment of wages",
    "apprenticeship act, 2018",
    "provincial employees social security",
    "employment of children",
    "employers liability",
    "workmen's compensation",
    "employees social insurance",
    "employment (record of services)",
    "mines act",
    "factories act",
    "dock labourers",
    "tea plantations labour",
    # Borderline — include these too
    "transgender persons",
    "rights of persons with disability",
]

def normalize(text):
    return text.lower().replace("'", "").replace("'", "").replace("-", " ")

def is_duplicate(entry):
    text = normalize((entry.get("text") or "")[:800])
    for act in PDF_DUPLICATES:
        if normalize(act) in text:
            return True
    return False

def is_target(entry):
    text = normalize((entry.get("text") or "")[:800])
    for act in KAGGLE_UNIQUE_ACTS:
        if normalize(act) in text:
            return True
    return False

kept = []
skipped_duplicates = []
skipped_irrelevant = []

for entry in data:
    if is_duplicate(entry):
        skipped_duplicates.append(entry)
    elif is_target(entry):
        kept.append(entry)
    else:
        skipped_irrelevant.append(entry)

print(f"✅ Keeping:              {len(kept)}")
print(f"🔴 Skipped (duplicates): {len(skipped_duplicates)}")
print(f"⚪ Skipped (irrelevant): {len(skipped_irrelevant)}")
print(f"\nKept entries:")
for e in kept:
    print(f"  → {e['file_name']}")

# Save to a clean file for your pipeline
with open("kaggle_unique_labour.json", "w", encoding="utf-8") as f:
    json.dump(kept, f, ensure_ascii=False, indent=2)

print(f"\n💾 Saved to kaggle_unique_labour.json")