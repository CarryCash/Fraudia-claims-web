# backend/src/api/agent.py
"""Blueprint for the conversational AI agent endpoint.

Exposes a single endpoint:
    POST /api/agent/chat
    Body:  { "question": "..." }
    Response: { "answer": "..." }

The ClaimsAgent is initialised lazily (once) so the heavy CSV/TF-IDF
setup only happens on the first request, then stays in memory.
"""

import sys
from pathlib import Path

# pyrefly: ignore [missing-import]
from flask import Blueprint, jsonify, request

# Ensure the backend root is on sys.path
BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

agent_bp = Blueprint("agent", __name__, url_prefix="/api/agent")

# Lazy singleton – initialised on first POST
_agent_instance = None


def _get_agent():
    """Return (or create) the singleton ClaimsAgent."""
    global _agent_instance
    if _agent_instance is None:
        from src.ai_agent.claims_agent import ClaimsAgent  # noqa: PLC0415

        data_dir = BACKEND_ROOT.parent / "data" / "processed"
        _agent_instance = ClaimsAgent(data_dir=str(data_dir))
    return _agent_instance


# ── POST /api/agent/chat ──────────────────────────────────────────────────────
@agent_bp.route("/chat", methods=["POST"])
def chat():
    """Handle a conversational question from the analyst UI."""
    body = request.get_json(silent=True) or {}
    question = (body.get("question") or "").strip()

    if not question:
        return jsonify({"error": "El campo 'question' es requerido."}), 400

    try:
        agent = _get_agent()
        answer = agent.answer_question(question)
        return jsonify({"answer": answer})
    except FileNotFoundError as exc:
        return jsonify({
            "answer": (
                "⚠️ No se encontró el dataset de siniestros. "
                "Por favor, ejecuta el script de ingesta de datos primero.\n\n"
                f"Detalle técnico: {exc}"
            )
        }), 200
    except Exception as exc:  # pragma: no cover
        return jsonify({
            "answer": (
                f"⚠️ Error al inicializar el agente: {exc}\n\n"
                "Verifica que el dataset esté disponible y que GEMINI_API_KEY esté configurado."
            )
        }), 200
