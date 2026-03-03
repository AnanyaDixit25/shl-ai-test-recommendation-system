"""
Run this script to diagnose your setup.
Put it in your project root and run: python check_index.py
"""
import sys

print("=" * 60)
print("SHL SYSTEM DIAGNOSTIC")
print("=" * 60)

# 1. Check FAISS index dimension
try:
    import faiss
    idx = faiss.read_index("data/vector/index.faiss")
    print(f"\n✅ FAISS index loaded: {idx.ntotal} vectors, dim={idx.d}")
    if idx.d == 384:
        print("  ⚠️  INDEX DIMENSION IS 384 (MiniLM)")
        print("  ⚠️  But embedding_engine.py uses MPNet (768-dim)")
        print("  ❌  MISMATCH — rebuild index: python scripts/build_index_pipeline.py")
    elif idx.d == 768:
        print("  ✅ Dimension 768 (MPNet) — correct")
    else:
        print(f"  ❓ Unusual dimension: {idx.d}")
except Exception as e:
    print(f"\n❌ Cannot load FAISS index: {e}")

# 2. Check embedding engine
try:
    from ai.embedding_engine import EmbeddingEngine
    eng = EmbeddingEngine()
    vec = eng.encode(["test query"])
    print(f"\n✅ EmbeddingEngine loaded: model={eng.model_name}, dim={eng.vector_dim}")
    print(f"   Test encode shape: {vec.shape}")
    
    # Check for dimension match
    try:
        idx_dim = faiss.read_index("data/vector/index.faiss").d
        if idx_dim != eng.vector_dim:
            print(f"\n❌ CRITICAL MISMATCH: index={idx_dim}d, encoder={eng.vector_dim}d")
            print("   FIX: python scripts/build_index_pipeline.py  (rebuilds index with correct dim)")
        else:
            print(f"\n✅ Dimensions match: {idx_dim}d")
    except:
        pass
except Exception as e:
    print(f"\n❌ EmbeddingEngine error: {e}")

# 3. Quick API test
try:
    import requests
    r = requests.get("http://localhost:8000/health", timeout=3)
    data = r.json()
    print(f"\n✅ API healthy: {data}")
except Exception as e:
    print(f"\n❌ API not reachable: {e}")
    print("   FIX: uvicorn fastapi_api_layer:app --port 8000 --reload")

# 4. Quick recommendation test
try:
    import requests, json
    r = requests.post("http://localhost:8000/recommend",
                      json={"query": "content writer english SEO", "top_k": 5, "use_llm": False},
                      timeout=10)
    data = r.json()
    items = data.get("recommended_assessments", [])
    print(f"\n✅ Test query returned {len(items)} results:")
    for i, item in enumerate(items[:5]):
        print(f"   {i+1}. {item.get('name','?')} | score={item.get('final_score','?')}")
    if not items:
        print("   ❌ ZERO RESULTS — likely index dimension mismatch or API using wrong endpoint")
        print("   Check: does API return 'recommended_assessments' key?")
        print(f"   Raw response: {json.dumps(data)[:200]}")
except Exception as e:
    print(f"\n❌ Test query failed: {e}")

print("\n" + "=" * 60)
print("If index dimension mismatch found, run:")
print("  python scripts/build_index_pipeline.py")
print("Then restart API:")
print("  uvicorn fastapi_api_layer:app --port 8000 --reload")
print("=" * 60)