import os
import json
import urllib.request
import urllib.error
from typing import List, Dict, Any

NOTION_API_URL = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


def get_notion_headers() -> Dict[str, str]:
    api_key = os.environ.get("NOTION_API_KEY")
    if not api_key:
        raise ValueError("NOTION_API_KEY no está configurado en las variables de entorno.")
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION
    }


def _text_prop(value: str) -> dict:
    """Build a rich_text property."""
    return {"rich_text": [{"type": "text", "text": {"content": str(value or "")}}]}


def _title_prop(value: str) -> dict:
    """Build a title property."""
    return {"title": [{"type": "text", "text": {"content": str(value or "")}}]}


def _select_prop(value: str) -> dict:
    """Build a select property."""
    v = str(value or "").strip()
    if not v:
        return {"select": None}
    return {"select": {"name": v}}


def _number_prop(value) -> dict:
    """Build a number property."""
    try:
        return {"number": float(value)}
    except (TypeError, ValueError):
        return {"number": None}


def _date_prop(value: str) -> dict:
    """Build a date property. Expects YYYY-MM-DD or similar."""
    v = str(value or "").strip()
    if not v or v.lower() in ("nan", "none", "nat"):
        return {"date": None}
    # Take only the date part (first 10 chars)
    return {"date": {"start": v[:10]}}


def _checkbox_prop(value) -> dict:
    """Build a checkbox property."""
    if isinstance(value, bool):
        return {"checkbox": value}
    return {"checkbox": bool(value)}


def _build_row_properties(claim: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map a claim dict to Notion database properties.
    Matches the user's database schema exactly.
    """
    return {
        "id_siniestro": _title_prop(claim.get("id_siniestro", "")),
        "id_poliza": _text_prop(claim.get("id_poliza", "")),
        "id_asegurado": _text_prop(claim.get("id_asegurado", "")),
        "ramo": _select_prop(claim.get("ramo", "")),
        "cobertura": _select_prop(claim.get("cobertura", "")),
        "fecha_ocurrencia": _date_prop(claim.get("fecha_ocurrencia", "")),
        "fecha_reporte": _date_prop(claim.get("fecha_reporte", "")),
        "monto_reclamado": _number_prop(claim.get("monto_reclamado", 0)),
        "monto_estimado": _number_prop(claim.get("monto_estimado", 0)),
        "sucursal": _select_prop(claim.get("sucursal", "")),
        "beneficiario": _text_prop(claim.get("beneficiario", "")),
        "estado": _select_prop(claim.get("estado", "")),
        "descripcion": _text_prop(str(claim.get("descripcion", ""))[:2000]),
        "final_score": _number_prop(claim.get("final_score", 0)),
        "final_color": _select_prop(claim.get("final_color", "")),
        "soft_score": _number_prop(claim.get("soft_score", 0)),
        "hard_score": _number_prop(claim.get("hard_score", 0)),
        "ml_probability": _number_prop(claim.get("ml_probability", 0)),
        "is_anomaly": _checkbox_prop(claim.get("is_anomaly", False)),
        "combined_score": _number_prop(claim.get("combined_score", 0)),
    }


def insert_claims_to_database(database_id: str, claims: List[Dict[str, Any]]) -> int:
    """
    Insert claim rows into a Notion database.
    Returns the number of rows successfully inserted.
    """
    headers = get_notion_headers()
    inserted = 0

    for claim in claims:
        properties = _build_row_properties(claim)

        payload = {
            "parent": {"type": "database_id", "database_id": database_id},
            "properties": properties,
        }

        req = urllib.request.Request(
            f"{NOTION_API_URL}/pages",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        try:
            with urllib.request.urlopen(req) as response:
                response.read()
                inserted += 1
        except urllib.error.HTTPError as e:
            error_info = e.read().decode()
            print(f"Notion insert error for {claim.get('id_siniestro', '?')}: {e.code} - {error_info}")
            # Continue with the rest instead of failing entirely
            continue

    return inserted
