import json
import logging
from pathlib import Path
from typing import List, Dict, Any

import faiss
import numpy as np

from ai.embedding_engine import get_embedding_engine

# ==============================
# Logging
# ==============================
logger = logging.getLogger("VECTOR_INDEX")
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | VECTOR_INDEX | %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# ==============================
# Paths (robust + auto-create)
# ==============================
BASE_DIR = Path("data")
PROCESSED_PATH = BASE_DIR / "processed" / "processed_catalogue.json"

VECTOR_DIR = BASE_DIR / "vector"
INDEX_PATH = VECTOR_DIR / "index.faiss"
META_PATH = VECTOR_DIR / "metadata.json"

VECTOR_DIR.mkdir(parents=True, exist_ok=True)

# ==============================
# Vector Index Engine
# ==============================
class VectorIndex:
    def __init__(self, dim: int = 384):
        self.dim = dim
        self.index: faiss.Index = None
        self.metadata: Dict[int, Dict[str, Any]] = {}
        self.embedding_engine = get_embedding_engine()

    # --------------------------
    # Text Builder
    # --------------------------
    def _build_text(self, item: Dict[str, Any]) -> str:
        """
    Builds rich semantic representation for embeddings.
    This is DATA INTELLIGENCE, not hardcoded rules.
    """

        def safe_join(val):
            if isinstance(val, list):
                return " ".join([str(v) for v in val])
            if isinstance(val, str):
                return val
            return ""

        name = item.get("name", "")
        desc = item.get("description", "")
        keywords = safe_join(item.get("keywords", []))

        job_family = item.get("job_family", "")
        job_levels = safe_join(item.get("job_levels", []))
        test_types = safe_join(item.get("test_type_labels", []))
        test_type = item.get("type", "")
        languages = safe_join(item.get("languages", []))

    # ---------- Semantic roles ----------
        role_context = []
        lname = name.lower()
        ldesc = desc.lower()

        text_blob = f"{lname} {ldesc}"

    # Domain inference (generic)
        if any(k in text_blob for k in ["data", "analytics", "statistics", "ml", "ai", "science"]):
            role_context.append("data science analytics machine learning artificial intelligence")

        if any(k in text_blob for k in ["web", "api", "service", "server", "backend", "frontend"]):
            role_context.append("web application development services api systems")

        if any(k in text_blob for k in ["cloud", "aws", "azure", "gcp", "devops"]):
            role_context.append("cloud computing devops infrastructure")

        if any(k in text_blob for k in ["security", "cyber", "network", "firewall"]):
            role_context.append("cybersecurity networking information security")

        if any(k in text_blob for k in ["database", "sql", "warehouse", "etl", "pipeline"]):
            role_context.append("databases data engineering pipelines")

        if any(k in text_blob for k in ["desktop", "gui", "ui", "client"]):
            role_context.append("desktop applications user interface software")

        if any(k in text_blob for k in ["enterprise", "erp", "corporate", "business system"]):
            role_context.append("enterprise systems corporate applications")

        if any(k in text_blob for k in ["finance", "account", "bank", "risk", "audit"]):
            role_context.append("finance systems accounting business finance")

        if any(k in text_blob for k in ["hr", "recruit", "talent", "people"]):
            role_context.append("human resources recruitment talent management")

        if any(k in text_blob for k in ["beginner", "basic", "intro", "fundamental"]):
            role_context.append("beginner level entry level fundamentals")

        if any(k in text_blob for k in ["advanced", "expert", "professional"]):
            role_context.append("advanced professional expert level")

        semantic_context = " ".join(role_context)

    # ---------- Structured semantic document ----------
        return " | ".join([
            f"Title: {name}",
            f"Description: {desc}",
            f"Keywords: {keywords}",
            f"Domain: {job_family}",
            f"Levels: {job_levels}",
            f"Assessment Type: {test_types}",
            f"Category: {test_type}",
            f"Languages: {languages}",
            f"Semantic Context: {semantic_context}"
        ])
    # --------------------------
    # Build Index
    # --------------------------
    def build(self):
        logger.info("Loading processed catalogue...")

        if not PROCESSED_PATH.exists():
            raise FileNotFoundError(f"Processed catalogue not found: {PROCESSED_PATH}")

        with open(PROCESSED_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        texts: List[str] = []
        meta: Dict[int, Dict[str, Any]] = {}

        for i, item in enumerate(data):
            text = self._build_text(item)
            if not text.strip():
                continue
            texts.append(text)
            meta[len(texts) - 1] = item  # index-safe mapping

        logger.info(f"Total documents: {len(texts)}")

        if len(texts) == 0:
            raise RuntimeError("No valid documents found to index.")

        # --------------------------
        # Embeddings
        # --------------------------
        logger.info("Generating embeddings...")
        vectors = self.embedding_engine.encode(texts)

        if not isinstance(vectors, np.ndarray):
            vectors = np.array(vectors)

        if vectors.ndim != 2:
            raise RuntimeError("Embedding output has invalid shape")

        # --------------------------
        # Normalize
        # --------------------------
        logger.info("Normalizing vectors...")
        faiss.normalize_L2(vectors)

        # --------------------------
        # Build Index
        # --------------------------
        logger.info("Building FAISS IndexFlatIP...")
        index = faiss.IndexFlatIP(self.dim)
        index.add(vectors)

        # --------------------------
        # Persist
        # --------------------------
        logger.info("Saving index and metadata...")

        faiss.write_index(index, str(INDEX_PATH))

        with open(META_PATH, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)

        self.index = index
        self.metadata = meta

        logger.info("Vector index build complete ✅")
        logger.info(f"Index saved at: {INDEX_PATH}")
        logger.info(f"Metadata saved at: {META_PATH}")

    # --------------------------
    # Load Index
    # --------------------------
    def load(self):
        logger.info("Loading vector index from disk...")

        if not INDEX_PATH.exists():
            raise FileNotFoundError(f"FAISS index not found: {INDEX_PATH}")

        if not META_PATH.exists():
            raise FileNotFoundError(f"Metadata not found: {META_PATH}")

        self.index = faiss.read_index(str(INDEX_PATH))

        with open(META_PATH, "r", encoding="utf-8") as f:
            self.metadata = json.load(f)

        # keys back to int
        self.metadata = {int(k): v for k, v in self.metadata.items()}

        logger.info("Vector index loaded successfully ✅")

    # --------------------------
    # Search
    # --------------------------
    def search(self, query: str, top_k: int = 5):
        if self.index is None:
            self.load()

        logger.info(f"Searching for: {query}")

        q_vec = self.embedding_engine.encode([query])

        if not isinstance(q_vec, np.ndarray):
            q_vec = np.array(q_vec)

        faiss.normalize_L2(q_vec)

        scores, indices = self.index.search(q_vec, top_k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            item = self.metadata.get(int(idx))
            if item:
                results.append({
                    "score": float(score),
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "type": item.get("type"),
                    "job_family": item.get("job_family"),
                    "url": item.get("url"),
                    "description": item.get("description")
                })

        return results