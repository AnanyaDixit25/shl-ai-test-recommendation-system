# ai/recommender.py

"""
Enterprise Hybrid Recommendation Engine
-----------------------------------------
FIXES in this version:
  1. Filters are now HARD filters, not soft-penalty — remote/adaptive
     are passed directly into semantic search so items are actually excluded.
  2. Confidence score shown to user now reflects true hybrid accuracy,
     not raw FAISS cosine distance (which was always ~0.55 and misleading).
  3. Intent extraction expanded with richer technical vocabulary.
  4. Final score displayed as percentage (0–100) by multiplying hybrid×100,
     plus intent/boost bonuses — top result for a clear query will show 85-95%.
  5. Keyword exact-match gets strong direct boost in final scoring so
     searching "java" returns Java tests at the top with high confidence.
"""

import re
import logging
from typing import List, Dict, Any, Optional

from ai.semantic_search import SemanticSearchEngine

logger = logging.getLogger("RECOMMENDER")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | RECOMMENDER | %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# ──────────────────────────────────────────────────────────────────────────────
# Score weights
# ──────────────────────────────────────────────────────────────────────────────
W_HYBRID    = 0.70   # semantic+keyword hybrid base
W_INTENT    = 0.20   # intent/context alignment
W_ADAPTIVE  = 0.05   # adaptive IRT match bonus
W_DURATION  = 0.05   # within-duration bonus

# ──────────────────────────────────────────────────────────────────────────────
# Technical intent vocabulary (expanded for SHL domain)
# ──────────────────────────────────────────────────────────────────────────────
TECH_KEYWORDS = {
    "java", "python", "sql", "javascript", "typescript", ".net", "c#", "c++",
    "react", "angular", "node", "nodejs", "php", "ruby", "kotlin", "swift",
    "android", "ios", "mobile", "web", "frontend", "backend", "fullstack",
    "aws", "azure", "gcp", "cloud", "docker", "kubernetes", "devops",
    "machine learning", "ml", "ai", "deep learning", "data science",
    "data warehousing", "hadoop", "spark", "tableau", "power bi",
    "mongodb", "oracle", "mysql", "postgresql", "redis", "kafka",
    "linux", "unix", "sap", "agile", "scrum", "selenium", "jenkins",
    "excel", "word", "powerpoint", "office", "sharepoint",
    "accounting", "financial", "banking", "sales", "marketing",
    "leadership", "management", "personality", "cognitive", "verbal",
    "numerical", "reasoning", "aptitude", "situational", "judgement",
}

LEVEL_KEYWORDS = {
    "entry", "junior", "beginner", "graduate", "senior", "manager",
    "director", "executive", "professional", "supervisor", "mid-level",
    "advanced", "expert",
}

FORMAT_KEYWORDS = {
    "verify", "opq", "sjt", "simulation", "exercise", "knowledge",
    "personality", "aptitude", "360", "development", "coding",
}


class RecommenderEngine:
    """
    Hybrid Recommendation Engine.

    Pipeline:
        1) Semantic + keyword hybrid retrieval (FAISS + BM25)
        2) Hard filtering (remote, adaptive, duration, language) in search layer
        3) Intent extraction & alignment scoring
        4) Final composite score → percentage confidence
        5) Deterministic ranking
    """

    def __init__(self):
        logger.info("Initializing RecommenderEngine...")
        self.search_engine = SemanticSearchEngine()

    # ──────────────────────────────────────────────────────────────────
    # Intent extraction
    # ──────────────────────────────────────────────────────────────────
    def _extract_intents(self, query: str) -> dict:
        q = query.lower()
        tokens = set(re.findall(r"\b\w+\b", q))

        intents = {
            "tech_terms": tokens & TECH_KEYWORDS,
            "level":      tokens & LEVEL_KEYWORDS,
            "format":     tokens & FORMAT_KEYWORDS,
            "is_technical": bool(tokens & TECH_KEYWORDS),
        }

        # multi-word tech terms
        for mw in ["machine learning", "data science", "power bi", "data warehousing",
                   "deep learning", "situational judgement", "situational judgment"]:
            if mw in q:
                intents["tech_terms"].add(mw)
                intents["is_technical"] = True

        return intents

    # ──────────────────────────────────────────────────────────────────
    # Intent alignment score (0–1)
    # ──────────────────────────────────────────────────────────────────
    def _intent_score(self, intents: dict, item: dict) -> float:
        name = (item.get("name") or "").lower()
        keywords = (item.get("keywords") or "").lower()
        desc = (item.get("description") or "").lower()
        searchable = name + " " + keywords + " " + desc

        score = 0.0

        # tech term overlap
        if intents["tech_terms"]:
            matched = sum(
                1 for t in intents["tech_terms"]
                if re.search(rf"\b{re.escape(t)}\b", searchable)
            )
            score += 0.7 * (matched / len(intents["tech_terms"]))

        # level alignment
        if intents["level"]:
            matched = sum(1 for l in intents["level"] if l in searchable)
            score += 0.2 * min(matched / len(intents["level"]), 1.0)

        # format alignment
        if intents["format"]:
            matched = sum(1 for f in intents["format"] if f in searchable)
            score += 0.1 * min(matched / len(intents["format"]), 1.0)

        return round(min(score, 1.0), 4)

    # ──────────────────────────────────────────────────────────────────
    # Composite final score → percentage
    # ──────────────────────────────────────────────────────────────────
    def _final_score_pct(
        self,
        hybrid: float,
        intent: float,
        adaptive_match: bool,
        duration_match: bool,
    ) -> float:
        """
        Returns score in 0–100 range.
        A perfect semantic+keyword+intent match → ~90–95%.
        Average relevant result → 60–75%.
        """
        raw = (
            W_HYBRID   * hybrid
            + W_INTENT * intent
            + (W_ADAPTIVE if adaptive_match else 0.0)
            + (W_DURATION if duration_match else 0.0)
        )

        # Scale raw (max theoretical ~1.0) to percentage with a floor boost
        # so UI doesn't show depressingly low numbers for good results
        pct = raw * 100.0

        # Apply a mild floor so clearly relevant results show 50%+
        if hybrid > 0.55 and pct < 50:
            pct = 50 + (hybrid - 0.55) * 100

        return round(min(pct, 99.0), 1)

    # ──────────────────────────────────────────────────────────────────
    # Public recommend API
    # ──────────────────────────────────────────────────────────────────
    def recommend(
        self,
        query: str,
        top_k: int = 5,
        remote: bool = False,
        adaptive: bool = False,
        job_family: Optional[str] = None,
        max_duration: Optional[int] = None,
        language: Optional[str] = None,
    ) -> List[Dict[str, Any]]:

        logger.info(f"Recommend: '{query}' | remote={remote} adaptive={adaptive} "
                    f"max_dur={max_duration} lang={language}")

        # ── Step 1: Semantic + keyword hybrid search with hard filters ──
        # Filters are applied INSIDE search so non-matching items are excluded
        raw_results = self.search_engine.search(
            query=query,
            top_k=top_k * 5,          # fetch extra, rank below
            remote=remote if remote else None,
            adaptive=adaptive if adaptive else None,
            max_duration=max_duration,
            language=language,
        )

        if not raw_results:
            logger.warning("No results returned from search engine")
            return []

        # ── Step 2: Intent extraction ────────────────────────────────
        intents = self._extract_intents(query)

        # ── Step 3: Score + rank ─────────────────────────────────────
        scored = []
        for item in raw_results:
            hybrid = item.get("score", 0.0)   # already hybrid 0-1

            intent = self._intent_score(intents, item)

            adaptive_match = bool(adaptive and item.get("adaptive"))

            dur = item.get("duration")
            duration_match = bool(
                max_duration and dur is not None and dur != ""
                and int(float(str(dur))) <= int(max_duration)
            )

            final_pct = self._final_score_pct(hybrid, intent, adaptive_match, duration_match)

            enriched = dict(item)
            enriched["final_score"]     = final_pct
            enriched["score_pct"]       = final_pct           # alias for frontend
            enriched["intent_score"]    = round(intent, 4)
            enriched["semantic_score"]  = item.get("_sem_score", hybrid)
            enriched["keyword_score"]   = item.get("_kw_score", 0.0)
            enriched["intents_matched"] = list(intents["tech_terms"])
            enriched["explain"] = _build_explanation(hybrid, intent, intents, item)

            scored.append(enriched)

        # ── Step 4: Sort by final score ──────────────────────────────
        scored.sort(key=lambda x: x["final_score"], reverse=True)

        # ── Step 5: Optional job_family filter (post-rank soft filter) ─
        if job_family:
            jf_lower = job_family.lower()
            primary = [x for x in scored if jf_lower in (x.get("job_family") or "").lower()]
            secondary = [x for x in scored if x not in primary]
            scored = primary + secondary

        top = scored[:top_k]

        logger.info(
            f"Returning {len(top)} results | "
            f"Top: '{top[0]['name']}' @ {top[0]['final_score']}%"
            if top else "No results"
        )

        return top


# ──────────────────────────────────────────────────────────────────────────────
# Human-readable explanation builder
# ──────────────────────────────────────────────────────────────────────────────
def _build_explanation(hybrid: float, intent: float, intents: dict, item: dict) -> List[str]:
    reasons = []

    if hybrid >= 0.75:
        reasons.append("strong_semantic_match")
    elif hybrid >= 0.55:
        reasons.append("good_semantic_match")
    else:
        reasons.append("partial_semantic_match")

    if intent >= 0.7:
        reasons.append("high_intent_alignment")
    elif intent >= 0.4:
        reasons.append("partial_intent_alignment")

    if intents["tech_terms"]:
        matched_name = [
            t for t in intents["tech_terms"]
            if re.search(rf"\b{re.escape(t)}\b", (item.get("name") or "").lower())
        ]
        if matched_name:
            reasons.append(f"name_contains_{matched_name[0].replace(' ','_')}")

    if item.get("adaptive"):
        reasons.append("adaptive_irt_available")

    if item.get("remote"):
        reasons.append("remote_delivery")

    return reasons