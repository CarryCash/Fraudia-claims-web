# backend/src/api/claims.py
"""Blueprint for claims-related API endpoints.

Provides REST endpoints to:
- List all claims (with optional filters)
- Get a single claim by ID
- Evaluate a claim (run rules + ML model)
- Generate AI explanation for a claim
"""

import json
import os
import re
import sys
import uuid
from datetime import date
from pathlib import Path
from typing import Any
# pyrefly: ignore [missing-import]
from werkzeug.utils import secure_filename
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
from src.storage.relational_db import DEFAULT_DB_PATH, ensure_relational_db, open_db
from src.paths import DATA_ROOT, UPLOADS_ROOT

claims_bp = Blueprint("claims", __name__, url_prefix="/api/claims")

ALLOWED_DOC_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp"}


# ── Helper: load the processed dataset once per request context ──────────
def _load_claims_df():
    """Load the processed siniestros DataFrame."""
    # Prefer relational DB view when available (keeps dashboard/entities/reports/network consistent)
    try:
        ensure_relational_db(DEFAULT_DB_PATH)
        conn = open_db(DEFAULT_DB_PATH, write=False)
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


def _sort_claims_newest_first(records: list[dict]) -> list[dict]:
    """Put newest claims first so manual inserts appear on the dashboard."""

    def sort_key(rec: dict) -> tuple:
        fecha = rec.get("fecha_reporte") or rec.get("fecha_ocurrencia") or ""
        sid = str(rec.get("id_siniestro", ""))
        return (str(fecha), sid)

    return sorted(records, key=sort_key, reverse=True)


def _resolve_document_pdf_path(pdf_name: str, claim_id: str) -> Path | None:
    """Locate a document file in uploads or legacy raw data folders."""
    if not pdf_name or ".." in pdf_name:
        return None

    project_root = BACKEND_ROOT.parent
    candidates: list[Path] = []

    stored = Path(pdf_name)
    if stored.is_absolute() and stored.exists():
        return stored

    uploads_claim_dir = UPLOADS_ROOT / str(claim_id)
    candidates.append(uploads_claim_dir / Path(pdf_name).name)
    candidates.append(uploads_claim_dir / pdf_name)
    candidates.append(UPLOADS_ROOT / pdf_name)

    raw_dir = DATA_ROOT / "raw"
    if pdf_name.startswith(("uploads/", "uploads\\")):
        candidates.append(DATA_ROOT / pdf_name.replace("\\", "/").split("uploads/", 1)[-1])
        candidates.append(project_root / "data" / pdf_name.replace("\\", "/"))
    candidates.append(raw_dir / pdf_name)

    for path in candidates:
        if path.exists() and path.is_file():
            return path

    search_name = pdf_name.lower().strip()
    search_name_no_ext = search_name.removesuffix(".pdf").strip()

    def normalize_name(name: str) -> str:
        return "".join(ch.lower() for ch in name if ch.isalnum())

    normalized_search = normalize_name(search_name_no_ext)

    for base_dir in (uploads_claim_dir, UPLOADS_ROOT, raw_dir):
        if not base_dir.exists():
            continue
        for root, _, files in os.walk(base_dir):
            for filename in files:
                if not filename.lower().endswith(tuple(ALLOWED_DOC_EXTENSIONS)):
                    continue
                candidate = Path(root) / filename
                candidate_lower = filename.lower()
                if candidate_lower == search_name or candidate_lower == f"{search_name_no_ext}.pdf":
                    return candidate
                normalized_candidate = normalize_name(candidate_lower)
                if normalized_search and (
                    normalized_search in normalized_candidate
                    or normalized_candidate in normalized_search
                ):
                    return candidate
    return None


MANUAL_REQUIRED = [
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


def _validate_manual_body(body: dict) -> str | None:
    missing = [k for k in MANUAL_REQUIRED if not str(body.get(k, "")).strip()]
    if missing:
        return f"Campos requeridos faltantes: {', '.join(missing)}"
    try:
        monto = float(body.get("monto_reclamado"))
        if monto <= 0:
            return "monto_reclamado debe ser mayor a 0"
    except Exception:
        return "monto_reclamado inválido"
    return None


def _build_manual_row(body: dict, cols: list[str]) -> dict[str, Any]:
    docs_ok = str(body.get("documentos_completos", "Sí")).strip().lower()
    dias_entre = 0
    try:
        fo = pd.to_datetime(body.get("fecha_ocurrencia"), errors="coerce")
        fr = pd.to_datetime(body.get("fecha_reporte"), errors="coerce")
        if pd.notna(fo) and pd.notna(fr):
            dias_entre = max(0, int((fr - fo).days))
    except Exception:
        pass

    monto = float(body.get("monto_reclamado"))
    fecha_occ = pd.to_datetime(body.get("fecha_ocurrencia"), errors="coerce")
    anio_siniestro = int(fecha_occ.year) if pd.notna(fecha_occ) else date.today().year
    defaults: dict[str, Any] = {
        "monto_estimado": monto,
        "monto_pagado": 0,
        "estado": "Reserva",
        "etiqueta_fraude_simulada": 0,
        "dias_entre_ocurrencia_reporte": dias_entre,
        "proveedor_lista_restrictiva": 0,
        "dias_desde_inicio_poliza": 999,
        "dias_desde_fin_poliza": 999,
        "historial_siniestros_asegurado": 0,
        "suma_asegurada": 0,
        "narrativa_similitud_score": 0,
        "documento_alterado": 0,
        "falta_documento_obligatorio": 1 if docs_ok in ("no", "incompleto") else 0,
        "freq_asegurado_18m": 0,
        "freq_vehiculo_18m": 0,
        "freq_conductor_18m": 0,
        "freq_solo_rc_previos": 0,
        "anio_siniestro": anio_siniestro,
        "proveedor_casos_observados_anio": 0,
        "relato_ilogico": 0,
        "accidente_madrugada": 0,
        "tercero_huye_sin_camaras": 0,
        "narrativa_clonada": 0,
        "monto_cercano_suma_asegurada": 0,
        "alerta_red_fraude": 0,
    }

    row: dict[str, Any] = {}
    for col in cols:
        if col in body and body[col] is not None and str(body[col]).strip() != "":
            row[col] = body[col]
        elif col in defaults:
            row[col] = defaults[col]
    return row


def _insert_row(conn: sqlite3.Connection, table: str, row: dict[str, Any]) -> None:
    keys = list(row.keys())
    placeholders = ",".join(["?"] * len(keys))
    sql = f"INSERT INTO {table} ({','.join(keys)}) VALUES ({placeholders})"
    conn.execute(sql, tuple(row[k] for k in keys))


def _load_single_claim_row(claim_id: str) -> pd.Series:
    conn = open_db(DEFAULT_DB_PATH, write=False)
    try:
        df = pd.read_sql_query(
            "SELECT * FROM claims_enriched WHERE id_siniestro = ?",
            conn,
            params=(str(claim_id),),
        )
    finally:
        conn.close()
    if df.empty:
        raise ValueError(f"Siniestro {claim_id} no encontrado tras insertar.")
    return df.iloc[0]


def _evaluate_claim_row(row: pd.Series) -> dict[str, Any]:
    evaluation = evaluate_record(row)
    evaluation = _apply_ml_to_evaluation(row, evaluation)
    record = row.to_dict()
    record.update(evaluation)
    return record


def _persist_manual_documents(
    conn: sqlite3.Connection,
    claim_id: str,
    uploads: list,
    docs_meta: list[dict],
) -> list[dict]:
    if not uploads:
        return []

    UPLOADS_ROOT.mkdir(parents=True, exist_ok=True)
    claim_dir = UPLOADS_ROOT / str(claim_id)
    claim_dir.mkdir(parents=True, exist_ok=True)
    doc_cols = [r["name"] for r in conn.execute("PRAGMA table_info(documentos)").fetchall()]
    saved: list[dict] = []

    for i, uploaded in enumerate(uploads):
        if uploaded is None or not uploaded.filename:
            continue

        original_name = secure_filename(uploaded.filename)
        ext = Path(original_name).suffix.lower()
        if ext not in ALLOWED_DOC_EXTENSIONS:
            raise ValueError(
                f"Tipo de archivo no permitido ({original_name}). "
                f"Use: {', '.join(sorted(ALLOWED_DOC_EXTENSIONS))}"
            )

        meta = docs_meta[i] if i < len(docs_meta) else {}
        tipo_documento = str(meta.get("tipo_documento", "")).strip() or "Documento"
        observacion = meta.get("observacion")
        inconsistencia = str(meta.get("inconsistencia_detectada", "No")).strip() or "No"

        stem = re.sub(r"[^a-zA-Z0-9._-]+", "_", Path(original_name).stem)[:80] or "documento"
        stored_name = f"{stem}_{uuid.uuid4().hex[:8]}{ext}"
        dest_path = claim_dir / stored_name
        uploaded.save(str(dest_path))

        relative_path = f"{claim_id}/{stored_name}"
        doc_id = f"DOC-{uuid.uuid4().hex[:8].upper()}"
        doc_row = {c: None for c in doc_cols}
        doc_row["id_documento"] = doc_id
        doc_row["id_siniestro"] = str(claim_id)
        doc_row["tipo_documento"] = tipo_documento
        doc_row["entregado"] = "Sí"
        doc_row["legible"] = "Sí"
        doc_row["inconsistencia_detectada"] = inconsistencia
        doc_row["observacion"] = observacion or None
        doc_row["fecha_emision"] = str(date.today())
        if "archivo_pdf" in doc_cols:
            doc_row["archivo_pdf"] = relative_path

        valid = {k: v for k, v in doc_row.items() if k in doc_cols}
        _insert_row(conn, "documentos", valid)
        saved.append(_sanitize(valid))

    return saved


@claims_bp.route("/manual/complete", methods=["POST"])
def create_manual_claim_complete():
    """
    Atomically create a claim and optional document uploads in one request.

    Accepts multipart/form-data:
      - payload: JSON string with claim fields
      - docs_meta: JSON array aligned with files (optional)
      - files: zero or more document files
    """
    if request.content_type and "multipart/form-data" in request.content_type:
        raw_payload = request.form.get("payload")
        if not raw_payload:
            return jsonify({"error": "Campo 'payload' requerido."}), 400
        try:
            body = json.loads(raw_payload)
            docs_meta = json.loads(request.form.get("docs_meta") or "[]")
        except json.JSONDecodeError:
            return jsonify({"error": "JSON inválido en payload o docs_meta."}), 400
        uploads = request.files.getlist("files")
    else:
        body = request.get_json(silent=True) or {}
        docs_meta = body.pop("documentos", []) if isinstance(body.get("documentos"), list) else []
        uploads = []

    err = _validate_manual_body(body)
    if err:
        return jsonify({"error": err}), 400

    sid = str(body.get("id_siniestro")).strip()
    conn = open_db(DEFAULT_DB_PATH)
    try:
        cur = conn.execute("SELECT 1 FROM siniestros WHERE id_siniestro = ?", (sid,))
        if cur.fetchone() is not None:
            return jsonify({"error": f"Ya existe un siniestro con id_siniestro={sid}"}), 400

        cols = [r["name"] for r in conn.execute("PRAGMA table_info(siniestros)").fetchall()]
        row = _build_manual_row(body, cols)
        _insert_row(conn, "siniestros", row)
        documents = _persist_manual_documents(conn, sid, uploads, docs_meta)
        conn.commit()
    except ValueError as exc:
        conn.rollback()
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        conn.rollback()
        return jsonify({"error": f"Error al guardar siniestro: {exc}"}), 500
    finally:
        conn.close()

    try:
        claim_row = _load_single_claim_row(sid)
        record = _evaluate_claim_row(claim_row)
        record["documentos"] = documents
    except Exception as exc:
        return jsonify({
            "success": True,
            "id_siniestro": sid,
            "warning": f"Siniestro guardado, evaluación pendiente: {exc}",
        })

    return jsonify({
        "success": True,
        "id_siniestro": sid,
        "claim": _sanitize(record),
    })


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
    err = _validate_manual_body(body)
    if err:
        return jsonify({"error": err}), 400

    sid = str(body.get("id_siniestro")).strip()
    conn = open_db(DEFAULT_DB_PATH)
    try:
        cur = conn.execute("SELECT 1 FROM siniestros WHERE id_siniestro = ?", (sid,))
        if cur.fetchone() is not None:
            return jsonify({"error": f"Ya existe un siniestro con id_siniestro={sid}"}), 400

        cols = [r["name"] for r in conn.execute("PRAGMA table_info(siniestros)").fetchall()]
        row = _build_manual_row(body, cols)
        _insert_row(conn, "siniestros", row)
        conn.commit()
    except Exception as exc:
        conn.rollback()
        return jsonify({"error": f"Error al guardar siniestro: {exc}"}), 500
    finally:
        conn.close()

    try:
        claim_row = _load_single_claim_row(sid)
        record = _evaluate_claim_row(claim_row)
    except Exception:
        return jsonify({"success": True, "id_siniestro": sid})

    return jsonify({"success": True, "id_siniestro": sid, "claim": _sanitize(record)})


# ── POST /api/claims/<id>/documentos/manual ──────────────────────────────
@claims_bp.route("/<claim_id>/documentos/manual", methods=["POST"])
def create_manual_claim_documents(claim_id):
    """
    Insert documents for an existing claim into the documentos table.

    Body: JSON with:
      documentos: list of { tipo_documento, entregado, legible,
                             inconsistencia_detectada, observacion? }
    """
    body = request.get_json(silent=True) or {}
    docs_input = body.get("documentos", [])

    if not isinstance(docs_input, list) or len(docs_input) == 0:
        return jsonify({"error": "Se requiere una lista 'documentos' no vacía."}), 400

    ensure_relational_db(DEFAULT_DB_PATH)
    conn = open_db(DEFAULT_DB_PATH)
    try:
        cur = conn.execute("SELECT 1 FROM siniestros WHERE id_siniestro = ?", (str(claim_id),))
        if cur.fetchone() is None:
            return jsonify({"error": f"Siniestro {claim_id} no encontrado."}), 404

        doc_cols = [r["name"] for r in conn.execute("PRAGMA table_info(documentos)").fetchall()]

        inserted = 0
        for doc in docs_input:
            doc_id = doc.get("id_documento") or f"DOC-{uuid.uuid4().hex[:8].upper()}"
            row = {c: None for c in doc_cols}
            row["id_documento"] = doc_id
            row["id_siniestro"] = str(claim_id)
            row["tipo_documento"] = str(doc.get("tipo_documento", "")).strip()
            row["entregado"] = str(doc.get("entregado", "Sí"))
            row["legible"] = str(doc.get("legible", "Sí"))
            row["inconsistencia_detectada"] = str(doc.get("inconsistencia_detectada", "No"))
            row["observacion"] = doc.get("observacion") or None
            row["fecha_emision"] = str(date.today())
            if "archivo_pdf" in doc_cols and doc.get("archivo_pdf"):
                row["archivo_pdf"] = str(doc.get("archivo_pdf")).strip()

            # Filter to only existing columns
            valid = {k: v for k, v in row.items() if k in doc_cols}
            keys = list(valid.keys())
            placeholders = ",".join(["?"] * len(keys))
            sql = f"INSERT OR IGNORE INTO documentos ({','.join(keys)}) VALUES ({placeholders})"
            conn.execute(sql, tuple(valid[k] for k in keys))
            inserted += 1

        conn.commit()
        return jsonify({"success": True, "inserted": inserted})
    finally:
        conn.close()


# ── POST /api/claims/validate-document ─────────────────────────────
@claims_bp.route("/validate-document", methods=["POST"])
def validate_document():
    """Validate a document using Gemini AI to cross-check dates, amounts, and names."""
    uploaded = request.files.get("file")
    if uploaded is None or not uploaded.filename:
        return jsonify({"error": "Se requiere un archivo PDF en el campo 'file'."}), 400

    ext = Path(uploaded.filename).suffix.lower()
    if ext != ".pdf":
        return jsonify({"error": "Solo se soportan archivos PDF para la validación con IA."}), 400

    claim_data_str = request.form.get("claim_data", "{}")
    try:
        claim_data = json.loads(claim_data_str)
    except json.JSONDecodeError:
        return jsonify({"error": "claim_data inválido."}), 400

    from src.ai_agent.pdf_validator import validate_pdf_with_gemini
    result = validate_pdf_with_gemini(uploaded, claim_data)
    
    return jsonify(result)

# ── POST /api/claims/<id>/documentos/upload ─────────────────────────────
@claims_bp.route("/<claim_id>/documentos/upload", methods=["POST"])
def upload_claim_document(claim_id):
    """Upload a real document file and attach it to a claim."""
    uploaded = request.files.get("file")
    if uploaded is None or not uploaded.filename:
        return jsonify({"error": "Se requiere un archivo en el campo 'file'."}), 400

    original_name = secure_filename(uploaded.filename)
    ext = Path(original_name).suffix.lower()
    if ext not in ALLOWED_DOC_EXTENSIONS:
        return jsonify({"error": f"Tipo de archivo no permitido. Use: {', '.join(sorted(ALLOWED_DOC_EXTENSIONS))}"}), 400

    tipo_documento = str(request.form.get("tipo_documento", "")).strip() or "Documento"
    observacion = request.form.get("observacion")
    inconsistencia = str(request.form.get("inconsistencia_detectada", "No")).strip() or "No"

    ensure_relational_db(DEFAULT_DB_PATH)
    conn = open_db(DEFAULT_DB_PATH)
    try:
        cur = conn.execute("SELECT 1 FROM siniestros WHERE id_siniestro = ?", (str(claim_id),))
        if cur.fetchone() is None:
            return jsonify({"error": f"Siniestro {claim_id} no encontrado."}), 404

        claim_dir = UPLOADS_ROOT / str(claim_id)
        claim_dir.mkdir(parents=True, exist_ok=True)

        stem = re.sub(r"[^a-zA-Z0-9._-]+", "_", Path(original_name).stem)[:80] or "documento"
        stored_name = f"{stem}_{uuid.uuid4().hex[:8]}{ext}"
        dest_path = claim_dir / stored_name
        uploaded.save(str(dest_path))

        relative_path = f"{claim_id}/{stored_name}"
        doc_id = f"DOC-{uuid.uuid4().hex[:8].upper()}"
        doc_cols = [r["name"] for r in conn.execute("PRAGMA table_info(documentos)").fetchall()]
        row = {c: None for c in doc_cols}
        row["id_documento"] = doc_id
        row["id_siniestro"] = str(claim_id)
        row["tipo_documento"] = tipo_documento
        row["entregado"] = "Sí"
        row["legible"] = "Sí"
        row["inconsistencia_detectada"] = inconsistencia
        row["observacion"] = observacion or None
        row["fecha_emision"] = str(date.today())
        if "archivo_pdf" in doc_cols:
            row["archivo_pdf"] = relative_path

        valid = {k: v for k, v in row.items() if k in doc_cols}
        keys = list(valid.keys())
        placeholders = ",".join(["?"] * len(keys))
        sql = f"INSERT INTO documentos ({','.join(keys)}) VALUES ({placeholders})"
        conn.execute(sql, tuple(valid[k] for k in keys))
        conn.commit()

        return jsonify({
            "success": True,
            "id_documento": doc_id,
            "archivo_pdf": relative_path,
            "tipo_documento": tipo_documento,
        })
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

    results = _sort_claims_newest_first(results)

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
        return jsonify({"error": "El documento no tiene un archivo asociado."}), 404

    pdf_path = _resolve_document_pdf_path(pdf_name, str(claim_id))
    if pdf_path is None or not pdf_path.exists():
        return jsonify({"error": f"Archivo no encontrado: {pdf_name}"}), 404

    ext = pdf_path.suffix.lower()
    mime = "application/pdf"
    if ext in {".png"}:
        mime = "image/png"
    elif ext in {".jpg", ".jpeg"}:
        mime = "image/jpeg"
    elif ext == ".webp":
        mime = "image/webp"

    return send_file(pdf_path, mimetype=mime, as_attachment=False)


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


# ── DELETE /api/claims/<id> ───────────────────────────────────────────────────
@claims_bp.route("/<claim_id>", methods=["DELETE"])
def delete_claim(claim_id):
    """Permanently delete a claim and all its associated documents.

    Body (optional JSON):
        motivo (str) – reason for deletion (for logging purposes)
    """
    body = request.get_json(silent=True) or {}
    motivo = str(body.get("motivo", "")).strip() or "No especificado"

    ensure_relational_db(DEFAULT_DB_PATH)
    conn = open_db(DEFAULT_DB_PATH)
    try:
        cur = conn.execute(
            "SELECT 1 FROM siniestros WHERE id_siniestro = ?", (str(claim_id),)
        )
        if cur.fetchone() is None:
            return jsonify({"error": f"Siniestro {claim_id} no encontrado."}), 404

        # Delete associated documents first (FK-style cleanup)
        conn.execute(
            "DELETE FROM documentos WHERE id_siniestro = ?", (str(claim_id),)
        )
        # Delete the claim itself
        conn.execute(
            "DELETE FROM siniestros WHERE id_siniestro = ?", (str(claim_id),)
        )
        conn.commit()
    except Exception as exc:
        conn.rollback()
        return jsonify({"error": f"Error al eliminar siniestro: {exc}"}), 500
    finally:
        conn.close()

    return jsonify({
        "success": True,
        "id_siniestro": claim_id,
        "motivo": motivo,
    })


# ── Private helpers ──────────────────────────────────────────────────────────


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
