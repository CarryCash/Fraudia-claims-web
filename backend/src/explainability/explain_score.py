# src/explainability/explain_score.py
"""Explainability utilities for the fraud detector.

- Computes a combined risk score (0-100) using a hybrid approach:
  * 40% weight from the business rules engine points (0-100).
  * 60% weight from the Machine Learning model probability (0-1).
- Calls Gemini 2.0 Flash Lite to generate a human-readable, professional justification
  of why the claim received its specific risk level.
"""

import os
from typing import Dict, Any, List
from dotenv import load_dotenv
# pyrefly: ignore [missing-import]
from google import genai

load_dotenv()  # Load GEMINI_API_KEY from .env

def combine_scores(rule_score: int, ml_prob: float) -> int:
    """Combine rule-based points (0-100) and ML probability (0-1).
    Final score is in range 0-100.
    
    Formula: 40% Rules Score + 60% ML Probability
    """
    rules_weighted = rule_score * 0.40
    ml_weighted = (ml_prob * 100) * 0.60
    total = int(round(rules_weighted + ml_weighted))
    return min(max(total, 0), 100)

def _build_prompt(claim: Dict[str, Any], rule_score: int, ml_prob: float, total_score: int, alerts: List[str]) -> str:
    """Build a professional prompt for Gemini to explain the risk score."""
    triggered_rules = ", ".join(claim.get("hard_triggered", [])) or "Ninguna"
    soft_alerts_str = "\n".join([f"- {a}" for a in alerts]) or "- Ninguna alerta de regla blanda detectada."
    
    # Map traffic light color
    if total_score <= 40:
        color = "Verde (Riesgo Bajo)"
        action = "Continuar con el flujo normal de liquidación."
    elif total_score <= 75:
        color = "Amarillo (Riesgo Medio)"
        action = "Escalar a la Unidad Antifraude para revisión documental y confirmación."
    else:
        color = "Rojo (Riesgo Alto / Crítico)"
        action = "Escalar a la Unidad Antifraude para inspección especializada en campo y auditoría profunda."

    prompt = f"""
    Eres un analista de fraudes senior de seguros en "Aseguradora del Sur" (Ecuador).
    Justifica de manera objetiva, técnica y clara por qué el siguiente siniestro recibió un Score de Riesgo de {total_score}/100, clasificándose en semáforo {color}.

    Detalles del Siniestro:
    - ID Siniestro: {claim.get('id_siniestro')}
    - ID Póliza: {claim.get('id_poliza')}
    - Ramo: {claim.get('ramo')}
    - Cobertura: {claim.get('cobertura')}
    - Ciudad (Sucursal): {claim.get('sucursal')}
    - Beneficiario/Proveedor: {claim.get('beneficiario')}
    - Monto Reclamado: ${claim.get('monto_reclamado'):,.2f}
    - Monto Estimado: ${claim.get('monto_estimado'):,.2f}
    - Días desde inicio de póliza: {claim.get('dias_desde_inicio_poliza')} días
    - Días hasta fin de póliza: {claim.get('dias_desde_fin_poliza')} días
    - Demora en reporte: {claim.get('dias_entre_ocurrencia_reporte')} días
    - Narrativa del siniestro: "{claim.get('descripcion')}"

    Métricas del Sistema Híbrido:
    - Reglas de Negocio Duras activadas: {triggered_rules}
    - Alertas de Reglas Blandas (Puntaje de Reglas: {rule_score}/100):
{soft_alerts_str}
    - Probabilidad del Modelo de Inteligencia Artificial (ML): {ml_prob:.2%} (Ponderación 60% del Score)

    Acción Sugerida por el Sistema:
    "{action}"

    Por favor redacta la justificación en español, estructurada de la siguiente manera:
    1. **Resumen de Alertas**: Un párrafo conciso resumiendo por qué es sospechoso o normal.
    2. **Factores de Riesgo Clave**: Lista con viñetas explicativas (máximo 4 puntos) analizando los cruces de variables (ej. tiempo de reporte, proveedor, narrativa).
    3. **Recomendación para el Analista Humano**: Pasos prácticos que debe tomar el analista (ej. verificar facturas, inspeccionar vehículo, cruzar datos).

    Mantén un tono profesional, preventivo y ético. Recuerda que es una alerta para revisión humana, NO una acusación de fraude.
    """
    return prompt

def generate_explanation(claim: Dict[str, Any], rule_score: int, ml_prob: float, alerts: List[str]) -> str:
    """Generate a natural-language explanation of a claim's fraud risk using Gemini."""
    total = combine_scores(rule_score, ml_prob)
    prompt = _build_prompt(claim, rule_score, ml_prob, total, alerts)
    
    try:
        # Load API key and create client
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return "Error: GEMINI_API_KEY no configurado en el entorno. No se puede generar la explicación detallada por IA."

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents=prompt,
        )
        return response.text.strip()
    except Exception as e:
        return f"Error al generar la explicación con Gemini: {str(e)}\n\n" \
               f"Justificación básica basada en reglas duras/blandas activas:\n" \
               f"- Reglas duras: {', '.join(claim.get('hard_triggered', [])) or 'Ninguna'}\n" \
               f"- Puntaje de Reglas: {rule_score}/100\n" \
               f"- Probabilidad ML: {ml_prob:.2%}"

__all__ = ["combine_scores", "generate_explanation"]
