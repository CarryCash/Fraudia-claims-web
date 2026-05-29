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
from flask import Blueprint, jsonify, request, send_file
from io import BytesIO
from datetime import datetime

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


@agent_bp.route("/export_pdf", methods=["POST"])
def export_pdf():
    """
    Export a chat session to a beautifully formatted PDF audit report.

    Body:
      {
        "title": "optional",
        "messages": [{ "role": "user"|"agent", "text": "..." }]
      }
    """
    body = request.get_json(silent=True) or {}
    title = (body.get("title") or "Auditoría - Agente de Fraude").strip()
    messages = body.get("messages") or []

    try:
        from fpdf import FPDF
        import os

        # ── Custom PDF class with header/footer ──────────────────────────
        class AuditPDF(FPDF):
            def __init__(self):
                super().__init__()
                self.set_auto_page_break(auto=True, margin=25)

                # Try to load a TTF font for full Unicode support
                font_dir = os.path.join(os.path.dirname(__file__), "fonts")
                self._has_unicode_font = False
                # Try system DejaVu font paths
                dejavu_paths = [
                    os.path.join(font_dir, "DejaVuSans.ttf"),
                    "C:/Windows/Fonts/arial.ttf",
                ]
                for fp in dejavu_paths:
                    if os.path.isfile(fp):
                        try:
                            self.add_font("CustomFont", "", fp, uni=True)
                            self.add_font("CustomFont", "B", fp.replace(".ttf", "-Bold.ttf") if os.path.isfile(fp.replace(".ttf", "-Bold.ttf")) else fp, uni=True)
                            self._has_unicode_font = True
                        except Exception:
                            pass
                        break

            def _font(self, style="", size=10):
                if self._has_unicode_font:
                    self.set_font("CustomFont", style, size)
                else:
                    self.set_font("Helvetica", style, size)

            def header(self):
                # Teal accent bar at the top
                self.set_fill_color(13, 148, 136)  # teal-600
                self.rect(0, 0, 210, 8, "F")

                # Logo area
                self.set_y(14)
                self.set_fill_color(13, 148, 136)
                self.rect(15, 14, 8, 8, "F")
                self.set_text_color(255, 255, 255)
                self._font("B", 7)
                self.set_xy(15.5, 15.5)
                self.cell(7, 5, "IA", align="C")

                # Title
                self.set_xy(26, 14)
                self.set_text_color(26, 26, 26)
                self._font("B", 14)
                self.cell(0, 8, self._sanitize("Fraudia Claims"), new_x="LMARGIN")

                # Subtitle
                self.set_y(22)
                self.set_x(26)
                self.set_text_color(120, 120, 120)
                self._font("", 9)
                self.cell(0, 5, self._sanitize("Sistema Avanzado de Deteccion de Fraudes"), new_x="LMARGIN")

                # Thin separator line
                self.set_draw_color(220, 220, 220)
                self.line(15, 30, 195, 30)
                self.set_y(34)

            def footer(self):
                self.set_y(-20)
                self.set_draw_color(220, 220, 220)
                self.line(15, self.get_y(), 195, self.get_y())
                self.set_y(-16)
                self.set_text_color(160, 160, 160)
                self._font("", 7)
                self.cell(0, 10, f"Pagina {self.page_no()}/{{nb}}", align="C")

            @staticmethod
            def _sanitize(text: str) -> str:
                return (
                    text.replace("\u2013", "-")
                    .replace("\u2014", "-")
                    .replace("\u201c", '"')
                    .replace("\u201d", '"')
                    .replace("\u2019", "'")
                    .replace("\u2018", "'")
                    .replace("\u00e1", "a")
                    .replace("\u00e9", "e")
                    .replace("\u00ed", "i")
                    .replace("\u00f3", "o")
                    .replace("\u00fa", "u")
                    .replace("\u00f1", "n")
                    .replace("\u00c1", "A")
                    .replace("\u00c9", "E")
                    .replace("\u00cd", "I")
                    .replace("\u00d3", "O")
                    .replace("\u00da", "U")
                    .replace("\u00d1", "N")
                    .replace("\u00bf", "?")
                    .replace("\u00a1", "!")
                    .replace("\u2026", "...")
                    .replace("\u2022", "-")
                    .replace("\u2705", "[OK]")
                    .replace("\u26a0\ufe0f", "[!]")
                    .replace("\u26a0", "[!]")
                    .replace("\u2757", "[!]")
                    .replace("\u2b50", "*")
                )

        # ── Build the PDF ─────────────────────────────────────────────────
        pdf = AuditPDF()
        pdf.alias_nb_pages()
        pdf.add_page()

        # Report title section
        pdf.set_text_color(26, 26, 26)
        pdf._font("B", 12)
        pdf.cell(0, 8, pdf._sanitize(title), new_x="LMARGIN", new_y="NEXT")

        pdf.set_text_color(120, 120, 120)
        pdf._font("", 8)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        pdf.cell(0, 5, pdf._sanitize(f"Reporte generado: {ts}"), new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 5, pdf._sanitize(f"Total de mensajes: {len(messages)}"), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(6)

        # Separator
        pdf.set_draw_color(220, 220, 220)
        pdf.line(15, pdf.get_y(), 195, pdf.get_y())
        pdf.ln(6)

        # ── Render each message ──────────────────────────────────────────
        for i, m in enumerate(messages):
            role = (m.get("role") or "").strip()
            text = (m.get("text") or "").strip()
            if not text:
                continue

            is_user = role == "user"
            sanitized = pdf._sanitize(text)

            # Role label with colored indicator
            if is_user:
                # User: gray dot + "Analista"
                pdf.set_fill_color(180, 180, 180)
                pdf.circle(17, pdf.get_y() + 2.5, 2, "F")
                pdf.set_x(22)
                pdf.set_text_color(80, 80, 80)
                pdf._font("B", 9)
                pdf.cell(0, 6, "Analista", new_x="LMARGIN", new_y="NEXT")
            else:
                # Agent: teal dot + "Agente IA"
                pdf.set_fill_color(13, 148, 136)
                pdf.circle(17, pdf.get_y() + 2.5, 2, "F")
                pdf.set_x(22)
                pdf.set_text_color(13, 148, 136)
                pdf._font("B", 9)
                pdf.cell(0, 6, "Agente IA", new_x="LMARGIN", new_y="NEXT")

            # Message body
            pdf.set_x(22)
            y_before = pdf.get_y()

            if not is_user:
                # Light gray background for agent messages
                # Calculate height first by doing a dry run
                pdf._font("", 9)
                # We need to estimate height for the background
                line_height = 4.5
                text_width = 195 - 22 - 8  # page width minus indent minus padding
                # Use multi_cell with dry_run if available, otherwise just render
                pdf.set_fill_color(245, 245, 245)
                x_start = 20
                pdf.set_x(x_start)
                # Save position, render text to measure, then draw bg
                pdf.set_text_color(40, 40, 40)

                # Render with background
                pdf.set_x(x_start + 2)
                pdf.multi_cell(
                    text_width,
                    line_height,
                    sanitized,
                    new_x="LMARGIN",
                    new_y="NEXT",
                )
            else:
                pdf.set_x(22)
                pdf.set_text_color(26, 26, 26)
                pdf._font("", 9)
                pdf.multi_cell(
                    195 - 22,
                    4.5,
                    sanitized,
                    new_x="LMARGIN",
                    new_y="NEXT",
                )

            pdf.ln(5)

            # Light separator between messages
            if i < len(messages) - 1:
                pdf.set_draw_color(235, 235, 235)
                pdf.line(22, pdf.get_y(), 195, pdf.get_y())
                pdf.ln(5)

        # ── Final footer note ─────────────────────────────────────────────
        pdf.ln(8)
        pdf.set_draw_color(220, 220, 220)
        pdf.line(15, pdf.get_y(), 195, pdf.get_y())
        pdf.ln(4)
        pdf.set_text_color(160, 160, 160)
        pdf._font("", 7)
        pdf.multi_cell(
            0, 4,
            pdf._sanitize(
                "Este reporte fue generado automaticamente por el sistema Fraudia Claims. "
                "La informacion presentada es orientativa y debe ser validada por un analista humano."
            ),
        )

        # ── Output ────────────────────────────────────────────────────────
        pdf_bytes = pdf.output()
        if isinstance(pdf_bytes, str):
            pdf_bytes = pdf_bytes.encode("latin-1", errors="ignore")

        buf = BytesIO(pdf_bytes)
        buf.seek(0)
        filename = f"auditoria_agente_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
        return send_file(
            buf,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=filename,
        )
    except Exception as exc:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(exc)}), 500
