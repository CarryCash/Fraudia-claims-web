# backend/src/api/health.py
"""Health-check blueprint – confirms the API is running."""

# pyrefly: ignore [missing-import]
from flask import Blueprint, jsonify

health_bp = Blueprint("health", __name__, url_prefix="/api")


@health_bp.route("/health", methods=["GET"])
def health_check():
    """Simple liveness probe."""
    return jsonify({"status": "ok", "service": "fraudia-claims-api"})
