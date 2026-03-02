import faiss
import json
import numpy as np
import logging
from typing import List, Dict, Any, Optional
from ai.embedding_engine import EmbeddingEngine

# ==============================
# Logging
# ==============================
logger = logging.getLogger("SEMANTIC_SEARCH")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | SEMANTIC_SEARCH | %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

class SemanticSearchEngine:
    """
    Enterprise-grade Semantic Retrieval Engine
    FAISS + Embeddings + Metadata Intelligence Layer
    """

    def __init__(
        self,
        index_path: str = "data/vector/index.faiss",
        meta_path: str = "data/vector/metadata.json",
        normalize: bool = True
    ):

        logger.info("Initializing SemanticSearchEngine...")

        self.embedder = EmbeddingEngine()
        self.normalize = normalize

        # Load FAISS index safely
        try:
            self.index = faiss.read_index(index_path)
            logger.info(f"FAISS index loaded from {index_path}")
        except Exception as e:
            logger.error(f"Failed to load FAISS index: {e}")
            raise RuntimeError("FAISS index load failed")

        # Load metadata safely
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                self.metadata = json.load(f)
            logger.info(f"Metadata loaded from {meta_path}")
        except Exception as e:
            logger.error(f"Failed to load metadata: {e}")
            raise RuntimeError("Metadata load failed")

        self.dim = self.index.d
        logger.info(f"Vector dimension: {self.dim}")

    # ------------------------------
    # Utility
    # ------------------------------
    def _safe_float(self, val, default=0.0):
        try:
            return float(val)
        except:
            return default

    def _normalize(self, vec: np.ndarray):
        if self.normalize:
            faiss.normalize_L2(vec)
        return vec

    # ------------------------------
    # Core Search
    # ------------------------------
    def search(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:

        if not query or not isinstance(query, str):
            logger.warning("Invalid query received")
            return []

        try:
            # Embedding
            query_vec = self.embedder.embed([query])

            if not isinstance(query_vec, np.ndarray):
                query_vec = np.array(query_vec, dtype=np.float32)

            query_vec = query_vec.astype(np.float32)

            # Normalize
            query_vec = self._normalize(query_vec)

            # FAISS search
            scores, indices = self.index.search(query_vec, top_k)

        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []

        results = []

        for raw_score, idx in zip(scores[0], indices[0]):

            if idx == -1:
                continue

            item = self.metadata.get(str(idx))
            if not item:
                continue

            # Hard filters (exact match filters)
            if filters:
                passed = True
                for k, v in filters.items():
                    if v is None:
                        continue
                    if item.get(k) != v:
                        passed = False
                        break
                if not passed:
                    continue

            # Structured output (stable schema)
            result = {
                "score": self._safe_float(raw_score),
                "id": item.get("id"),
                "name": item.get("name"),
                "job_family": item.get("job_family"),
                "job_levels": item.get("job_levels"),
                "test_type": item.get("test_type_labels"),
                "remote": item.get("remote_testing"),
                "adaptive": item.get("adaptive_irt"),
                "duration": item.get("duration_minutes"),
                "languages": item.get("languages"),
                "confidence": self._safe_float(item.get("confidence_score", 0.0)),

                # internal metadata (future use)
                "_vector_id": int(idx),
            }

            results.append(result)

        # Deterministic ordering
        results = sorted(results, key=lambda x: x["score"], reverse=True)

        logger.info(f"Semantic search returned {len(results)} results")

        return results