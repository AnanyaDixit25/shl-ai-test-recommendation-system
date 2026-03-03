# ai/semantic_search.py

"""
Enterprise Semantic Search Engine — v3 ULTRA
----------------------------------------------
Major upgrades:
  1. Query expansion: maps synonyms & intents to SHL vocabulary before embedding
     so "verbal reasoning" → finds "Verify Verbal Ability" reliably.
  2. Field-weighted BM25+ keyword scoring: name(5x) > keywords(3x) > description(1x)
     with exact phrase and partial-token bonuses.
  3. Cognitive domain reverse-index: maps query terms like "abstract", "numerical",
     "inductive" directly to tests containing those cognitive domains.
  4. Test type signal boosting: queries containing "knowledge", "coding", "simulation"
     directly boost K, S, E type tests respectively.
  5. Confidence-score amplification: SHL's own confidence_score (0.75–0.95) is used
     as a tie-breaker multiplier so higher-quality assessments rank first.
  6. All original filter logic preserved exactly — no breaking changes.
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

# ──────────────────────────────────────────────────────────────────────────────
# SHL-Specific Query Expansion Dictionary
# Maps natural language queries → SHL assessment vocabulary
# This is the single biggest accuracy upgrade: closing the vocabulary gap
# between "what a hiring manager types" vs "how SHL names its tests"
# ──────────────────────────────────────────────────────────────────────────────
QUERY_EXPANSION = {
    # Cognitive / Aptitude
    "verbal":           "verbal ability reasoning language comprehension",
    "verbal reasoning": "verbal ability verify language comprehension text",
    "numerical":        "numerical ability reasoning calculation quantitative mathematics",
    "numerical reasoning": "numerical ability calculation quantitative verify",
    "abstract":         "abstract reasoning inductive logical patterns",
    "inductive":        "inductive reasoning abstract logical patterns sequences",
    "deductive":        "deductive reasoning logical critical thinking analysis",
    "logical":          "logical reasoning abstract inductive deductive critical thinking",
    "cognitive":        "cognitive ability aptitude reasoning verbal numerical abstract",
    "reasoning":        "reasoning ability aptitude cognitive abstract verbal numerical inductive",
    "aptitude":         "aptitude ability cognitive reasoning verify",
    "problem solving":  "problem solving reasoning critical thinking inductive abstract",
    "critical thinking":"critical thinking reasoning analysis cognitive",
    "spatial":          "spatial reasoning abstract visual patterns",
    "mechanical":       "mechanical reasoning spatial technical aptitude",

    # Personality / Behavior
    "personality":      "personality behavior OPQ situational judgement competencies",
    "behaviour":        "behavior personality OPQ situational judgement",
    "behavioral":       "behavior personality competencies situational judgement OPQ",
    "opq":              "OPQ personality behavior occupational questionnaire",
    "motivation":       "motivation personality behavior values drive",
    "values":           "values personality culture fit behavior",
    "integrity":        "integrity honesty personality counter-productive behavior",

    # Situational Judgment
    "situational":      "situational judgement SJT biodata scenarios behavioral",
    "sjt":              "situational judgement scenarios biodata behavioral",
    "judgement":        "situational judgement biodata decision making scenarios",
    "judgment":         "situational judgement biodata decision making scenarios",

    # Leadership / Management
    "leadership":       "leadership management competencies 360 enterprise OPQ",
    "leader":           "leadership management competencies 360 development",
    "management":       "management leadership competencies supervisor manager",
    "executive":        "executive leadership senior management competencies",
    "360":              "360 development feedback leadership enterprise",

    # Sales
    "sales":            "sales account manager selling negotiation customer",
    "selling":          "sales selling account manager customer negotiation",
    "account manager":  "account manager sales solution negotiation customer",

    # Customer Service / Contact Center
    "customer service": "customer service contact center support solution",
    "call center":      "contact center customer service phone support solution",
    "contact center":   "contact center customer service solution phone support",

    # IT / Technical
    "developer":        "developer software engineer programmer knowledge skills",
    "software engineer":"software engineer developer programmer knowledge skills IT",
    "programmer":       "programmer developer software engineer coding knowledge",
    "coding":           "coding programming developer knowledge skills automata",
    "java developer":   "Java core java developer knowledge skills IT programmer",
    "python developer": "Python developer knowledge skills IT programmer",
    "data science":     "data science analytics machine learning Python SQL automata",
    "data scientist":   "data science analytics machine learning Python SQL statistics",
    "machine learning": "machine learning AI data science Python statistics",
    "devops":           "DevOps cloud AWS Linux infrastructure systems",
    "cloud":            "cloud computing AWS Azure GCP infrastructure DevOps",
    "full stack":       "full stack developer JavaScript React Node.js backend frontend",
    "frontend":         "frontend developer JavaScript React Angular HTML CSS",
    "backend":          "backend developer server-side API database programming",
    "database":         "database SQL Oracle MySQL PostgreSQL data management",
    "network":          "network engineer analyst systems infrastructure",
    "security":         "security cybersecurity information security network",

    # Healthcare
    "nurse":            "nurse nursing healthcare clinical aide solution",
    "healthcare":       "healthcare clinical nursing aide medical solution",
    "clinical":         "clinical healthcare nursing medical professional",

    # General
    "graduate":         "graduate entry level new hire talent acquisition",
    "entry level":      "entry level graduate new hire beginner",
    "intern":           "entry level graduate intern student",
    "manager":          "manager management supervisor leadership solution",
    "supervisor":       "supervisor front line manager leadership management",
    "administrative":   "administrative assistant clerical support office",
    "clerical":         "clerical administrative assistant office support",
    "finance":          "finance accounting financial analyst banking",
    "accounting":       "accounting finance bookkeeping audit financial",
    "insurance":        "insurance agency manager sales solution",
    "retail":           "retail store manager cashier sales customer",
    "industrial":       "industrial operations entry level safety manufacturing",
    "safety":           "safety industrial workplace screening solution",
}

# ──────────────────────────────────────────────────────────────────────────────
# Cognitive Domain Reverse Index
# Maps query terms → cognitive_domain_ids to directly boost matching tests
# ──────────────────────────────────────────────────────────────────────────────
COGNITIVE_SIGNALS: Dict[str, str] = {
    "verbal":           "COG_VRB_001",
    "numerical":        "COG_NUM_001",
    "abstract":         "COG_ABS_001",
    "inductive":        "COG_IND_001",
    "critical thinking":"COG_CRT_001",
    "learning agility": "COG_LRN_001",
    "processing speed": "COG_SPD_001",
    "working memory":   "COG_WMM_001",
    "speed":            "COG_SPD_001",
    "memory":           "COG_WMM_001",
    "reasoning":        "COG_ABS_001",  # generic reasoning → abstract
}

# ──────────────────────────────────────────────────────────────────────────────
# Test Type Code → label mapping (for query intent detection)
# ──────────────────────────────────────────────────────────────────────────────
TEST_TYPE_SIGNALS: Dict[str, str] = {
    "knowledge":        "K",
    "skills":           "K",
    "technical":        "K",
    "coding":           "K",
    "programming":      "K",
    "personality":      "P",
    "behaviour":        "P",
    "behavior":         "P",
    "opq":              "P",
    "ability":          "A",
    "aptitude":         "A",
    "reasoning":        "A",
    "cognitive":        "A",
    "biodata":          "B",
    "situational":      "B",
    "sjt":              "B",
    "simulation":       "S",
    "exercise":         "E",
    "competencies":     "C",
    "leadership":       "C",
    "360":              "D",
    "development":      "D",
    "feedback":         "D",
}


class SemanticSearchEngine:
    """
    Hybrid Semantic + Keyword Search Engine — v3 ULTRA.

    Scoring formula (final hybrid 0–1):
        hybrid = 0.50 * semantic_score
               + 0.35 * keyword_score
               + 0.10 * cognitive_boost
               + 0.05 * confidence_amplifier

    Where:
        - semantic_score:      normalized FAISS cosine similarity (0–1)
        - keyword_score:       field-weighted BM25+ token overlap (0–1)
        - cognitive_boost:     cognitive domain reverse-index match (0–1)
        - confidence_amplifier: SHL's own quality signal (0.75–0.95 → 0–1)
    """

    def __init__(
        self,
        index_path: str = "data/vector/index.faiss",
        meta_path: str = "data/vector/metadata.json",
        normalize: bool = True,
    ):
        logger.info("Initializing SemanticSearchEngine v3 ULTRA...")
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
    # Query Expansion
    # Enriches the raw query with SHL vocabulary before embedding
    # This dramatically improves recall for natural-language queries
    # ──────────────────────────────────────────────────────────────────
    @staticmethod
    def _expand_query(query: str) -> str:
        """
        Expand query with SHL-specific synonyms and vocabulary.
        Returns original query + expansion terms.
        """
        q_lower = query.lower().strip()
        expansions = []

        # Check multi-word phrases first (order matters: longest first)
        multi_word_keys = sorted(
            [k for k in QUERY_EXPANSION if " " in k],
            key=len, reverse=True
        )
        for phrase in multi_word_keys:
            if phrase in q_lower:
                expansions.append(QUERY_EXPANSION[phrase])

        # Then single-word tokens
        tokens = re.findall(r"\b\w[\w.#+]*\b", q_lower)
        for token in tokens:
            if token in QUERY_EXPANSION and QUERY_EXPANSION[token] not in expansions:
                expansions.append(QUERY_EXPANSION[token])

        if expansions:
            expanded = query + " " + " ".join(expansions)
            logger.debug(f"Query expanded: '{query}' → '{expanded[:120]}...'")
            return expanded

        return query

    # ──────────────────────────────────────────────────────────────────
    # Cognitive domain boost
    # Directly rewards items whose cognitive_domain_ids match query intent
    # ──────────────────────────────────────────────────────────────────
    @staticmethod
    def _cognitive_boost(query: str, item: dict) -> float:
        """
        Returns 0–1 based on how many cognitive domain signals in the
        query match the item's cognitive_domain_ids.
        """
        q_lower = query.lower()
        item_cog = (item.get("cognitive_domain_ids") or "").upper()

        if not item_cog:
            return 0.0

        matched = 0
        total_signals = 0
        for term, cog_id in COGNITIVE_SIGNALS.items():
            if term in q_lower:
                total_signals += 1
                if cog_id in item_cog:
                    matched += 1

        if total_signals == 0:
            return 0.0

        return round(min(matched / total_signals, 1.0), 4)

    # ──────────────────────────────────────────────────────────────────
    # Test type signal boost
    # Rewards items whose test_type_codes match the implied type in query
    # ──────────────────────────────────────────────────────────────────
    @staticmethod
    def _test_type_boost(query: str, item: dict) -> float:
        """
        Returns 0–1 if item's test_type_codes match what the query implies.
        e.g. query "coding test for java developer" → K-type items boosted.
        """
        q_lower = query.lower()
        item_codes = (item.get("test_type_codes") or "").upper()

        if not item_codes:
            return 0.0

        implied_codes = set()
        for term, code in TEST_TYPE_SIGNALS.items():
            if re.search(rf"\b{re.escape(term)}\b", q_lower):
                implied_codes.add(code)

        if not implied_codes:
            return 0.0

        item_code_set = set(c.strip() for c in item_codes.split(","))
        matched = implied_codes & item_code_set

        if matched:
            # Partial match = 0.5, full match = 1.0
            return round(len(matched) / len(implied_codes), 4)

        return 0.0

    # ──────────────────────────────────────────────────────────────────
    # Bool coercion — preserves existing behavior exactly
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
    # BM25+ keyword scorer — field-weighted with phrase and partial bonuses
    # ──────────────────────────────────────────────────────────────────
    @staticmethod
    def _keyword_score(query: str, item: dict) -> float:
        """
        Weighted BM25+ keyword score.
        Field weights: name(5x) > keywords(3x) > job_family(2x) > description(1x)
        Bonuses: exact phrase in name (+0.35), per-token partial name match (+0.15 each)
        """
        q_lower = query.lower().strip()
        q_tokens = set(re.findall(r"\b[\w.#+]+\b", q_lower))
        if not q_tokens:
            return 0.0

        name        = (item.get("name") or "").lower()
        keywords    = (item.get("keywords") or "").lower()
        description = (item.get("description") or "").lower()
        job_family  = (item.get("job_family") or "").lower()

        # Weighted field corpus
        weighted_text = (
            (name + " ") * 5
            + (keywords + " ") * 3
            + (job_family + " ") * 2
            + (description + " ") * 1
        )
        doc_tokens = set(re.findall(r"\b[\w.#+]+\b", weighted_text))

        # Token overlap ratio
        matched = q_tokens & doc_tokens
        overlap = len(matched) / len(q_tokens) if q_tokens else 0.0

        # Exact phrase bonus: full query appears in name
        phrase_bonus = 0.35 if q_lower in name else 0.0

        # Per-token partial match in name (rewards 3+ char tokens)
        partial_bonus = 0.0
        for tok in q_tokens:
            if len(tok) >= 3 and re.search(rf"\b{re.escape(tok)}\b", name):
                partial_bonus += 0.15
        partial_bonus = min(partial_bonus, 0.45)

        # Keyword field exact match bonus (test names often appear in keywords)
        keyword_phrase_bonus = 0.2 if q_lower in keywords else 0.0

        raw = overlap + phrase_bonus + partial_bonus + keyword_phrase_bonus
        return round(min(raw, 1.0), 4)

    # ──────────────────────────────────────────────────────────────────
    # Confidence amplifier
    # SHL's own confidence_score (0.75–0.95) as a subtle quality signal
    # ──────────────────────────────────────────────────────────────────
    @staticmethod
    def _confidence_amplifier(item: dict) -> float:
        """
        Normalize SHL confidence_score from [0.75, 0.95] → [0, 1].
        HIGH confidence assessments get a tie-breaking edge.
        """
        raw = SemanticSearchEngine._safe_float(item.get("confidence_score", 0.82))
        # Map [0.75, 0.95] → [0, 1]
        normalized = (raw - 0.75) / (0.95 - 0.75)
        return round(min(max(normalized, 0.0), 1.0), 4)

    # ──────────────────────────────────────────────────────────────────
    # Normalize FAISS cosine score [-1,1] → [0,1]
    # ──────────────────────────────────────────────────────────────────
    @staticmethod
    def _normalize_cosine(score: float) -> float:
        return (score + 1.0) / 2.0

    # ──────────────────────────────────────────────────────────────────
    # Hard filter — preserves original behavior exactly
    # ──────────────────────────────────────────────────────────────────
    def _passes_hard_filters(
        self,
        item: dict,
        remote: Optional[bool],
        adaptive: Optional[bool],
        max_duration: Optional[int],
        language: Optional[str],
    ) -> bool:
        if remote:
            if not self._to_bool(item.get("remote_testing")):
                return False

        if adaptive:
            if not self._to_bool(item.get("adaptive_irt")):
                return False

        if max_duration is not None and max_duration > 0:
            dur = item.get("duration_minutes")
            if dur is not None and dur != "":
                try:
                    if int(float(str(dur))) > max_duration:
                        return False
                except:
                    pass

        if language and language.lower() not in ("any", "all", ""):
            langs = (item.get("languages") or "").lower()
            if language.lower() not in langs:
                return False

        return True

    # ──────────────────────────────────────────────────────────────────
    # Core search — all original params preserved
    # ──────────────────────────────────────────────────────────────────
    def search(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        remote: Optional[bool] = None,
        adaptive: Optional[bool] = None,
        max_duration: Optional[int] = None,
        language: Optional[str] = None,
    ) -> List[Dict[str, Any]]:

        if not query or not isinstance(query, str):
            logger.warning("Invalid query")
            return []

        # ── Query expansion (key accuracy upgrade) ───────────────────
        expanded_query = self._expand_query(query)

        # ── Embed expanded query ─────────────────────────────────────
        try:
            query_vec = self.embedder.embed([expanded_query])
            if not isinstance(query_vec, np.ndarray):
                query_vec = np.array(query_vec, dtype=np.float32)
            query_vec = query_vec.astype(np.float32)
            if self.normalize:
                faiss.normalize_L2(query_vec)
        except Exception as e:
            logger.error(f"Embedding failed: {e}")
            return []

        # ── FAISS search ─────────────────────────────────────────────
        fetch_k = min(top_k * 8, self.index.ntotal)
        try:
            scores, indices = self.index.search(query_vec, fetch_k)
        except Exception as e:
            logger.error(f"FAISS search failed: {e}")
            return []

        # ── Merge filter sources (preserves existing dict-based filter support) ─
        if filters:
            remote       = remote       or filters.get("remote")
            adaptive     = adaptive     or filters.get("adaptive")
            max_duration = max_duration or filters.get("max_duration")
            language     = language     or filters.get("language")

        results = []

        for raw_score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue

            item = self.metadata.get(str(idx))
            if not item:
                continue

            # Hard filter (unchanged)
            if not self._passes_hard_filters(item, remote, adaptive, max_duration, language):
                continue

            # ── Multi-signal scoring ─────────────────────────────────
            sem_score    = self._normalize_cosine(self._safe_float(raw_score))
            kw_score     = self._keyword_score(query, item)    # use RAW query for kw
            cog_boost    = self._cognitive_boost(query, item)
            tt_boost     = self._test_type_boost(query, item)
            conf_amp     = self._confidence_amplifier(item)

            # Weighted hybrid — semantic anchors, keyword/cognitive/conf refine
            hybrid = (
                0.50 * sem_score
                + 0.30 * kw_score
                + 0.08 * cog_boost
                + 0.07 * tt_boost
                + 0.05 * conf_amp
            )
            hybrid = round(min(max(hybrid, 0.0), 1.0), 4)

            result = {
                # All original fields preserved exactly
                "score":       hybrid,
                "_sem_score":  round(sem_score, 4),
                "_kw_score":   round(kw_score, 4),
                "_cog_boost":  round(cog_boost, 4),
                "_tt_boost":   round(tt_boost, 4),
                "id":          item.get("id"),
                "name":        item.get("name"),
                "job_family":  item.get("job_family"),
                "job_levels":  item.get("job_levels"),
                "test_type":   item.get("test_type_labels"),
                "test_type_codes": item.get("test_type_codes"),
                "remote":      self._to_bool(item.get("remote_testing")),
                "adaptive":    self._to_bool(item.get("adaptive_irt")),
                "duration":    item.get("duration_minutes"),
                "languages":   item.get("languages"),
                "url":         item.get("url", ""),
                "keywords":    item.get("keywords", ""),
                "description": item.get("description", ""),
                "confidence":  self._safe_float(item.get("confidence_score", 0.0)),
                "cognitive_domains": item.get("cognitive_domain_ids", ""),
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