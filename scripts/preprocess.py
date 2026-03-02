import pandas as pd
import json
import os
from datetime import datetime
from typing import List, Dict

RAW_PATH = "data/raw/shl_catalogue.csv"
OUT_PATH = "data/processed/processed_catalogue.json"

PIPE = "|"


def safe_split(value: str) -> List[str]:
    if pd.isna(value) or value is None or str(value).strip() == "":
        return []
    return [v.strip() for v in str(value).split(PIPE)]


def safe_bool(value):
    if isinstance(value, bool):
        return value
    if pd.isna(value):
        return False
    v = str(value).strip().upper()
    return v in ["TRUE", "1", "YES", "Y"]


def safe_int(value):
    try:
        if pd.isna(value) or value == "":
            return None
        return int(float(value))
    except:
        return None


def safe_float(value):
    try:
        if pd.isna(value) or value == "":
            return None
        return float(value)
    except:
        return None


def safe_date(value):
    if pd.isna(value) or value == "":
        return None
    try:
        return datetime.strptime(str(value), "%d-%m-%Y").date().isoformat()
    except:
        return None


def build_text_for_embedding(row: Dict) -> str:
    parts = [
        row.get("name", ""),
        row.get("type", ""),
        " ".join(row.get("test_type_labels", [])),
        row.get("job_family", ""),
        " ".join(row.get("job_levels", [])),
        " ".join(row.get("industry", [])),
        row.get("description", ""),
        " ".join(row.get("use_cases", [])),
        " ".join(row.get("keywords", [])),
        " ".join(row.get("skill_ids", [])),
        " ".join(row.get("cognitive_domain_ids", [])),
        " ".join(row.get("ucf_competency_cluster_ids", [])),
    ]
    return " ".join([p for p in parts if p])


def main():
    if not os.path.exists(RAW_PATH):
        raise FileNotFoundError(f"CSV not found at {RAW_PATH}")

    print("Loading CSV...")
    df = pd.read_csv(RAW_PATH)

    print("Rows loaded:", len(df))

    processed = []

    for _, row in df.iterrows():
        record = {
            "id": int(row["id"]),
            "name": str(row["name"]).strip(),
            "type": str(row["type"]).strip(),

            "test_type_codes": safe_split(row.get("test_type_codes")),
            "test_type_labels": safe_split(row.get("test_type_labels")),

            "job_family": str(row.get("job_family")).strip() if not pd.isna(row.get("job_family")) else None,
            "job_levels": safe_split(row.get("job_levels")),
            "industry": safe_split(row.get("industry")),

            "remote_testing": safe_bool(row.get("remote_testing")),
            "adaptive_irt": safe_bool(row.get("adaptive_irt")),

            "duration_minutes": safe_int(row.get("duration_minutes")),
            "description": str(row.get("description")).strip() if not pd.isna(row.get("description")) else "",

            "languages": safe_split(row.get("languages")),
            "url": str(row.get("url")).strip(),

            "use_cases": safe_split(row.get("use_cases")),
            "keywords": safe_split(row.get("keywords")),

            # Ontology IDs
            "job_family_id": row.get("job_family_id"),
            "job_level_ids": safe_split(row.get("job_level_ids")),
            "sub_industry_ids": safe_split(row.get("sub_industry_ids")),
            "skill_ids": safe_split(row.get("skill_ids")),
            "cognitive_domain_ids": safe_split(row.get("cognitive_domain_ids")),
            "ucf_competency_cluster_ids": safe_split(row.get("ucf_competency_cluster_ids")),

            # Delivery & accessibility
            "delivery_proctoring_id": row.get("delivery_proctoring_id"),
            "delivery_bandwidth_id": row.get("delivery_bandwidth_id"),
            "delivery_device_ids": safe_split(row.get("delivery_device_ids")),
            "accessibility_flags": safe_split(row.get("accessibility_flags")),

            # Governance & trust
            "confidence_score": safe_float(row.get("confidence_score")),
            "confidence_band": row.get("confidence_band"),
            "schema_version": row.get("schema_version"),

            "effective_from": safe_date(row.get("effective_from")),
            "valid_until": safe_date(row.get("valid_until")),
            "lifecycle_status": row.get("lifecycle_status"),

            "gdpr_compliant": safe_bool(row.get("gdpr_compliant")),
            "bias_audit_required": safe_bool(row.get("bias_audit_required")),
            "right_to_explanation": safe_bool(row.get("right_to_explanation")),
        }

        # AI embedding field
        record["text_for_embedding"] = build_text_for_embedding(record)

        processed.append(record)

    os.makedirs("data/processed", exist_ok=True)

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(processed, f, indent=2, ensure_ascii=False)

    print("Processed catalogue saved to:", OUT_PATH)
    print("Total processed records:", len(processed))


if __name__ == "__main__":
    main()