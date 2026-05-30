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
import requests
import joblib
from pathlib import Path

load_dotenv()  # Load GEMINI_API_KEY from .env

# Global model cache
_rf_model = None
_rf_features = None
_iso_model = None
_iso_features = None

def _load_models():
    global _rf_model, _rf_features, _iso_model, _iso_features
    if _rf_model is not None:
        return
        
    project_root = Path(__file__).resolve().parents[2]
    models_dir = project_root / "models"
    
    try:
        if (models_dir / "random_forest_fraud.joblib").exists():
            _rf_model = joblib.load(models_dir / "random_forest_fraud.joblib")
            _rf_features = joblib.load(models_dir / "features.joblib")
    except Exception as e:
        print(f"Error loading RF model: {e}")
        
    try:
        if (models_dir / "isolation_forest.joblib").exists():
            _iso_model = joblib.load(models_dir / "isolation_forest.joblib")
            _iso_features = joblib.load(models_dir / "anomaly_features.joblib")
    except Exception as e:
        print(f"Error loading Isolation Forest model: {e}")

def combine_scores(rule_score: int, ml_prob: float) -> int:
    """Combine rule-based points (0-100) and ML probability (0-1).
    Final score is in range 0-100.
    
    Formula: 40% Rules Score + 60% ML Probability
    """
    rules_weighted = rule_score * 0.40
    ml_weighted = (ml_prob * 100) * 0.60
    total = int(round(rules_weighted + ml_weighted))
    return min(max(total, 0), 100)

def _build_prompt(claim: Dict[str, Any], rule_score: int, ml_prob: float, total_score: int, alerts: List[str], is_anomaly: bool) -> str:
    """Build a professional prompt for Gemini to explain the risk score."""
    triggered_rules = ", ".join(claim.get("hard_triggered", [])) or "Ninguna"
    soft_alerts_str = "\n".join([f"- {a}" for a in alerts]) or "- Ninguna alerta de regla blanda detectada."
    
    anomaly_text = ""
    if is_anomaly:
        anomaly_text = "\n\nIMPORTANTE: El modelo matemático no supervisado (Isolation Forest) detectó una ANOMALÍA ESTADÍSTICA en este siniestro. Como parte de tu análisis, DEBES instruir al analista humano a buscar explícitamente desviaciones numéricas atípicas (montos, tiempos, frecuencias) ya que los patrones numéricos de este caso se alejan de la norma histórica."
    
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
    "{action}"{anomaly_text}

    Por favor redacta la justificación en español, estructurada de la siguiente manera:
    1. **Resumen de Alertas**: Un párrafo conciso resumiendo por qué es sospechoso o normal.
    2. **Factores de Riesgo Clave**: Lista con viñetas explicativas (máximo 4 puntos) analizando los cruces de variables (ej. tiempo de reporte, proveedor, narrativa).
    3. **Recomendación para el Analista Humano**: Pasos prácticos que debe tomar el analista (ej. verificar facturas, inspeccionar vehículo, cruzar datos).

    Mantén un tono profesional, preventivo y ético. Recuerda que es una alerta para revisión humana, NO una acusación de fraude.
    """
    return prompt

def generate_explanation(claim: Dict[str, Any], rule_score: int, ml_prob: float, alerts: List[str], is_anomaly: bool = False) -> str:
    """Generate a natural-language explanation of a claim's fraud risk using NVIDIA API."""
    total = combine_scores(rule_score, ml_prob)
    prompt = _build_prompt(claim, rule_score, ml_prob, total, alerts, is_anomaly)
    # Prepare NVIDIA API request
    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key:
        return "Error: NVIDIA_API_KEY no configurado en el entorno. No se puede generar la explicación detallada por IA."
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "google/gemma-3n-e4b-it",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1536,
        "temperature": 0.2,
        "top_p": 0.7,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0,
        "stream": False,
    }
    try:
        response = requests.post(
            "https://integrate.api.nvidia.com/v1/chat/completions",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        # The response structure may contain 'choices' with 'message'->'content'
        if isinstance(data, dict) and "choices" in data:
            return data["choices"][0]["message"]["content"].strip()
        return str(data)
    except Exception as e:
        return f"Error al generar la explicación con NVIDIA API: {str(e)}\n\n" \
               f"Justificación básica basada en reglas duras/blandas activas:\n" \
               f"- Reglas duras: {', '.join(claim.get('hard_triggered', [])) or 'Ninguna'}\n" \
               f"- Puntaje de Reglas: {rule_score}/100\n" \
               f"- Probabilidad ML: {ml_prob:.2%}"

def _predict_ml(row: Dict[str, Any]) -> tuple[float, bool]:
    """Return ML probability (Random Forest) and Anomaly flag (Isolation Forest)."""
    _load_models()
    
    ml_prob = 0.0
    is_anomaly = False
    
    # Random Forest Prediction
    if _rf_model is not None and _rf_features is not None:
        try:
            import pandas as pd
            feat_dict = {f: [row.get(f, 0.0)] for f in _rf_features}
            df_x = pd.DataFrame(feat_dict).fillna(0)
            ml_prob = float(_rf_model.predict_proba(df_x)[0, 1])
        except Exception as e:
            print(f"Prediction error (RF): {e}")
            
    # Isolation Forest Prediction
    if _iso_model is not None and _iso_features is not None:
        try:
            import pandas as pd
            feat_dict = {f: [row.get(f, 0.0)] for f in _iso_features}
            df_x = pd.DataFrame(feat_dict).fillna(0)
            pred = _iso_model.predict(df_x)[0]
            is_anomaly = bool(pred == -1)
        except Exception as e:
            print(f"Prediction error (ISO): {e}")
            
    return ml_prob, is_anomaly

def _bulk_predict_ml(df) -> tuple:
    """Run ML predictions on an entire DataFrame at once. Extremely fast."""
    _load_models()
    import numpy as np
    import pandas as pd
    ml_probs = np.zeros(len(df))
    is_anomalies = np.zeros(len(df), dtype=bool)
    
    if _rf_model is not None and _rf_features is not None:
        try:
            df_x = pd.DataFrame()
            for f in _rf_features:
                df_x[f] = df.get(f, 0.0)
            df_x = df_x.fillna(0)
            ml_probs = _rf_model.predict_proba(df_x)[:, 1]
        except Exception as e:
            print(f"Prediction error (RF Bulk): {e}")
            
    if _iso_model is not None and _iso_features is not None:
        try:
            df_x = pd.DataFrame()
            for f in _iso_features:
                df_x[f] = df.get(f, 0.0)
            df_x = df_x.fillna(0)
            preds = _iso_model.predict(df_x)
            is_anomalies = (preds == -1)
        except Exception as e:
            print(f"Prediction error (ISO Bulk): {e}")
            
    return ml_probs, is_anomalies

__all__ = ["combine_scores", "generate_explanation", "_predict_ml", "_bulk_predict_ml"]
