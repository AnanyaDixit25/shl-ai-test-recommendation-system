import logging
from typing import List, Dict, Any, Optional

from ai.semantic_search import SemanticSearchEngine

# ==============================
# Logging
# ==============================
logger = logging.getLogger("RECOMMENDER")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | RECOMMENDER | %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# ==============================
# Scoring Weights (Configurable)
# ==============================
SCORING_WEIGHTS = {
    "semantic": 1.0,
    "remote": 0.10,
    "adaptive": 0.08,
    "job_family": 0.07,
    "duration": 0.05,
    "language": 0.05,
    "confidence": 0.05,
    "intent": 0.25   # 🔥 intelligence layer
}


class RecommenderEngine:
    """
    Enterprise-grade Hybrid Intelligence Recommendation Engine

    Layers:
    1) Semantic Retrieval (FAISS)
    2) Soft Filtering
    3) Business Logic Boosting
    4) Intent Intelligence
    5) Explainable Scoring
    6) Deterministic Ranking
    """

    def __init__(self):
        logger.info("Initializing RecommenderEngine...")
        self.search_engine = SemanticSearchEngine()

    # ------------------------------
    # Utils
    # ------------------------------
    def _safe_float(self, val, default=0.0):
        try:
            return float(val)
        except:
            return default

    def _normalize_score(self, score: float) -> float:
        """Keeps score in stable range"""
        return round(min(max(score, 0.0), 2.0), 4)

    # ------------------------------
    # Intent Intelligence (Domain-Agnostic)
    # ------------------------------
    def _extract_intents(self, query: str) -> dict:
        q = query.lower()

        intents = {
            "level": None,
            "app_type": None,
            "scope": None,
            "function": None,
            "format": None,
        }

        # --- level ---
        if any(k in q for k in ["basic", "beginner", "fundamental", "intro"]):
            intents["level"] = "basic"
        elif any(k in q for k in ["advanced", "expert", "professional"]):
            intents["level"] = "advanced"

        # --- app type ---
        if any(k in q for k in ["web", "website", "http"]):
            intents["app_type"] = "web"
        elif any(k in q for k in ["mobile", "android", "ios"]):
            intents["app_type"] = "mobile"
        elif any(k in q for k in ["desktop", "gui"]):
            intents["app_type"] = "desktop"

        # --- scope ---
        if "enterprise" in q:
            intents["scope"] = "enterprise"
        elif "startup" in q:
            intents["scope"] = "startup"

        # --- function ---
        if "backend" in q or "api" in q:
            intents["function"] = "backend"
        elif "frontend" in q:
            intents["function"] = "frontend"
        elif "fullstack" in q:
            intents["function"] = "fullstack"

        # --- format ---
        if any(k in q for k in ["framework", "library"]):
            intents["format"] = "framework"
        elif any(k in q for k in ["service", "api"]):
            intents["format"] = "service"

        return intents

    def _generic_intent_boost(self, intents: dict, item: dict) -> float:
        name = (item.get("name") or "").lower()
        tags = " ".join(item.get("test_type", [])).lower() if item.get("test_type") else ""
        text = name + " " + tags

        boost = 0.0

        if intents["level"] and intents["level"] in text:
            boost += 0.20
        if intents["app_type"] and intents["app_type"] in text:
            boost += 0.25
        if intents["scope"] and intents["scope"] in text:
            boost += 0.25
        if intents["function"] and intents["function"] in text:
            boost += 0.25
        if intents["format"] and intents["format"] in text:
            boost += 0.20

        return boost

    # ------------------------------
    # Soft Filtering (non-destructive)
    # ------------------------------
    def _apply_soft_filters(
        self,
        items: List[Dict[str, Any]],
        filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:

        results = []

        for item in items:
            penalty = 0.0

            if filters.get("remote") and not item.get("remote"):
                penalty += 0.05

            if filters.get("adaptive") and not item.get("adaptive"):
                penalty += 0.05

            if filters.get("job_family"):
                jf = item.get("job_family", "")
                if filters["job_family"].lower() not in jf.lower():
                    penalty += 0.04

            if filters.get("max_duration") and item.get("duration"):
                if item["duration"] > filters["max_duration"]:
                    penalty += 0.03

            if filters.get("language") and item.get("languages"):
                if filters["language"] not in item["languages"]:
                    penalty += 0.03

            new_item = dict(item)
            new_item["_penalty"] = penalty
            results.append(new_item)

        return results

    # ------------------------------
    # Hybrid Scoring
    # ------------------------------
    def _score_item(
        self,
        item: Dict[str, Any],
        semantic_score: float,
        filters: Dict[str, Any],
        intents: dict
    ) -> Dict[str, Any]:

        base = self._safe_float(semantic_score)
        score = base * SCORING_WEIGHTS["semantic"]
        reasons = ["semantic_match"]

        # --- Business boosts ---
        if filters.get("remote") and item.get("remote"):
            score += SCORING_WEIGHTS["remote"]
            reasons.append("remote_match")

        if filters.get("adaptive") and item.get("adaptive"):
            score += SCORING_WEIGHTS["adaptive"]
            reasons.append("adaptive_match")

        if filters.get("job_family") and item.get("job_family"):
            if filters["job_family"].lower() in item["job_family"].lower():
                score += SCORING_WEIGHTS["job_family"]
                reasons.append("job_family_match")

        if filters.get("max_duration") and item.get("duration"):
            if item["duration"] <= filters["max_duration"]:
                score += SCORING_WEIGHTS["duration"]
                reasons.append("duration_match")

        if filters.get("language") and item.get("languages"):
            if filters["language"] in item["languages"]:
                score += SCORING_WEIGHTS["language"]
                reasons.append("language_match")

        if item.get("confidence") is not None:
            conf = self._safe_float(item["confidence"])
            score += SCORING_WEIGHTS["confidence"] * conf
            reasons.append("confidence_boost")

        # --- Intent intelligence ---
        intent_boost = self._generic_intent_boost(intents, item)
        if intent_boost > 0:
            score += SCORING_WEIGHTS["intent"] * intent_boost
            reasons.append("intent_alignment")

        score = self._normalize_score(score - item.get("_penalty", 0.0))

        enriched = dict(item)
        enriched["final_score"] = score
        enriched["explain"] = reasons
        enriched["intent_boost"] = round(intent_boost, 4)
        enriched["intents"] = intents

        return enriched

    # ------------------------------
    # Public API
    # ------------------------------
    def recommend(
        self,
        query: str,
        top_k: int = 5,
        remote: bool = False,
        adaptive: bool = False,
        job_family: Optional[str] = None,
        max_duration: Optional[int] = None,
        language: Optional[str] = None
    ) -> List[Dict[str, Any]]:

        logger.info(f"Recommendation query: {query}")

        filters = {
            "remote": remote,
            "adaptive": adaptive,
            "job_family": job_family,
            "max_duration": max_duration,
            "language": language
        }

        # Step 1: Semantic retrieval
        semantic_results = self.search_engine.search(query, top_k=top_k * 4)

        if not semantic_results:
            logger.warning("No semantic results found")
            return []

        # Step 2: Soft filtering
        filtered = self._apply_soft_filters(semantic_results, filters)

        # Step 3: Intent extraction
        intents = self._extract_intents(query)

        # Step 4: Hybrid scoring
        scored = []
        for item in filtered:
            enriched = self._score_item(
                item=item,
                semantic_score=item.get("score", 0.0),
                filters=filters,
                intents=intents
            )
            scored.append(enriched)

        # Step 5: Deterministic ranking
        ranked = sorted(
            scored,
            key=lambda x: (x["final_score"], self._safe_float(x.get("score", 0.0))),
            reverse=True
        )

        # Step 6: Return top_k
        return ranked[:top_k]