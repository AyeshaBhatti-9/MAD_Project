"""
ingest2.py  —  ingests clr.org.pk cleaned text into ChromaDB
Uses a SEPARATE collection ('qanoon_labour_clr') so the original
'qanoon_labour' collection stays intact.
"""
import os
import re
import chromadb
from sentence_transformers import SentenceTransformer
from utils.cleaner2 import extract_law_name2
from Backend.backend.knowledge_base.chunker2 import chunk_by_section2, law_name_from_clr_filename

# ── Config ────────────────────────────────────────────────────────────────────
CLR_TEXT_FOLDER = "../data/cleaned_text_clr"   # post_clean.py output
CHROMA_PATH     = "../data/chroma_db"
COLLECTION_NAME = "qanoon_labour_clr"
EMBED_MODEL     = "BAAI/bge-small-en-v1.5"
BATCH_SIZE      = 64

# ── Init ──────────────────────────────────────────────────────────────────────
print("Loading embedding model...")
model = SentenceTransformer(EMBED_MODEL)

client = chromadb.PersistentClient(path=CHROMA_PATH)

try:
    client.delete_collection(COLLECTION_NAME)
    print(f"Dropped existing collection '{COLLECTION_NAME}'")
except Exception:
    pass

collection = client.create_collection(
    name=COLLECTION_NAME,
    metadata={"hnsw:space": "cosine"},
)
print(f"Created collection '{COLLECTION_NAME}'")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _sanitize_id(filename: str) -> str:
    """
    ChromaDB IDs must not contain special characters.
    Strip URL encoding and anything non-alphanumeric except hyphens/underscores.
    """
    name = filename.replace('%20', '_').replace('%27', '').replace('%2C', '')
    name = re.sub(r'[^\w\-]', '_', name)
    name = re.sub(r'_+', '_', name).strip('_')
    return name[:120]   # keep IDs short


def upsert_chunks(chunks: list[dict]) -> None:
    if not chunks:
        return

    texts     = [c["text"] for c in chunks]
    ids       = [
        f"clr_{_sanitize_id(c['source_file'])}_{c['chunk_index']}"
        for c in chunks
    ]
    metadatas = [{
        "law_name":       c["law_name"],
        "section_number": c["section_number"],
        "section_title":  c["section_title"],
        "source_file":    c["source_file"],
        "source_type":    c["source_type"],
    } for c in chunks]

    embeddings = model.encode(
        texts, batch_size=32, show_progress_bar=False,
        normalize_embeddings=True,          # required for cosine space
    ).tolist()

    for i in range(0, len(chunks), BATCH_SIZE):
        collection.upsert(
            ids        = ids[i : i + BATCH_SIZE],
            documents  = texts[i : i + BATCH_SIZE],
            embeddings = embeddings[i : i + BATCH_SIZE],
            metadatas  = metadatas[i : i + BATCH_SIZE],
        )


# ── Main ingest loop ──────────────────────────────────────────────────────────
print(f"\n=== Ingesting from '{CLR_TEXT_FOLDER}' ===\n")

total_chunks = 0
skipped      = []
processed    = []

for filename in sorted(os.listdir(CLR_TEXT_FOLDER)):
    if not filename.endswith(".txt"):
        continue

    path = os.path.join(CLR_TEXT_FOLDER, filename)
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    # Files from cleaned_text_clr are already post-cleaned — no second clean needed
    if len(text.strip()) < 100:
        print(f"  ⚠️  SKIP (too short): {filename}")
        skipped.append(filename)
        continue

    # Extract law name: text first, then filename fallback
    law_name = extract_law_name2(text, filename)
    if law_name == "Unknown Act":
        law_name = law_name_from_clr_filename(filename)

    # Chunk
    chunks = chunk_by_section2(
        text        = text,
        law_name    = law_name,
        source_file = filename,
        source_type = "clr",
    )

    if not chunks:
        print(f"  ⚠️  SKIP (no chunks): {filename}")
        skipped.append(filename)
        continue

    upsert_chunks(chunks)
    total_chunks += len(chunks)
    processed.append((law_name, filename, len(chunks)))
    print(f"  ✅ {law_name[:55]:<55} → {len(chunks):>3} chunks")


# ── Summary ───────────────────────────────────────────────────────────────────
print(f"\n{'='*60}")
print(f"✅ Collection  : {COLLECTION_NAME}")
print(f"   Total chunks: {total_chunks}")
print(f"   Files OK    : {len(processed)}")
print(f"   Files skipped: {len(skipped)}")
if skipped:
    print("\n  Skipped files:")
    for f in skipped:
        print(f"    → {f}")
print(f"\n   DB path: {CHROMA_PATH}")
print(f"{'='*60}")

print("""
NOTE: To query BOTH collections from main.py:

    col1 = chroma.get_collection('qanoon_labour')
    col2 = chroma.get_collection('qanoon_labour_clr')

    def retrieve(query, n=TOP_K):
        embedding = embedder.encode(
            query, normalize_embeddings=True
        ).tolist()

        def _query(col):
            r = col.query(
                query_embeddings=[embedding],
                n_results=n,
                include=['documents', 'metadatas', 'distances'],
            )
            return list(zip(
                r['documents'][0],
                r['metadatas'][0],
                r['distances'][0],
            ))

        results = _query(col1) + _query(col2)
        results.sort(key=lambda x: x[2])   # ascending distance = best first

        return [
            {
                'text':           doc,
                'law_name':       meta.get('law_name', 'Unknown'),
                'section_number': meta.get('section_number', ''),
                'section_title':  meta.get('section_title', ''),
                'score':          round(1 - dist, 3),
            }
            for doc, meta, dist in results[:n]
        ]
""")