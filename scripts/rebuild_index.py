"""
scripts/rebuild_index.py  — place in your shl/scripts/ folder
Run: python scripts/rebuild_index.py  (from shl root)
"""
import os, sys, json, time
import numpy as np
import faiss

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT       = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, ROOT)

INPUT_JSON = os.path.join(ROOT, "data", "processed", "processed_catalogue.json")
OUT_DIR    = os.path.join(ROOT, "data", "vector")
INDEX_PATH = os.path.join(OUT_DIR, "index.faiss")
META_PATH  = os.path.join(OUT_DIR, "metadata.json")
os.makedirs(OUT_DIR, exist_ok=True)

def build_embed_text(item):
    name  = item.get("name", "")
    tt    = item.get("test_type_labels", "")
    jf    = item.get("job_family", "")
    kw    = item.get("keywords", "")
    desc  = item.get("description", "")
    lvl   = item.get("job_levels", "")
    return f"{name}. {name}. {name}. {tt}. {jf}. {lvl}. {kw}. {desc}"

def to_bool(val):
    if isinstance(val, bool): return val
    if isinstance(val, str):  return val.strip().lower() in ("true","1","yes")
    return bool(val)

def build_index():
    print(f"Loading: {INPUT_JSON}")
    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        catalogue = json.load(f)
    print(f"Records: {len(catalogue)}")

    from ai.embedding_engine import EmbeddingEngine
    embedder = EmbeddingEngine()
    print(f"Model: {embedder.model_name} | Dim: {embedder.vector_dim}")

    texts = [build_embed_text(item) for item in catalogue]
    print(f"Embedding {len(texts)} documents...")
    t0 = time.time()

    BATCH, all_vecs = 64, []
    for i in range(0, len(texts), BATCH):
        vecs = embedder.encode(texts[i:i+BATCH])
        all_vecs.append(vecs)
        done = min(i+BATCH, len(texts))
        print(f"  {int(done/len(texts)*100)}%  ({done}/{len(texts)})", end="\r")

    embeddings = np.vstack(all_vecs).astype(np.float32)
    print(f"\nDone in {time.time()-t0:.1f}s | Shape: {embeddings.shape}")

    faiss.normalize_L2(embeddings)
    dim   = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)
    faiss.write_index(index, INDEX_PATH)
    print(f"[OK] index -> {INDEX_PATH}")

    metadata = {}
    for i, item in enumerate(catalogue):
        m = dict(item)
        m["remote_testing"] = to_bool(item.get("remote_testing", False))
        m["adaptive_irt"]   = to_bool(item.get("adaptive_irt", False))
        dur = item.get("duration_minutes", "")
        try:    m["duration_minutes"] = int(float(str(dur))) if str(dur).strip() else None
        except: m["duration_minutes"] = None
        metadata[str(i)] = m

    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    print(f"[OK] metadata -> {META_PATH}")

    print(f"\n-- Sanity checks --")
    for q in ["java", "python", "verbal reasoning", "leadership", "data science"]:
        qv = embedder.encode([q]).astype(np.float32)
        faiss.normalize_L2(qv)
        sc, ix = index.search(qv, 1)
        print(f"  '{q}' -> {catalogue[ix[0][0]]['name']}  ({sc[0][0]:.4f})")

    print("\n[DONE] Restart FastAPI: uvicorn fastapi_api_layer:app --reload --port 8000")

if __name__ == "__main__":
    build_index()
