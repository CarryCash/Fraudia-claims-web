import os
import sys
import traceback
from datetime import datetime
# pyrefly: ignore [missing-import]
from flask import Blueprint, jsonify, request
from src.integrations.notion_client import create_report_page
from src.api.reports import get_report_stats

notion_bp = Blueprint("notion", __name__, url_prefix="/api/notion")

@notion_bp.route("/export", methods=["POST"])
def export_to_notion():
    try:
        data = request.json or {}
        claims = data.get("claims", [])
        
        parent_page_id = os.environ.get("NOTION_PAGE_ID")
        if not parent_page_id:
            return jsonify({"error": "NOTION_PAGE_ID no está configurado."}), 500

        # Obtener los KPIs actuales usando la misma lógica que los reportes
        # Para esto llamamos a la función subyacente o hacemos fetch
        # Como get_report_stats es una vista de Flask, extraemos su response JSON
        stats_response = get_report_stats()
        stats_data = stats_response.get_json() if hasattr(stats_response, 'get_json') else {}

        if "error" in stats_data:
            stats_data = {"ahorro_potencial": 0, "monto_total": 0}

        title = f"Reporte Ejecutivo Fraudia - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        notion_url = create_report_page(
            parent_page_id=parent_page_id,
            title=title,
            stats=stats_data,
            claims=claims
        )
        
        return jsonify({"success": True, "url": notion_url})

    except Exception as e:
        print(f"Error exporting to notion: {e}", file=sys.stderr)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
