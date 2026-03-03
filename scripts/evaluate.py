"""
evaluate.py  — Drop-in replacement for your evaluate.py
Computes Mean Recall@10 on the train set and shows per-query breakdown.
"""

import os
import sys
import pandas as pd
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ai.recommender import RecommenderEngine
engine = RecommenderEngine()
# Path to train set Excel
DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "Gen_AI_Dataset.xlsx")
if not os.path.exists(DATA_PATH):
    DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "Gen_AI_Dataset.xlsx")
if not os.path.exists(DATA_PATH):
    DATA_PATH = "data/Gen_AI_Dataset.xlsx"

URL_PREFIX_SOLUTION = "https://www.shl.com/solutions/products/product-catalog/view/"
URL_PREFIX_PRODUCT  = "https://www.shl.com/products/product-catalog/view/"


def normalize_url(url: str) -> str:
    url = str(url).strip().rstrip("/")
    # Unify both prefixes to a canonical slug
    for prefix in [URL_PREFIX_SOLUTION, URL_PREFIX_PRODUCT]:
        if url.startswith(prefix):
            return url[len(prefix):]
    return url.lower()


def recall_at_k(predicted_urls: list, relevant_urls: list, k: int = 10) -> float:
    if not relevant_urls:
        return 0.0
    pred_slugs = [normalize_url(u) for u in predicted_urls[:k]]
    rel_slugs  = [normalize_url(u) for u in relevant_urls]
    hits = sum(1 for u in rel_slugs if u in pred_slugs)
    return hits / len(rel_slugs)


def evaluate(k: int = 10, verbose: bool = True):
    xl = pd.ExcelFile(DATA_PATH)
    train = xl.parse("Train-Set")

    # Group by query
    grouped = train.groupby("Query")["Assessment_url"].apply(list).reset_index()
    recalls = []

    for _, row in grouped.iterrows():
        query = row["Query"]
        relevant = row["Assessment_url"]

        results = engine.recommend(query, top_k=10)
        pred_urls = [p["url"] for p in results]

        rc = recall_at_k(pred_urls, relevant, k)
        recalls.append(rc)

        if verbose:
            short_q = query[:70].replace("\n", " ")
            print(f"Recall@{k}: {rc:.2f} | {short_q}...")
            if rc < 1.0:
                # Show which were missed
                pred_slugs = set(normalize_url(u) for u in pred_urls)
                for rel_url in relevant:
                    slug = normalize_url(rel_url)
                    mark = "✓" if slug in pred_slugs else "✗"
                    print(f"  {mark} {rel_url}")

    mean_recall = sum(recalls) / len(recalls)
    max_achievable = 1.0  # all relevant are in catalogue (ideally)

    print(f"\n{'='*50}")
    print(f"Mean Recall@{k}: {mean_recall:.4f}")
    print(f"Num queries evaluated: {len(recalls)}")
    return mean_recall


if __name__ == "__main__":
    k = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    evaluate(k=k, verbose=True)