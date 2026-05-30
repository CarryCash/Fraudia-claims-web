import os
# pyrefly: ignore [missing-import]
from flask import Blueprint, request, jsonify
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from dotenv import load_dotenv

load_dotenv()

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

@auth_bp.route("/google", methods=["POST"])
def google_auth():
    """Verifica un token de Google y retorna los datos del usuario."""
    body = request.get_json(silent=True) or {}
    token = body.get("credential")

    if not token:
        return jsonify({"error": "No credential provided"}), 400

    try:
        # Si tienes el VITE_GOOGLE_CLIENT_ID en el backend, úsalo aquí para mayor seguridad.
        # Por ahora lo validamos genéricamente.
        client_id = os.getenv("VITE_GOOGLE_CLIENT_ID", os.getenv("GOOGLE_CLIENT_ID"))
        
        # Verify the token
        idinfo = id_token.verify_oauth2_token(
            token, google_requests.Request(), client_id, clock_skew_in_seconds=10
        )

        # Opcional: Validar dominio aquí si se requiere en el futuro
        # if idinfo.get("hd") != "aseguradoradelsur.com":
        #     return jsonify({"error": "Unauthorized domain"}), 403

        # Si todo está bien, retornamos la data que nos interesa
        user_data = {
            "name": idinfo.get("name"),
            "email": idinfo.get("email"),
            "picture": idinfo.get("picture"),
            "sub": idinfo.get("sub"), # ID único de google
        }

        return jsonify({
            "success": True,
            "user": user_data
        })

    except ValueError as e:
        # Invalid token
        return jsonify({"error": f"Invalid token: {str(e)}"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500
