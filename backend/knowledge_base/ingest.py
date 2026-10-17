import os
import json
import chromadb
from sentence_transformers import SentenceTransformer
from Backend.backend.knowledge_base.chunker import extract_law_name, chunk_by_section, law_name_from_pdf_filename

# ── Config ────────────────────────────────────────────────────────────────────
PDF_TEXT_FOLDER  = "data/extracted_text"
KAGGLE_JSON      = "data/kaggle_unique_labour.json"
CHROMA_PATH      = "data/chroma_db"
COLLECTION_NAME  = "qanoon_labour"
EMBED_MODEL      = "BAAI/bge-small-en-v1.5"
BATCH_SIZE       = 64
SKIP_LOW_QUALITY = True    # set False to include all chunks regardless of OCR score

# ── Init ──────────────────────────────────────────────────────────────────────
print("Loading embedding model...")
model = SentenceTransformer(EMBED_MODEL)

client = chromadb.PersistentClient(path=CHROMA_PATH)
try:
    client.delete_collection(COLLECTION_NAME)
except:
    pass
collection = client.create_collection(
    name=COLLECTION_NAME,
    metadata={"hnsw:space": "cosine"}
)

# ── Helpers ───────────────────────────────────────────────────────────────────
def upsert_chunks(chunks: list[dict]):
    if not chunks:
        return

    # Optionally skip low-quality OCR chunks
    if SKIP_LOW_QUALITY:
        before = len(chunks)
        chunks = [c for c in chunks if not c.get("low_quality", False)]
        dropped = before - len(chunks)
        if dropped:
            print(f"    ⚠️  Dropped {dropped} low-quality OCR chunks")

    if not chunks:
        return

    texts     = [c["text"] for c in chunks]
    ids       = [
        f"{c['source_type']}_{c['source_file']}_{c['chunk_index']}"
        for c in chunks
    ]
    metadatas = [{
        "law_name":       c["law_name"],
        "section_number": c["section_number"],
        "section_title":  c["section_title"],
        "source_file":    c["source_file"],
        "source_type":    c["source_type"],
        "ocr_quality":    c.get("ocr_quality", 1.0),
    } for c in chunks]

    embeddings = model.encode(texts, batch_size=32, show_progress_bar=False).tolist()

    for i in range(0, len(chunks), BATCH_SIZE):
        collection.upsert(
            ids        = ids[i:i+BATCH_SIZE],
            documents  = texts[i:i+BATCH_SIZE],
            embeddings = embeddings[i:i+BATCH_SIZE],
            metadatas  = metadatas[i:i+BATCH_SIZE],
        )


# ── 1. Ingest PDFs ────────────────────────────────────────────────────────────
print("\n=== Ingesting PDFs ===")
pdf_total_chunks = 0

for filename in sorted(os.listdir(PDF_TEXT_FOLDER)):
    if not filename.endswith(".txt"):
        continue
    path = os.path.join(PDF_TEXT_FOLDER, filename)
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    if len(text.strip()) < 100:
        print(f"  ⚠️  SKIP (too short): {filename}")
        continue

    law_name = law_name_from_pdf_filename(filename)
    chunks   = chunk_by_section(
        text=text, law_name=law_name,
        source_file=filename, source_type="pdf",
    )
    upsert_chunks(chunks)
    pdf_total_chunks += len(chunks)
    print(f"  ✅ {law_name[:55]:<55} → {len(chunks):>3} chunks")

print(f"\nPDF total: {pdf_total_chunks} chunks")


# ── 2. Ingest Kaggle ──────────────────────────────────────────────────────────
print("\n=== Ingesting Kaggle ===")
kaggle_total_chunks = 0

with open(KAGGLE_JSON, "r", encoding="utf-8") as f:
    kaggle_data = json.load(f)

seen, deduped = set(), []
for entry in kaggle_data:
    law = extract_law_name(entry.get("text", ""))
    key = law[:60].lower().strip()
    if key not in seen:
        seen.add(key)
        deduped.append(entry)
    else:
        print(f"  🔁 DUPE DROPPED: {entry['file_name'][:50]}")

for entry in deduped:
    text = entry.get("text", "").strip()
    if len(text) < 100:
        continue
    law_name = extract_law_name(text)
    chunks   = chunk_by_section(
        text=text, law_name=law_name,
        source_file=entry["file_name"], source_type="kaggle",
    )
    upsert_chunks(chunks)
    kaggle_total_chunks += len(chunks)
    print(f"  ✅ {law_name[:55]:<55} → {len(chunks):>3} chunks")

print(f"\nKaggle total: {kaggle_total_chunks} chunks")


# ── Final report ──────────────────────────────────────────────────────────────
grand_total = collection.count()
print(f"\n{'='*50}")
print(f"✅ ChromaDB collection '{COLLECTION_NAME}'")
print(f"   Total documents: {grand_total}")
print(f"   PDF chunks:      {pdf_total_chunks}")
print(f"   Kaggle chunks:   {kaggle_total_chunks}")
print(f"   DB path:         {CHROMA_PATH}")