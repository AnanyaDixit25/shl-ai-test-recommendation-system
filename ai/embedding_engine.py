# ai/embedding_engine.py

"""
Enterprise Embedding Engine
---------------------------
Centralized vector representation service.

Used by:
- semantic search
- recommendation engine
- ranking
- matching
- explainability
- analytics
"""

from typing import List, Union, Optional
from sentence_transformers import SentenceTransformer
import numpy as np
import logging
import threading
import time

# ================== Logging ================== #

logger = logging.getLogger("EMBEDDING_ENGINE")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | EMBEDDING_ENGINE | %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# ================== Config ================== #

DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_DEVICE = "cpu"
DEFAULT_BATCH_SIZE = 32

# ================== Engine ================== #

class EmbeddingEngine:
    """
    Production-grade embedding service
    """

    _lock = threading.Lock()

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        device: str = DEFAULT_DEVICE,
        batch_size: int = DEFAULT_BATCH_SIZE,
        normalize: bool = True
    ):
        self.model_name = model_name
        self.device = device
        self.batch_size = batch_size
        self.normalize = normalize

        self.model: Optional[SentenceTransformer] = None
        self.vector_dim: Optional[int] = None
        self._initialized = False

        self._load_model()

    # ------------------ Init ------------------ #

    def _load_model(self):
        with self._lock:
            if self._initialized:
                return

            logger.info(f"Loading embedding model: {self.model_name} on {self.device}")

            self.model = SentenceTransformer(self.model_name, device=self.device)

            # warm-up (cold-start fix)
            test_vec = self.model.encode(["warmup"], normalize_embeddings=self.normalize)
            self.vector_dim = int(len(test_vec[0]))

            self._initialized = True

            logger.info(f"Model loaded | Dim={self.vector_dim}")

    # ------------------ Core API ------------------ #

    def encode(self, texts: Union[str, List[str]]) -> np.ndarray:
        """
        Encode text(s) into embeddings.
        Stable API.
        """

        if isinstance(texts, str):
            texts = [texts]

        if not texts:
            raise ValueError("Empty input to embedding engine")

        try:
            embeddings = self.model.encode(
                texts,
                batch_size=self.batch_size,
                normalize_embeddings=self.normalize,
                show_progress_bar=False
            )

            return np.asarray(embeddings, dtype=np.float32)

        except Exception as e:
            logger.error(f"Embedding failed: {e}")
            raise RuntimeError("Embedding engine failure")

    # Backward compatibility
    def embed(self, texts: Union[str, List[str]]) -> np.ndarray:
        """
        Backward-compatible API
        """
        return self.encode(texts)

    # ------------------ Structured Encoding ------------------ #

    def encode_with_metadata(
        self,
        records: List[dict],
        fields: List[str]
    ) -> np.ndarray:
        """
        Encode structured objects into embeddings
        """

        texts = []

        for rec in records:
            parts = []
            for field in fields:
                value = rec.get(field)
                if isinstance(value, list):
                    value = " ".join(map(str, value))
                if value:
                    parts.append(str(value))
            texts.append(" | ".join(parts))

        return self.encode(texts)

    # ------------------ Health ------------------ #

    def health_check(self) -> dict:
        try:
            vec = self.encode("health_check_probe")
            return {
                "status": "healthy",
                "model": self.model_name,
                "device": self.device,
                "vector_dim": self.vector_dim,
                "normalize": self.normalize
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }

# ================== Singleton Factory ================== #

_ENGINE: Optional[EmbeddingEngine] = None

def get_embedding_engine() -> EmbeddingEngine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = EmbeddingEngine()
    return _ENGINE