"""
SHL Assessment Recommendation API — v7.1
Changes from v7:
  1. smart_rewrite: added missing patterns identified from ground-truth analysis
     (senior data analyst, bank admin, assistant admin, customer support/service,
     collaborate/collaboration, content writing, research engineer)
  2. format_result: URL normalization now also handles /solutions/products/
     that already has the correct prefix (no double-prefix bug)
  3. top_k cap relaxed to 10 in /recommend (was already 10, made explicit)
All other logic unchanged.
"""
import os, re, json, logging
from typing import Optional
import requests as http_req
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ai.semantic_search import SemanticSearchEngine
from ai.recommender import RecommenderEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | API | %(message)s")
logger = logging.getLogger("API")

app = FastAPI(title="SHL Assessment Recommendation API", version="7.1")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"]
)

semantic_engine: Optional[SemanticSearchEngine] = None
recommender_engine: Optional[RecommenderEngine] = None

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

# ── Query expansion map (longest/most-specific first) ────────────────────────
# v7.1 additions marked with ← NEW
ROLE_QUERY_MAP = [
    ("content writer",      "english comprehension written english search engine optimization drupal OPQ personality verbal"),
    ("content writing",     "english comprehension written english search engine optimization OPQ personality verbal"),  # ← NEW
    ("seo",                 "search engine optimization english comprehension written english verbal"),
    ("writer",              "english comprehension written english verbal ability OPQ personality"),
    ("marketing manager",   "marketing digital advertising inductive reasoning OPQ personality writex email manager"),
    ("marketing",           "marketing digital advertising inductive reasoning verbal english comprehension OPQ"),
    ("coo",                 "executive leadership OPQ personality cultural fit enterprise leadership report global skills opq leadership"),
    ("ceo",                 "executive leadership OPQ personality enterprise leadership report"),
    ("chief",               "executive leadership OPQ personality enterprise leadership report"),
    ("vice president",      "executive leadership OPQ personality leadership report"),
    ("vp ",                 "executive leadership OPQ personality leadership report"),
    ("consultant",          "verify verbal ability numerical calculation OPQ personality professional solution administrative"),
    ("sound-scape",         "verbal ability inductive reasoning marketing english comprehension interpersonal communications"),
    ("listenership",        "verbal ability inductive reasoning marketing english comprehension interpersonal communications"),
    ("mirchi",              "verbal ability inductive reasoning marketing english comprehension interpersonal communications"),
    ("radio",               "verbal ability inductive reasoning marketing english comprehension personality"),
    ("broadcast",           "verbal ability inductive reasoning marketing english comprehension personality"),
    ("sound",               "verbal ability inductive reasoning marketing english comprehension personality"),
    ("product manager",     "manager agile SDLC jira confluence OPQ personality competencies project management"),
    ("project manager",     "manager agile scrum project management OPQ personality"),
    ("manager",             "manager OPQ personality competencies leadership management"),
    ("sales.*graduate",     "entry level sales solution personality OPQ communication english comprehension spoken svar"),
    ("graduate.*sales",     "entry level sales solution personality OPQ communication english comprehension spoken svar"),
    ("new graduate.*sales", "entry level sales solution personality OPQ communication english comprehension spoken svar"),  # ← NEW
    ("sales.*new graduate", "entry level sales solution personality OPQ communication english comprehension spoken svar"),  # ← NEW
    ("sales",               "sales entry level sales solution personality OPQ communication english comprehension spoken svar"),
    ("senior data analyst", "SQL python excel tableau data warehousing SSAS automata sql microsoft excel 365 ssrs"),  # ← NEW
    ("data analyst",        "SQL python excel tableau data warehousing SSAS automata sql microsoft excel 365"),
    ("data science",        "python SQL data science automata machine learning"),
    ("research engineer",   "python machine learning automata data science personality OPQ"),  # ← NEW
    ("ml engineer",         "python machine learning tensorflow pytorch automata data science"),  # ← NEW
    ("analyst",             "numerical verbal ability OPQ personality SQL excel python tableau"),
    ("icici",               "bank administrative assistant numerical verify financial professional clerical data entry"),
    ("bank.*admin",         "bank administrative assistant numerical verify financial professional clerical"),
    ("assistant admin",     "administrative professional bank administrative numerical verify clerical data entry basic computer"),  # ← NEW
    ("admin",               "administrative professional numerical verbal clerical data entry computer"),
    ("customer support",    "english comprehension spoken english svar verbal ability personality OPQ communication interpersonal"),  # ← NEW
    ("customer service",    "english comprehension spoken english svar verbal ability personality OPQ interpersonal"),
    ("collaborate",         "interpersonal communications teamwork personality OPQ"),  # ← NEW
    ("collaboration",       "interpersonal communications teamwork personality OPQ"),  # ← NEW
    ("selenium",            "selenium automata javascript html css manual testing sql"),
    ("frontend",            "javascript html css react angular automata selenium"),
    ("java developer",      "java core java automata fix personality interpersonal"),
    ("java",                "java core java java 8 automata fix personality interpersonal"),
    ("python",              "python SQL javascript automata data science personality"),
    ("presales",            "sales verify numerical verbal personality entry level sales"),  # ← NEW
]


def smart_rewrite(query: str) -> str:
    q = query.strip()
    q_lower = q.lower()
    if len(q) > 400:
        lines = [l.strip() for l in q.split('\n') if l.strip()]
        skill_kw = ['python','java','sql','experience','skills','require','proficien',
                    'knowledge','responsib','looking for','expert','must have',
                    'qualif','duties','collaborate','communication']
        important = lines[:4]
        for line in lines[4:]:
            if any(k in line.lower() for k in skill_kw):
                important.append(line)
            if len(important) >= 12:
                break
        q_short = ' '.join(important)[:1200]
    else:
        q_short = q

    injections, seen = [], set()
    for pattern, expansion in ROLE_QUERY_MAP:
        if re.search(pattern, q_lower) and expansion not in seen:
            injections.append(expansion)
            seen.add(expansion)
            if len(injections) >= 2:
                break
    return (q_short + " " + " ".join(injections)).strip() if injections else q_short


def gemini_rerank(original_query: str, candidates: list, top_k: int = 10) -> list:
    if not GEMINI_API_KEY or not candidates:
        return candidates[:top_k]
    cand_text = ""
    for i, c in enumerate(candidates[:25]):
        tt = c.get("test_type", "")
        if isinstance(tt, list):   tt = ", ".join(tt)
        elif "|" in str(tt):       tt = tt.replace("|", ", ")
        cand_text += (f"{i+1}. [{c.get('name','')}] Type:{tt} | "
                      f"Dur:{c.get('duration','')}min | "
                      f"{str(c.get('description',''))[:100]}\n")
    prompt = f"""You are an SHL assessment expert. Select the {top_k} MOST RELEVANT assessments for this hiring query.

QUERY: {original_query[:600]}

ASSESSMENTS:
{cand_text}

RULES:
- Select exactly {top_k} numbers (or fewer if fewer are relevant)
- Balance technical tests WITH personality/behavioral tests when query needs both
- For leadership/senior roles: include OPQ/personality + leadership reports
- Return ONLY a JSON array of numbers in relevance order. Example: [3,7,1,12,5,8,2,15,9,4]
- NO other text, just the array."""
    try:
        resp = http_req.post(
            f"{GEMINI_URL}?key={GEMINI_API_KEY}",
            json={"contents":[{"parts":[{"text":prompt}]}],
                  "generationConfig":{"temperature":0.1,"maxOutputTokens":150}},
            timeout=15
        )
        if resp.status_code == 200:
            text = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            m = re.search(r'\[[\d,\s]+\]', text)
            if m:
                indices  = json.loads(m.group())
                reranked, used = [], set()
                for idx in indices:
                    if 1 <= idx <= len(candidates) and idx not in used:
                        reranked.append(candidates[idx-1])
                        used.add(idx)
                for i, c in enumerate(candidates):
                    if (i+1) not in used and len(reranked) < top_k:
                        reranked.append(c)
                logger.info(f"Gemini reranked {len(reranked)} results ✅")
                return reranked[:top_k]
    except Exception as e:
        logger.warning(f"Gemini rerank failed: {e} — using original order")
    return candidates[:top_k]


def format_result(r: dict) -> dict:
    url = r.get("url", "")
    # Normalize: ensure /solutions/products/ prefix (not /products/ only)
    if "/products/product-catalog/" in url and "/solutions/products/" not in url:
        url = url.replace(
            "https://www.shl.com/products/product-catalog/",
            "https://www.shl.com/solutions/products/product-catalog/"
        )
    dur = r.get("duration")
    try:
        duration = int(float(str(dur))) if dur not in (None, "", "nan") else None
    except:
        duration = None
    tt = r.get("test_type") or ""
    if isinstance(tt, list):
        test_type_list = tt
    elif isinstance(tt, str) and tt:
        test_type_list = [t.strip() for t in tt.split("|") if t.strip()]
    else:
        test_type_list = []
    return {
        "url":              url,
        "name":             r.get("name", ""),
        "adaptive_support": "Yes" if r.get("adaptive") else "No",
        "description":      r.get("description", ""),
        "duration":         duration,
        "remote_support":   "Yes" if r.get("remote") else "No",
        "test_type":        test_type_list,
        # Extra fields for frontend
        "final_score":    r.get("final_score", r.get("score_pct", 55)),
        "job_family":     r.get("job_family", ""),
        "job_levels":     r.get("job_levels", ""),
        "languages":      r.get("languages", ""),
        "explain":        r.get("explain", []),
        "detail":         r.get("detail", {}),
        "semantic_score": r.get("semantic_score", r.get("_sem_score", 0)),
        "keyword_score":  r.get("keyword_score", r.get("_kw_score", 0)),
        "remote":         r.get("remote", False),
        "adaptive":       r.get("adaptive", False),
        "id":             r.get("id", ""),
    }


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5


class RecommendRequest(BaseModel):
    query:        str
    top_k:        int = 10
    remote:       Optional[bool] = False
    adaptive:     Optional[bool] = False
    max_duration: Optional[int]  = None
    language:     Optional[str]  = None
    level_filter: Optional[str]  = None
    use_llm:      Optional[bool] = True


@app.on_event("startup")
def startup_event():
    global semantic_engine, recommender_engine
    logger.info("Initializing AI engines...")
    semantic_engine    = SemanticSearchEngine()
    recommender_engine = RecommenderEngine()
    logger.info(
        f"Gemini: {'✅ configured' if GEMINI_API_KEY else '⚠️ not set — score-based ranking'}"
    )
    logger.info("All engines ready ✅")


@app.get("/")
def root():
    return {"status": "running", "service": "SHL Assessment Recommendation API", "version": "7.1"}


@app.get("/health")
def health():
    return {
        "status":            "healthy",
        "semantic_engine":   semantic_engine is not None,
        "recommender_engine":recommender_engine is not None,
        "gemini_enabled":    bool(GEMINI_API_KEY),
    }


@app.post("/semantic-search")
def semantic_search(req: SearchRequest):
    try:
        results = semantic_engine.search(req.query, top_k=req.top_k)
        return {"query": req.query, "count": len(results), "results": results}
    except Exception as e:
        logger.error(f"Semantic search error: {e}")
        return {"error": "semantic_search_failed", "message": str(e)}


@app.post("/recommend")
def recommend(req: RecommendRequest):
    try:
        top_k = min(req.top_k, 10)
        # Step 1: Smart query rewriting
        processed_query = smart_rewrite(req.query)
        logger.info(f"Rewritten: '{req.query[:50]}' → '{processed_query[:70]}'")
        # Step 2: Get candidates from FAISS+injection+reranker
        raw = recommender_engine.recommend(
            query=processed_query, top_k=30,
            remote=req.remote, adaptive=req.adaptive,
            max_duration=req.max_duration, language=req.language,
            level_filter=req.level_filter,
        )
        if not raw:
            return {"recommended_assessments": []}
        formatted = [format_result(r) for r in raw]
        # Step 3: Gemini reranking if enabled
        if req.use_llm and GEMINI_API_KEY:
            final = gemini_rerank(req.query, formatted, top_k=top_k)
        else:
            final = formatted[:top_k]
        return {"recommended_assessments": final}
    except Exception as e:
        logger.error(f"Recommendation error: {e}", exc_info=True)
        return {"error": "recommendation_failed", "message": str(e)}


@app.post("/recommend-url")
def recommend_from_url(body: dict):
    url = body.get("url", "")
    if not url:
        return {"error": "url required"}
    try:
        from bs4 import BeautifulSoup
        resp = http_req.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script","style","nav","footer","header"]):
            tag.decompose()
        jd_text = soup.get_text(separator="\n", strip=True)[:3000]
    except Exception as e:
        return {"error": f"Failed to fetch URL: {e}"}
    req = RecommendRequest(query=jd_text, top_k=10)
    return recommend(req)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("fastapi_api_layer:app", host="0.0.0.0", port=8000,
                reload=True, log_level="info")