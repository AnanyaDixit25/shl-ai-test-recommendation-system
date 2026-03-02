# ai/semantic_search.py

"""
Enterprise Semantic Search Engine
-----------------------------------
FIXES in this version:
  1. Boolean type mismatch: remote_testing/adaptive_irt stored as
     strings "True"/"False" in JSON — now correctly cast to bool.
  2. Hybrid scoring: FAISS cosine-sim + BM25-style keyword score
     combined for dramatically better accuracy on short/technical queries.
  3. Score normalization: raw FAISS scores mapped to 0-1 range so the
     UI confidence bar is meaningful (not stuck at 55%).
  4. Keyword boosting: exact query-term overlap in name/keywords
     gets a direct score boost — fixes "java" returning low-confidence results.
"""

import faiss
import json
import re
import math
import numpy as np
import logging
from typing import List, Dict, Any, Optional
from ai.embedding_engine import EmbeddingEngine

logger = logging.getLogger("SEMANTIC_SEARCH")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | SEMANTIC_SEARCH | %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)


class SemanticSearchEngine:
    """
    Hybrid Semantic + Keyword Search Engine.

    Scoring formula:
        final = 0.65 * semantic_score + 0.35 * keyword_score

    Where:
        - semantic_score: normalized FAISS cosine similarity (0–1)
        - keyword_score:  BM25-inspired token overlap (0–1)
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

        try:
            self.index = faiss.read_index(index_path)
            logger.info(f"FAISS index loaded: {index_path} | Vectors: {self.index.ntotal}")
        except Exception as e:
            logger.error(f"Failed to load FAISS index: {e}")
            raise RuntimeError("FAISS index load failed")

        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                self.metadata = json.load(f)
            logger.info(f"Metadata loaded: {meta_path} | Records: {len(self.metadata)}")
        except Exception as e:
            logger.error(f"Failed to load metadata: {e}")
            raise RuntimeError("Metadata load failed")

        self.dim = self.index.d
        logger.info(f"Vector dimension: {self.dim}")

    # ──────────────────────────────────────────────────────────────────
    # Bool coercion — ROOT CAUSE FIX for broken filters
    # JSON stores "True"/"False" strings; Python needs actual bools
    # ──────────────────────────────────────────────────────────────────
    @staticmethod
    def _to_bool(val) -> bool:
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            return val.strip().lower() in ("true", "1", "yes")
        if isinstance(val, (int, float)):
            return bool(val)
        return False

    @staticmethod
    def _safe_float(val, default=0.0) -> float:
        try:
            return float(val)
        except:
            return default

    # ──────────────────────────────────────────────────────────────────
    # BM25-inspired keyword scorer
    # Computes token overlap between query and document text fields
    # ──────────────────────────────────────────────────────────────────
    @staticmethod
    def _keyword_score(query: str, item: dict) -> float:
        """
        Score = matched_query_tokens / total_query_tokens
        Weighted by field importance:
          name (highest) > keywords > description > job_family
        Exact phrase match in name gets a large bonus.
        """
        q_tokens = set(re.findall(r"\b\w+\b", query.lower()))
        if not q_tokens:
            return 0.0

        name = (item.get("name") or "").lower()
        keywords = (item.get("keywords") or "").lower()
        description = (item.get("description") or "").lower()
        job_family = (item.get("job_family") or "").lower()

        # weighted field text
        weighted_text = (
            (name + " ") * 4          # name counts 4x
            + (keywords + " ") * 3    # keywords 3x
            + (description + " ") * 1 # description 1x
            + (job_family + " ") * 2  # job_family 2x
        )
        doc_tokens = set(re.findall(r"\b\w+\b", weighted_text))

        # token overlap ratio
        matched = q_tokens & doc_tokens
        overlap = len(matched) / len(q_tokens)

        # exact phrase bonus
        phrase_bonus = 0.3 if query.lower().strip() in name else 0.0

        # partial-name bonus (query token appears as standalone word in name)
        partial_bonus = 0.0
        for tok in q_tokens:
            if len(tok) >= 3 and re.search(rf"\b{re.escape(tok)}\b", name):
                partial_bonus += 0.15
        partial_bonus = min(partial_bonus, 0.4)

        raw = overlap + phrase_bonus + partial_bonus
        return min(raw, 1.0)

    # ──────────────────────────────────────────────────────────────────
    # Normalize FAISS cosine score from [-1,1] → [0,1]
    # For normalized vectors, FAISS inner product IS cosine similarity
    # ──────────────────────────────────────────────────────────────────
    @staticmethod
    def _normalize_cosine(score: float) -> float:
        # cosine similarity is in [-1, 1]; shift to [0, 1]
        return (score + 1.0) / 2.0

    # ──────────────────────────────────────────────────────────────────
    # Hard filter application with proper type coercion
    # ──────────────────────────────────────────────────────────────────
    def _passes_hard_filters(
        self,
        item: dict,
        remote: Optional[bool],
        adaptive: Optional[bool],
        max_duration: Optional[int],
        language: Optional[str]
    ) -> bool:
        """
        Returns False if item definitively fails a filter the user set.
        None / falsy filters are treated as 'no filter' (pass-through).
        """

        # Remote filter
        if remote:  # only filter if user explicitly wants remote
            item_remote = self._to_bool(item.get("remote_testing"))
            if not item_remote:
                return False

        # Adaptive filter
        if adaptive:
            item_adaptive = self._to_bool(item.get("adaptive_irt"))
            if not item_adaptive:
                return False

        # Max duration filter
        if max_duration is not None and max_duration > 0:
            dur = item.get("duration_minutes")
            if dur is not None and dur != "":
                try:
                    if int(float(str(dur))) > max_duration:
                        return False
                except:
                    pass  # if unparseable, don't penalize

        # Language filter
        if language and language.lower() not in ("any", "all", ""):
            langs = (item.get("languages") or "").lower()
            if language.lower() not in langs:
                return False

        return True

    # ──────────────────────────────────────────────────────────────────
    # Core search
    # ──────────────────────────────────────────────────────────────────
    def search(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        # Direct filter params (used by recommender)
        remote: Optional[bool] = None,
        adaptive: Optional[bool] = None,
        max_duration: Optional[int] = None,
        language: Optional[str] = None,
    ) -> List[Dict[str, Any]]:

        if not query or not isinstance(query, str):
            logger.warning("Invalid query")
            return []

        # ── embed query ──────────────────────────────────────────────
        try:
            query_vec = self.embedder.embed([query])
            if not isinstance(query_vec, np.ndarray):
                query_vec = np.array(query_vec, dtype=np.float32)
            query_vec = query_vec.astype(np.float32)
            if self.normalize:
                faiss.normalize_L2(query_vec)
        except Exception as e:
            logger.error(f"Embedding failed: {e}")
            return []

        # ── FAISS search (fetch extra to allow filtering) ─────────────
        fetch_k = min(top_k * 6, self.index.ntotal)
        try:
            scores, indices = self.index.search(query_vec, fetch_k)
        except Exception as e:
            logger.error(f"FAISS search failed: {e}")
            return []

        # ── Support both filters dict and direct params ───────────────
        if filters:
            remote    = remote    or filters.get("remote")
            adaptive  = adaptive  or filters.get("adaptive")
            max_duration = max_duration or filters.get("max_duration")
            language  = language  or filters.get("language")

        results = []

        for raw_score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue

            item = self.metadata.get(str(idx))
            if not item:
                continue

            # ── hard filter check ────────────────────────────────────
            if not self._passes_hard_filters(
                item, remote, adaptive, max_duration, language
            ):
                continue

            # ── hybrid scoring ───────────────────────────────────────
            sem_score = self._normalize_cosine(self._safe_float(raw_score))
            kw_score  = self._keyword_score(query, item)

            # Weighted hybrid: semantic 65%, keyword 35%
            hybrid = 0.65 * sem_score + 0.35 * kw_score
            hybrid = round(min(max(hybrid, 0.0), 1.0), 4)

            result = {
                "score":       hybrid,          # hybrid 0-1 score
                "_sem_score":  round(sem_score, 4),
                "_kw_score":   round(kw_score, 4),
                "id":          item.get("id"),
                "name":        item.get("name"),
                "job_family":  item.get("job_family"),
                "job_levels":  item.get("job_levels"),
                "test_type":   item.get("test_type_labels"),
                "remote":      self._to_bool(item.get("remote_testing")),
                "adaptive":    self._to_bool(item.get("adaptive_irt")),
                "duration":    item.get("duration_minutes"),
                "languages":   item.get("languages"),
                "url":         item.get("url", ""),
                "keywords":    item.get("keywords", ""),
                "description": item.get("description", ""),
                "confidence":  self._safe_float(item.get("confidence_score", 0.0)),
                "_vector_id":  int(idx),
            }

            results.append(result)

        results.sort(key=lambda x: x["score"], reverse=True)
        results = results[:top_k]

        logger.info(
            f"Query: '{query}' | Found: {len(results)} | "
            f"Top score: {results[0]['score'] if results else 0}"
        )

        return results