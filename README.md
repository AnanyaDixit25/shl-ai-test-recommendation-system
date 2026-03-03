# SHL AI Test Recommendation System

An end-to-end AI-powered recommendation platform for SHL-style assessments that combines:
- semantic retrieval over assessment metadata,
- keyword-aware reranking,
- rule-based intent enrichment,
- and filter-aware recommendation logic for hiring use-cases.

This repository contains the backend AI engine + FastAPI layer, and references to the Colab notebooks used for dataset scraping and accuracy evaluation.

##  Key Features

- Hybrid semantic search (FAISS + Sentence Transformers + keyword overlap scoring).
- AI recommendation endpoint with business filters (`remote`, `adaptive`, `max_duration`, `language`).
- Intent-aware reranking for domain-specific job family relevance.
- Production-style API layer with health checks and CORS-enabled endpoints.
- Rebuild pipeline scripts for preprocessing and vector index regeneration.

##  System Overview

### Core Components

- "fastapi_api_layer.py" — API server with '/semantic-search' and '/recommend' routes.
- "ai/semantic_search.py" — hybrid retrieval engine with hard filtering and normalized scoring.
- "ai/recommender.py" — recommendation/reranking engine with intent and confidence logic.
- "ai/embedding_engine.py" — embedding model wrapper.
- "scripts/rebuild_index.py" — regenerate FAISS index and metadata from processed catalogue.

### High-level Flow

1. User sends a query (e.g., *“Data science”*).
2. Query is embedded and searched in FAISS vector space.
3. Retrieved items are hybrid-scored (semantic + keyword signals).
4. Optional hard filters are applied.
5. Recommender reranks for intent alignment and confidence.
6. Top-K assessments are returned via API.

## 📦 Project Structure

text
.
├── ai/
│   ├── build_index_pipeline.py
│   ├── embedding_engine.py
│   ├── recommender.py
│   ├── semantic_search.py
│   └── vector_index.py
├── data/
│   ├── raw/
│   ├── processed/
│   └── embeddings/
├── docs/
│   └── images/
├── requirements/
│   ├── api.txt
│   ├── base.txt
│   ├── dev.txt
│   └── ml.txt
├── scripts/
│   ├── preprocess.py
│   └── rebuild_index.py
└── fastapi_api_layer.py


---

## 🛠️ Setup & Run

### 1) Create environment

``bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements/base.txt
pip install -r requirements/ml.txt
pip install -r requirements/api.txt


### 2) Rebuild vector index (optional but recommended)

-bash
python scripts/rebuild_index.py


### 3) Start API

-bash
python fastapi_api_layer.py


or

-bash
uvicorn fastapi_api_layer:app --host 0.0.0.0 --port 8000 --reload


### 4) Test endpoints

- 'GET /health'
- 'POST /semantic-search'
- 'POST /recommend'



## 🌐 Colab Notebooks (Source Links)

### 1) Accuracy / Evaluation Pipeline

- Notebook link:  
  https://colab.research.google.com/drive/1Ceg0xYmdICHbBR9UMnF00XjgiSIv5ReD?usp=sharing

### 2) Dataset Scraping Pipeline

[shl_catalogue_enriched_v2.csv](https://github.com/user-attachments/files/25707970/shl_catalogue_enriched_v2.csv)


- Notebook link:  
  https://colab.research.google.com/drive/1MpHZisbbjAewx7oaqFR3-owcVVcUzRyQ?usp=sharing

---

## 📊 Pipeline Accuracy Results (Attached)

### Evaluation Dashboard
<img width="2985" height="2653" alt="shl_eval_dashboard (1)" src="https://github.com/user-attachments/assets/5833331f-a139-43f2-b2f4-c2559b582c4d" />


### Interpretation of Final Results

Based on the attached dashboard:

- Recall@K improves strongly with larger K:
  - Recall@5 ~0.79,
  - Recall@10 ~0.93.  
  Meaning: the correct answer is frequently present in the top 5–10 recommendations.

- Precision@K decreases as K increases:
  - Precision@1 is very high (~0.98),
  - Precision@3/5 remain strong,
  - Precision@10 drops (~0.61).  
  Meaning: top-ranked results are highly relevant, while lower-ranked entries add broader (less precise) coverage.

- NDCG@K is consistently very high (close to 1.0+):
  Meaning: relevant results are not only retrieved but generally ranked near the top, indicating strong ranking quality.

- Hit Rate@K is near-perfect:
  - ~0.98 at K=1 and ~1.0 for K≥3.  
  Meaning: almost every query has at least one relevant recommendation in the returned set.

- MRR distribution is concentrated near 1.0 (mean ≈ 0.99):
  Meaning: the first relevant result usually appears at rank 1 for most queries.

- Category-level performance is strong and balanced:
  Most categories show near-maximum MRR, with only slight dip in one or two segments (e.g., Leadership), suggesting good generalization with room for targeted tuning in weaker categories.

- Confidence distribution (Top-1 scores):
  Most predictions are in “good confidence” range, with a smaller tail in “fair” confidence.  
 Meaning: model confidence is generally reliable for top recommendations, while lower-confidence cases can be routed for fallback logic or human review.

### Practical Conclusion

The pipeline appears production-ready for recommendation assistance:
- excellent top-rank quality,
- very high hit coverage,
- strong retrieval depth by K=5/10.

If desired, future optimization can focus on:
1. lifting Recall@1 for harder/ambiguous queries,
2. improving underperforming categories,
3. calibrating confidence thresholds for automated vs. human-in-the-loop decisions.

---

## 🖼️ Product Screenshots

### Dashboard (Home)
<img width="1920" height="1080" alt="image" src="https://github.com/user-attachments/assets/2208db96-488e-4c16-ad58-6f0f26f96288" />


![Dashboard Home](docs/images/dashboard-home.png)

### Search Results – Java Developer
 
<img width="1920" height="1080" alt="image" src="https://github.com/user-attachments/assets/74de9893-024f-4ecc-87ba-57321a4f0558" />


<img width="1920" height="1080" alt="image" src="https://github.com/user-attachments/assets/c29d5852-9c1d-4ce9-95e4-a80e30f9d6fe" />


### Search Results – Situational Judgements
<img width="1920" height="1080" alt="image" src="https://github.com/user-attachments/assets/2470c457-d4ea-4ba6-83b9-5ec699c68a6d" />

### Search Results – Sales Manager
<img width="1920" height="1080" alt="image" src="https://github.com/user-attachments/assets/5664665d-9011-4df7-83fa-b43818bc871b" />


<img width="1920" height="1080" alt="image" src="https://github.com/user-attachments/assets/c827066c-1088-491a-802b-c6f049268a36" />


---

## 🔌 API Contract (Quick Reference)

### `POST /semantic-search`

Request body:

-json
{
  "query": "data science",
  "top_k": 10
}


### `POST /recommend`

Request body:

-json
{
  "query": "java developer",
  "top_k": 10,
  "remote": true,
  "adaptive": false,
  "max_duration": 60,
  "language": "english"
}



---

