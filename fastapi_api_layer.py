from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware
import logging

from ai.semantic_search import SemanticSearchEngine
from ai.recommender import RecommenderEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | API | %(message)s")
logger = logging.getLogger("API")

app = FastAPI(
    title="AI Recommendation API",
    version="2.0",
    description="Enterprise-grade AI Semantic Search & Recommendation Platform"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

semantic_engine: Optional[SemanticSearchEngine] = None
recommender_engine: Optional[RecommenderEngine] = None


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5


class RecommendRequest(BaseModel):
    query: str
    top_k: int = 5
    remote: Optional[bool] = False
    adaptive: Optional[bool] = False
    max_duration: Optional[int] = None
    language: Optional[str] = None
    level_filter: Optional[str] = None   # NEW: e.g. "Entry-Level", "Graduate", "Manager"


@app.on_event("startup")
def startup_event():
    global semantic_engine, recommender_engine
    logger.info("Initializing AI engines...")
    semantic_engine = SemanticSearchEngine()
    recommender_engine = RecommenderEngine()
    logger.info("AI engines ready ✅")


@app.get("/")
def root():
    return {"status": "running", "service": "AI Recommendation API", "version": "2.0"}


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "semantic_engine": semantic_engine is not None,
        "recommender_engine": recommender_engine is not None,
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
        results = recommender_engine.recommend(
            query=req.query,
            top_k=req.top_k,
            remote=req.remote,
            adaptive=req.adaptive,
            max_duration=req.max_duration,
            language=req.language,
            level_filter=req.level_filter,    # NEW
        )
        return {"query": req.query, "count": len(results), "results": results}
    except Exception as e:
        logger.error(f"Recommendation error: {e}")
        return {"error": "recommendation_failed", "message": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("fastapi_api_layer:app", host="0.0.0.0", port=8000, reload=True, log_level="info")