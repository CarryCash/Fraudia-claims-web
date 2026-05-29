# backend/src/api/claims.py
"""Blueprint for claims-related API endpoints.

Provides REST endpoints to:
- List all claims (with optional filters)
- Get a single claim by ID
- Evaluate a claim (run rules + ML model)
- Generate AI explanation for a claim
"""

import os
import sys
from pathlib import Path
from typing import Any
# pyrefly: ignore [missing-import]
import sqlite3
# pyrefly: ignore [missing-import]
import pandas as pd
# pyrefly: ignore [missing-import]
from flask import Blueprint, jsonify, request, send_file

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
from src.explainability.explain_score import combine_scores, generate_explanation, _predict_ml
from src.storage.relational_db import DEFAULT_DB_PATH, ensure_relational_db

claims_bp = Blueprint("claims", __name__, url_prefix="/api/claims")


# ── Helper: load the processed dataset once per request context ──────────
def _load_claims_df():
    """Load the processed siniestros DataFrame."""
    # Prefer relational DB view when available (keeps dashboard/entities/reports/network consistent)
    try:
        ensure_relational_db(DEFAULT_DB_PATH)
        conn = sqlite3.connect(DEFAULT_DB_PATH)
        try:
            df_rel = pd.read_sql_query("SELECT * FROM claims_enriched", conn)
        finally:
            conn.close()
        if not df_rel.empty:
            return df_rel
    except Exception:
        pass
    try:
        return load_siniestros(processed=True)
    except FileNotFoundError:
        return load_siniestros(processed=False)

def _apply_ml_to_evaluation(row, evaluation):
    """Run ML prediction and merge into the rules evaluation."""
    ml_prob, is_anomaly = _predict_ml(row)
    
    if is_anomaly:
        # Append alert if not already present
        alert_msg = "Alerta de ML: Comportamiento Atípico (Isolation Forest)"
        if alert_msg not in evaluation.get("soft_alerts", []):
            evaluation.setdefault("soft_alerts", []).append(alert_msg)
            evaluation["soft_score"] = min(evaluation.get("soft_score", 0) + 15, 100)
            
    total_score = combine_scores(evaluation.get("soft_score", 0), ml_prob)
    evaluation["ml_probability"] = ml_prob
    evaluation["is_anomaly"] = is_anomaly
    evaluation["combined_score"] = total_score
    
    # Overwrite final_score and final_color for the frontend
    current_final = evaluation.get("final_score", 0)
    new_final = max(current_final, total_score)
    evaluation["final_score"] = new_final
    
    if new_final >= 80:
        evaluation["final_color"] = "rojo"
    elif new_final >= 50:
        evaluation["final_color"] = "amarillo"
    else:
        evaluation["final_color"] = "verde"
        
    return evaluation


@claims_bp.route("/manual", methods=["POST"])
def create_manual_claim():
    """
    Insert a new claim manually into the relational DB.

    Body: JSON with at least:
      id_siniestro, id_poliza, id_asegurado, ramo, cobertura,
      fecha_ocurrencia, fecha_reporte, monto_reclamado, sucursal,
      descripcion, beneficiario, documentos_completos
    """
    body = request.get_json(silent=True) or {}
    required = [
        "id_siniestro",
        "id_poliza",
        "id_asegurado",
        "ramo",
        "cobertura",
        "fecha_ocurrencia",
        "fecha_reporte",
        "monto_reclamado",
        "sucursal",
        "descripcion",
        "beneficiario",
        "documentos_completos",
    ]
    missing = [k for k in required if not str(body.get(k, "")).strip()]
    if missing:
        return jsonify({"error": f"Campos requeridos faltantes: {', '.join(missing)}"}), 400

    # Basic validations
    try:
        monto = float(body.get("monto_reclamado"))
        if monto <= 0:
            return jsonify({"error": "monto_reclamado debe ser mayor a 0"}), 400
    except Exception:
        return jsonify({"error": "monto_reclamado inválido"}), 400

    ensure_relational_db(DEFAULT_DB_PATH)
    conn = sqlite3.connect(DEFAULT_DB_PATH)
    try:
        conn.row_factory = sqlite3.Row
        sid = str(body.get("id_siniestro")).strip()
        # ensure uniqueness
        cur = conn.execute("SELECT 1 FROM siniestros WHERE id_siniestro = ?", (sid,))
        if cur.fetchone() is not None:
            return jsonify({"error": f"Ya existe un siniestro con id_siniestro={sid}"}), 400

        # Insert using current table columns (ignore unknown keys)
        cols = [r["name"] for r in conn.execute("PRAGMA table_info(siniestros)").fetchall()]
        row = {c: body.get(c) for c in cols if c in body}

        # Fill optional defaults
        row.setdefault("monto_estimado", row.get("monto_reclamado"))
        row.setdefault("monto_pagado", 0)
        row.setdefault("estado", "Reserva")
        row.setdefault("etiqueta_fraude_simulada", 0)

        keys = list(row.keys())
        placeholders = ",".join(["?"] * len(keys))
        sql = f"INSERT INTO siniestros ({','.join(keys)}) VALUES ({placeholders})"
        conn.execute(sql, tuple(row[k] for k in keys))
        conn.commit()
        return jsonify({"success": True, "id_siniestro": sid})
    finally:
        conn.close()


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

    from src.explainability.explain_score import _bulk_predict_ml
    ml_probs, is_anomalies = _bulk_predict_ml(df)

    results = []
    for i, (idx, row) in enumerate(df.iterrows()):
        evaluation = evaluate_record(row)
        
        # Override with precomputed ML predictions
        ml_prob = float(ml_probs[i])
        is_anomaly = bool(is_anomalies[i])
        
        if is_anomaly:
            alert_msg = "Alerta de ML: Comportamiento Atípico (Isolation Forest)"
            if alert_msg not in evaluation.get("soft_alerts", []):
                evaluation.setdefault("soft_alerts", []).append(alert_msg)
                evaluation["soft_score"] = min(evaluation.get("soft_score", 0) + 15, 100)
                
        total_score = combine_scores(evaluation.get("soft_score", 0), ml_prob)
        evaluation["ml_probability"] = ml_prob
        evaluation["is_anomaly"] = is_anomaly
        evaluation["combined_score"] = total_score
        
        current_final = evaluation.get("final_score", 0)
        new_final = max(current_final, total_score)
        evaluation["final_score"] = new_final
        
        if new_final >= 80:
            evaluation["final_color"] = "rojo"
        elif new_final >= 50:
            evaluation["final_color"] = "amarillo"
        else:
            evaluation["final_color"] = "verde"

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
    evaluation = _apply_ml_to_evaluation(row, evaluation)
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
    evaluation = _apply_ml_to_evaluation(row, evaluation)

    return jsonify(evaluation)


# ── GET /api/claims/<id>/documentos/<doc_id>/preview ────────────────────────────────────
@claims_bp.route("/<claim_id>/documentos/<doc_id>/preview", methods=["GET"])
def preview_claim_document(claim_id, doc_id):
    """Return the raw PDF referenced by a claim document."""
    try:
        df_docs = load_documentos()
    except FileNotFoundError as exc:
        return jsonify({"error": str(exc)}), 404

    claim_docs = df_docs[
        (df_docs["id_siniestro"].astype(str) == str(claim_id)) &
        (df_docs["id_documento"].astype(str) == str(doc_id))
    ]
    if claim_docs.empty:
        return jsonify({"error": "Documento no encontrado para este siniestro."}), 404

    pdf_name = str(claim_docs.iloc[0].get("archivo_pdf", "")).strip()
    if not pdf_name:
        return jsonify({"error": "El documento no tiene un archivo PDF asociado."}), 404

    if ".." in pdf_name or pdf_name.startswith(("/", "\\")):
        return jsonify({"error": "Nombre de archivo inválido."}), 400

    project_root = BACKEND_ROOT.parent
    raw_dir = project_root / "data" / "raw"

    def normalize_name(name: str) -> str:
        return "".join(ch.lower() for ch in name if ch.isalnum())

    search_name = pdf_name.lower().strip()
    search_name_no_ext = search_name.removesuffix('.pdf').strip()
    normalized_search = normalize_name(search_name_no_ext)

    pdf_path = None
    for root, _, files in os.walk(raw_dir):
        for filename in files:
            if not filename.lower().endswith('.pdf'):
                continue
            candidate = filename.strip()
            if candidate == pdf_name:
                pdf_path = Path(root) / candidate
                break

            candidate_lower = candidate.lower()
            if search_name_no_ext and candidate_lower == f"{search_name_no_ext}.pdf":
                pdf_path = Path(root) / candidate
                break

            normalized_candidate = normalize_name(candidate_lower)
            if normalized_search and normalized_search in normalized_candidate:
                pdf_path = Path(root) / candidate
                break

            if normalized_search and normalized_candidate in normalized_search:
                pdf_path = Path(root) / candidate
                break

        if pdf_path is not None:
            break

    if pdf_path is None or not pdf_path.exists():
        return jsonify({"error": f"PDF no encontrado: {pdf_name}"}), 404

    return send_file(pdf_path, mimetype="application/pdf", as_attachment=False)


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
    evaluation = _apply_ml_to_evaluation(row, evaluation)
        
    explanation = generate_explanation(
        claim=row.to_dict(),
        rule_score=evaluation["soft_score"],
        ml_prob=evaluation["ml_probability"],
        alerts=evaluation["soft_alerts"],
        is_anomaly=evaluation["is_anomaly"]
    )

    return jsonify({
        "id_siniestro": claim_id,
        "explanation": explanation,
        "combined_score": evaluation["combined_score"],
    })


# ── Private helpers ──────────────────────────────────────────────────────


def _sanitize(obj: Any) -> Any:
    """Recursively convert NaN / Timestamps / Numpy types to JSON-safe values."""
    import math
    import numpy as np
    
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    elif isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    elif isinstance(obj, (np.integer, int)):
        return int(obj)
    elif isinstance(obj, (np.floating, float)):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return float(obj)
    elif hasattr(obj, "isoformat"):
        return obj.isoformat()
    elif pd.isna(obj):
        return None
    else:
        return obj


def _sanitize_list(records: list) -> list:
    return [_sanitize(r) for r in records]
