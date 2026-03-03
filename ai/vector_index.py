# ai/vector_index.py  (scripts/build_vector_index.py — same logic)

"""
Vector Index Builder — v3 ULTRA
---------------------------------
Key upgrade: _build_text() now constructs a much richer semantic document per item.

OLD: ~4 fields joined with pipes, minimal context
NEW: 12+ signals including:
  - Cognitive domain IDs decoded to readable names
  - Test type codes decoded to readable labels
  - SHL confidence band included
  - Repeated title and keywords (increases weight in embedding space)
  - Domain inference expanded and more precise
  - Job level and industry context embedded explicitly

This means the FAISS index itself is far more semantically accurate before
hybrid scoring even starts.

All paths, method names, and public interfaces preserved.
"""

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
# Paths (preserved exactly)
# ==============================
BASE_DIR       = Path("data")
PROCESSED_PATH = BASE_DIR / "processed" / "processed_catalogue.json"

VECTOR_DIR     = BASE_DIR / "vector"
INDEX_PATH     = VECTOR_DIR / "index.faiss"
META_PATH      = VECTOR_DIR / "metadata.json"

VECTOR_DIR.mkdir(parents=True, exist_ok=True)

# ==============================
# Decode Maps — new in v3
# ==============================
COG_DOMAIN_LABELS = {
    "COG_LRN_001": "learning agility adaptability",
    "COG_SPD_001": "processing speed accuracy efficiency",
    "COG_CRT_001": "critical thinking deductive reasoning analysis",
    "COG_ABS_001": "abstract reasoning spatial patterns",
    "COG_IND_001": "inductive reasoning logical patterns sequences",
    "COG_NUM_001": "numerical reasoning quantitative mathematics calculation",
    "COG_VRB_001": "verbal reasoning language comprehension text",
    "COG_WMM_001": "working memory recall retention multitasking",
}

TEST_TYPE_LABELS = {
    "K": "knowledge skills technical domain expertise",
    "P": "personality behavior OPQ traits values",
    "A": "ability aptitude reasoning cognitive",
    "B": "biodata situational judgement SJT scenarios decisions",
    "S": "simulation realistic work scenarios",
    "C": "competencies leadership soft skills",
    "D": "development 360 feedback growth",
    "E": "assessment exercises structured tasks",
}


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
    # Text Builder — v3 ULTRA
    # --------------------------
    def _build_text(self, item: Dict[str, Any]) -> str:
        """
        Builds a rich, multi-signal semantic document for embedding.
        Each field is decoded, weighted, and contextually expanded.
        """

        def safe_str(val):
            if isinstance(val, list):
                return " ".join(str(v) for v in val)
            return str(val) if val else ""

        name        = safe_str(item.get("name", ""))
        desc        = safe_str(item.get("description", ""))
        keywords    = safe_str(item.get("keywords", ""))
        job_family  = safe_str(item.get("job_family", ""))
        job_levels  = safe_str(item.get("job_levels", ""))
        industry    = safe_str(item.get("industry", ""))
        languages   = safe_str(item.get("languages", ""))
        use_cases   = safe_str(item.get("use_cases", ""))
        conf_band   = safe_str(item.get("confidence_band", ""))

        # Decode cognitive domain IDs → readable labels
        cog_ids = safe_str(item.get("cognitive_domain_ids", ""))
        cog_labels = []
        for cog_id in cog_ids.split("|"):
            cog_id = cog_id.strip()
            if cog_id in COG_DOMAIN_LABELS:
                cog_labels.append(COG_DOMAIN_LABELS[cog_id])
        cog_text = " ".join(cog_labels)

        # Decode test type codes → readable labels
        type_codes = safe_str(item.get("test_type_codes", ""))
        type_labels_decoded = []
        for code in type_codes.split(","):
            code = code.strip()
            if code in TEST_TYPE_LABELS:
                type_labels_decoded.append(TEST_TYPE_LABELS[code])
        type_text = " ".join(type_labels_decoded)

        # Original test_type_labels field
        test_type_labels = safe_str(item.get("test_type_labels", ""))

        # ── Domain inference (expanded + more precise than v2) ──
        lname = name.lower()
        ldesc = desc.lower()
        lkw   = keywords.lower()
        blob  = f"{lname} {ldesc} {lkw}"

        role_context = []

        # Technical domains
        if any(k in blob for k in ["java", "j2ee", "jee", "spring", "hibernate", "ejb"]):
            role_context.append("Java developer enterprise programming object oriented")
        if any(k in blob for k in ["python", "django", "flask", "pandas", "numpy", "scipy"]):
            role_context.append("Python developer data science scripting automation")
        if any(k in blob for k in ["javascript", "js", "node", "react", "angular", "vue", "typescript"]):
            role_context.append("JavaScript web frontend backend developer framework")
        if any(k in blob for k in ["sql", "mysql", "oracle", "postgresql", "pl/sql", "t-sql"]):
            role_context.append("SQL database relational query data management")
        if any(k in blob for k in ["c#", ".net", "asp.net", "mvc", "wpf", "wcf", "xaml"]):
            role_context.append("C# .NET Microsoft developer enterprise applications")
        if any(k in blob for k in ["c++", "c programming", "embedded", "system programming"]):
            role_context.append("C++ systems programming performance embedded software")
        if any(k in blob for k in ["data", "analytics", "statistics", "ml", "ai", "machine learning"]):
            role_context.append("data science analytics machine learning artificial intelligence statistics")
        if any(k in blob for k in ["cloud", "aws", "azure", "gcp", "devops", "kubernetes", "docker"]):
            role_context.append("cloud computing DevOps infrastructure containerization")
        if any(k in blob for k in ["security", "cyber", "network", "firewall", "cisco"]):
            role_context.append("cybersecurity networking information security systems")
        if any(k in blob for k in ["linux", "unix", "bash", "shell", "system admin"]):
            role_context.append("Linux Unix system administration shell scripting")
        if any(k in blob for k in ["sap", "erp", "abap", "hana"]):
            role_context.append("SAP ERP enterprise resource planning ABAP")
        if any(k in blob for k in ["android", "ios", "mobile", "swift", "kotlin"]):
            role_context.append("mobile development Android iOS app developer")
        if any(k in blob for k in ["agile", "scrum", "kanban", "sprint"]):
            role_context.append("Agile Scrum project management software development methodology")
        if any(k in blob for k in ["selenium", "junit", "testing", "qa", "quality assurance"]):
            role_context.append("software testing quality assurance test automation")

        # Business / Cognitive domains
        if any(k in blob for k in ["verbal", "language", "reading", "comprehension", "communication"]):
            role_context.append("verbal ability language reasoning comprehension communication")
        if any(k in blob for k in ["numerical", "calculation", "quantitative", "arithmetic", "mathematical"]):
            role_context.append("numerical ability quantitative reasoning calculation mathematics")
        if any(k in blob for k in ["abstract", "inductive", "logical", "pattern", "reasoning"]):
            role_context.append("abstract inductive reasoning logical patterns cognitive aptitude")
        if any(k in blob for k in ["personality", "behavior", "opq", "trait", "motivation"]):
            role_context.append("personality behavior occupational questionnaire traits motivation values")
        if any(k in blob for k in ["situational", "sjt", "scenario", "judgement", "judgment"]):
            role_context.append("situational judgement test scenarios decisions workplace behaviour")
        if any(k in blob for k in ["leadership", "management", "director", "executive"]):
            role_context.append("leadership management executive development competencies")
        if any(k in blob for k in ["sales", "selling", "negotiation", "account manager"]):
            role_context.append("sales selling negotiation account manager revenue")
        if any(k in blob for k in ["customer service", "call center", "contact center", "support"]):
            role_context.append("customer service contact center support phone agent")
        if any(k in blob for k in ["healthcare", "nursing", "clinical", "medical", "aide"]):
            role_context.append("healthcare nursing clinical medical professional aide")
        if any(k in blob for k in ["finance", "accounting", "audit", "banking", "bookkeeping"]):
            role_context.append("finance accounting banking audit bookkeeping financial")
        if any(k in blob for k in ["graduate", "entry level", "entry-level", "new hire"]):
            role_context.append("graduate entry level new hire early career talent")
        if any(k in blob for k in ["simulation", "realistic", "work sample", "exercise"]):
            role_context.append("simulation realistic work sample assessment exercise")
        if any(k in blob for k in ["360", "development report", "feedback", "growth"]):
            role_context.append("360 degree feedback development growth report")
        if any(k in blob for k in ["adaptive", "irt", "item response"]):
            role_context.append("adaptive testing IRT item response theory precision")
        if any(k in blob for k in ["automata", "coding test", "programming test"]):
            role_context.append("coding programming test automata computer science technical")

        semantic_context = " ".join(role_context)

        # ── Build final rich document ──
        # Title repeated 3x for strong embedding weight
        # Keywords repeated 2x
        parts = [
            f"{name}. {name}. {name}.",
            f"Assessment: {name}",
            f"Description: {desc}",
            f"Keywords: {keywords}. {keywords}.",
            f"Job Family: {job_family}",
            f"Job Levels: {job_levels}",
            f"Industry: {industry}",
            f"Test Types: {test_type_labels}",
            f"Test Type Details: {type_text}",
            f"Cognitive Abilities Measured: {cog_text}",
            f"Use Cases: {use_cases}",
            f"Languages: {languages}",
            f"Quality Band: {conf_band}",
            f"Domain Context: {semantic_context}",
        ]

        return " | ".join(p for p in parts if p.split(": ", 1)[-1].strip())

    # --------------------------
    # Build Index (unchanged signature)
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
            meta[len(texts) - 1] = item

        logger.info(f"Total documents: {len(texts)}")

        if len(texts) == 0:
            raise RuntimeError("No valid documents found to index.")

        logger.info("Generating embeddings...")
        vectors = self.embedding_engine.encode(texts)

        if not isinstance(vectors, np.ndarray):
            vectors = np.array(vectors)

        if vectors.ndim != 2:
            raise RuntimeError("Embedding output has invalid shape")

        logger.info("Normalizing vectors...")
        faiss.normalize_L2(vectors)

        logger.info("Building FAISS IndexFlatIP...")
        index = faiss.IndexFlatIP(self.dim)
        index.add(vectors)

        logger.info("Saving index and metadata...")
        faiss.write_index(index, str(INDEX_PATH))

        with open(META_PATH, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)

        self.index = index
        self.metadata = meta

        logger.info("Vector index build complete ✅")
        logger.info(f"Index saved: {INDEX_PATH} | Metadata: {META_PATH}")

    # --------------------------
    # Load (unchanged)
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

        self.metadata = {int(k): v for k, v in self.metadata.items()}
        logger.info("Vector index loaded ✅")

    # --------------------------
    # Search (unchanged signature)
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
                    "score":       float(score),
                    "id":          item.get("id"),
                    "name":        item.get("name"),
                    "type":        item.get("type"),
                    "job_family":  item.get("job_family"),
                    "url":         item.get("url"),
                    "description": item.get("description"),
                })

        return results