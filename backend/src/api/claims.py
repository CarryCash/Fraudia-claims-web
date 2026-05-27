# backend/src/api/claims.py
"""Blueprint for claims-related API endpoints.

Provides REST endpoints to:
- List all claims (with optional filters)
- Get a single claim by ID
- Evaluate a claim (run rules + ML model)
- Generate AI explanation for a claim
"""

import sys
from pathlib import Path
# pyrefly: ignore [missing-import]
from flask import Blueprint, jsonify, request

# Ensure the backend root is on sys.path so relative imports work
BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from src.ingestion.load_data import (
    load_siniestros,
    load_polizas,
    load_asegurados,
    load_proveedores,
    load_documentos,
)
from src.rules.fraud_rules import evaluate_record
from src.explainability.explain_score import combine_scores, generate_explanation

claims_bp = Blueprint("claims", __name__, url_prefix="/api/claims")


# ── Helper: load the processed dataset once per request context ──────────
def _load_claims_df():
    """Load the processed siniestros DataFrame."""
    try:
        return load_siniestros(processed=True)
    except FileNotFoundError:
        return load_siniestros(processed=False)


# ── GET /api/claims ──────────────────────────────────────────────────────
@claims_bp.route("", methods=["GET"])
def list_claims():
    """Return a paginated list of claims.

    Query params:
        page  (int, default 1)
        limit (int, default 20)
        color (str, optional) – filter by final semaphore colour
    """
    try:
        df = _load_claims_df()
    except FileNotFoundError as exc:
        return jsonify({"error": str(exc)}), 404

    # Optional colour filter
    color_filter = request.args.get("color")

    # Evaluate all records so we can filter/sort by score
    results = []
    for _, row in df.iterrows():
        evaluation = evaluate_record(row)
        if color_filter and evaluation["final_color"] != color_filter:
            continue
        record = row.to_dict()
        record.update(evaluation)
        results.append(record)

    # Pagination
    page = int(request.args.get("page", 1))
    limit = int(request.args.get("limit", 20))
    start = (page - 1) * limit
    end = start + limit
    paginated = results[start:end]

    return jsonify({
        "total": len(results),
        "page": page,
        "limit": limit,
        "data": _sanitize_list(paginated),
    })


# ── GET /api/claims/<id> ────────────────────────────────────────────────
@claims_bp.route("/<claim_id>", methods=["GET"])
def get_claim(claim_id):
    """Return a single claim together with its fraud evaluation."""
    try:
        df = _load_claims_df()
    except FileNotFoundError as exc:
        return jsonify({"error": str(exc)}), 404

    match = df[df["id_siniestro"].astype(str) == str(claim_id)]
    if match.empty:
        return jsonify({"error": f"Claim {claim_id} not found"}), 404

    row = match.iloc[0]
    evaluation = evaluate_record(row)
    record = row.to_dict()
    record.update(evaluation)

    # Load related documents from DB
    documents = []
    try:
        df_docs = load_documentos()
        if not df_docs.empty and "id_siniestro" in df_docs.columns:
            claim_docs = df_docs[df_docs["id_siniestro"].astype(str) == str(claim_id)]
            for _, d_row in claim_docs.iterrows():
                documents.append(_sanitize(d_row.to_dict()))
    except Exception:
        pass
    record["documentos"] = documents

    return jsonify(_sanitize(record))


# ── POST /api/claims/<id>/evaluate ───────────────────────────────────────
@claims_bp.route("/<claim_id>/evaluate", methods=["POST"])
def evaluate_claim(claim_id):
    """Run the full evaluation pipeline (rules + ML) on a single claim."""
    try:
        df = _load_claims_df()
    except FileNotFoundError as exc:
        return jsonify({"error": str(exc)}), 404

    match = df[df["id_siniestro"].astype(str) == str(claim_id)]
    if match.empty:
        return jsonify({"error": f"Claim {claim_id} not found"}), 404

    row = match.iloc[0]
    evaluation = evaluate_record(row)

    # Attempt ML prediction
    ml_prob = _predict_ml(row)

    total_score = combine_scores(evaluation["soft_score"], ml_prob)
    evaluation["ml_probability"] = ml_prob
    evaluation["combined_score"] = total_score

    return jsonify(evaluation)


# ── POST /api/claims/<id>/explain ────────────────────────────────────────
@claims_bp.route("/<claim_id>/explain", methods=["POST"])
def explain_claim(claim_id):
    """Generate an AI-powered explanation for a claim's risk score."""
    try:
        df = _load_claims_df()
    except FileNotFoundError as exc:
        return jsonify({"error": str(exc)}), 404

    match = df[df["id_siniestro"].astype(str) == str(claim_id)]
    if match.empty:
        return jsonify({"error": f"Claim {claim_id} not found"}), 404

    row = match.iloc[0]
    evaluation = evaluate_record(row)
    ml_prob = _predict_ml(row)
    explanation = generate_explanation(
        claim=row.to_dict(),
        rule_score=evaluation["soft_score"],
        ml_prob=ml_prob,
        alerts=evaluation["soft_alerts"],
    )

    return jsonify({
        "id_siniestro": claim_id,
        "explanation": explanation,
        "combined_score": combine_scores(evaluation["soft_score"], ml_prob),
    })


# ── Private helpers ──────────────────────────────────────────────────────
def _predict_ml(row) -> float:
    """Return the ML model's fraud probability for a single row."""
    try:
        import joblib
        import numpy as np

        model_path = BACKEND_ROOT / "models" / "random_forest_fraud.joblib"
        features_path = BACKEND_ROOT / "models" / "features.joblib"

        if not model_path.exists():
            return 0.0

        model = joblib.load(model_path)
        features = joblib.load(features_path)

        X = np.array([[float(row.get(f, 0) or 0) for f in features]])
        prob = model.predict_proba(X)[0][1]
        return round(float(prob), 4)
    except Exception:
        return 0.0


def _sanitize(record: dict) -> dict:
    """Convert NaN / Timestamps to JSON-safe values."""
    import math
    clean = {}
    for k, v in record.items():
        if isinstance(v, float) and math.isnan(v):
            clean[k] = None
        elif hasattr(v, "isoformat"):
            clean[k] = v.isoformat()
        else:
            clean[k] = v
    return clean


def _sanitize_list(records: list) -> list:
    return [_sanitize(r) for r in records]
