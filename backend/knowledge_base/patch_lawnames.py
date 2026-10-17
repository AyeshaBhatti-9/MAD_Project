"""
patch_law_names.py  —  Fix incorrect law_name metadata in ChromaDB
without re-running ingestion.

Usage:
    python patch_law_names.py            # dry run — shows what would change
    python patch_law_names.py --apply    # actually writes to DB
"""
import argparse
import chromadb

parser = argparse.ArgumentParser()
parser.add_argument("--apply", action="store_true", help="Write changes to DB")
args = parser.parse_args()

CHROMA_PATH     = "../data/chroma_db"
COLLECTION_NAME = "qanoon_labour_clr"

# ── Edit this dict whenever you spot a bad name ──────────────────────────────
# key   = exact source_file value stored in metadata (the .txt filename)
# value = the correct law name you want displayed in citations
FIXES = {
    "Industrial%20Relation%20Act%202012.txt":
        "Industrial Relations Act, 2012",

    "PPC%201860.%202017.txt":
        "Pakistan Penal Code, 1860 (as amended 2017)",

    "The%20Punjab%20Labour%20Code%202026.txt":
        "The Punjab Labour Code, 2026",

    "Khyber%20Pakhtunkhwa%20Bonded%20Labour%20Rules%202021.txt":
        "Khyber Pakhtunkhwa Bonded Labour Rules, 2021",

    "Balochistan-Focrced-and-Bonded-Labour-System-Abolition-Act-2021.txt":
        "The Balochistan Forced and Bonded Labour System (Abolition) Act, 2021",

    "Balochistan-Mines-Amendment-Act-2011.txt":
        "The Balochistan Mines (Amendment) Act, 2011",

    #"Khyber%20Pakhtunkhwa%20Factories%20Amendment%20Act%202.txt":
     #   "Khyber Pakhtunkhwa Factories (Amendment) Act",

#    "Workers%20Children%20Education%20Ordinance%201972.txt":
 #       "Workers Children Education Ordinance, 1972",
    
    # Add more as needed — copy the source_file value exactly from the
    # ingest output or run: python patch_law_names.py --list_bad
}

# ── Connect ───────────────────────────────────────────────────────────────────
client     = chromadb.PersistentClient(path=CHROMA_PATH)
collection = client.get_collection(COLLECTION_NAME)

print(f"Collection '{COLLECTION_NAME}' — {collection.count()} total chunks\n")

total_patched = 0

for source_file, correct_name in FIXES.items():
    # Fetch all chunks that belong to this source file
    results = collection.get(
        where={"source_file": {"$eq": source_file}},
        include=["metadatas"],
    )

    ids       = results["ids"]
    metadatas = results["metadatas"]

    if not ids:
        print(f"  ⚠️  NOT FOUND: {source_file}")
        continue

    old_name = metadatas[0].get("law_name", "?")

    if old_name == correct_name:
        print(f"  ✓  ALREADY OK ({len(ids)} chunks): {correct_name}")
        continue

    print(f"  {'✅ PATCHING' if args.apply else '🔍 WOULD PATCH'} {len(ids):>4} chunks")
    print(f"     OLD: {old_name}")
    print(f"     NEW: {correct_name}")

    if args.apply:
        # Update law_name in every chunk's metadata, keep all other fields intact
        updated_metadatas = [
            {**m, "law_name": correct_name}
            for m in metadatas
        ]
        collection.update(ids=ids, metadatas=updated_metadatas)
        total_patched += len(ids)

print(f"\n{'='*55}")
if args.apply:
    print(f"✅ Done — patched {total_patched} chunks")
else:
    print("Dry run complete. Run with --apply to write changes.")
print(f"{'='*55}")