import os
import sys
import traceback
from datetime import datetime
# pyrefly: ignore [missing-import]
from flask import Blueprint, jsonify, request
from src.integrations.notion_client import insert_claims_to_database

notion_bp = Blueprint("notion", __name__, url_prefix="/api/notion")

@notion_bp.route("/export", methods=["POST"])
def export_to_notion():
    try:
        data = request.json or {}
        claims = data.get("claims", [])

        database_id = os.environ.get("NOTION_DATABASE_ID")
        if not database_id:
            return jsonify({"error": "NOTION_DATABASE_ID no está configurado en .env"}), 500

        if not claims:
            return jsonify({"error": "No hay siniestros para exportar."}), 400

        inserted = insert_claims_to_database(database_id, claims)

        # Build the Notion database URL for the user
        clean_id = database_id.replace("-", "")
        notion_url = f"https://www.notion.so/{clean_id}"

        return jsonify({
            "success": True,
            "url": notion_url,
            "inserted": inserted,
            "total": len(claims),
        })

    except Exception as e:
        print(f"Error exporting to Notion: {e}", file=sys.stderr)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
