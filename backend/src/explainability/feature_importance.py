"""Feature importance and sector comparison for claim explanations."""

from typing import Dict, Any, List
import pandas as pd
from pathlib import Path
import numpy as np

def get_feature_importance_for_claim(row: pd.Series, rule_score: int, ml_prob: float) -> Dict[str, Any]:
    # High-impact features that typically drive risk scores
    feature_weights = {
        "dias_entre_ocurrencia_reporte": {"weight": 0.15, "name": "Demora en Reporte", "threshold": 30},
        "monto_reclamado": {"weight": 0.12, "name": "Monto Reclamado", "threshold": 50000},
        "falta_documento_obligatorio": {"weight": 0.10, "name": "Documentación Incompleta", "threshold": 0.5},
        "freq_asegurado_18m": {"weight": 0.10, "name": "Frecuencia de Asegurado", "threshold": 2},
        "proveedor_casos_observados_anio": {"weight": 0.08, "name": "Casos Proveedor", "threshold": 5},
        "documento_alterado": {"weight": 0.08, "name": "Documento Alterado", "threshold": 0.5},
        "frecuencia_similar": {"weight": 0.07, "name": "Patrón Similar", "threshold": 0.5},
        "accidente_madrugada": {"weight": 0.07, "name": "Siniestro en Madrugada", "threshold": 0.5},
        "narrativa_clonada": {"weight": 0.06, "name": "Narrativa Clonada", "threshold": 0.5},
        "tercero_huye_sin_camaras": {"weight": 0.06, "name": "Tercero Ausente", "threshold": 0.5},
        "relato_ilogico": {"weight": 0.05, "name": "Relato Incoherente", "threshold": 0.5},
    }
    
    # Calculate contribution of each feature
    contributions = []
    for feature, info in feature_weights.items():
        if feature in row.index:
            value = row[feature]
            # Normalize value relative to threshold
            if pd.isna(value):
                normalized = 0
            else:
                try:
                    normalized = min(float(value) / float(info["threshold"]), 2.0)  # Cap at 2x threshold
                except:
                    normalized = 1.0 if value else 0
            
            contribution_pct = info["weight"] * 100 * normalized
            impact_level = "high" if contribution_pct > 15 else "medium" if contribution_pct > 5 else "low"
            
            contributions.append({
                "name": info["name"],
                "feature": feature,
                "value": float(value) if pd.notna(value) else 0,
                "contribution": round(contribution_pct, 1),
                "impact": impact_level,
                "threshold": info["threshold"]
            })
    
    # Sort by contribution and take top 5
    contributions.sort(key=lambda x: x["contribution"], reverse=True)
    top_factors = contributions[:5]
    
    # Risk factors breakdown
    risk_breakdown = {
        "timing_risk": {
            "score": 0,
            "factors": []
        },
        "amount_risk": {
            "score": 0,
            "factors": []
        },
        "provider_risk": {
            "score": 0,
            "factors": []
        },
        "documentation_risk": {
            "score": 0,
            "factors": []
        },
        "frequency_risk": {
            "score": 0,
            "factors": []
        }
    }
    
    for factor in top_factors:
        feature_name = factor["feature"]
        if "dias_entre" in feature_name or "accidente_madrugada" in feature_name:
            risk_breakdown["timing_risk"]["score"] += factor["contribution"]
            risk_breakdown["timing_risk"]["factors"].append(factor["name"])
        elif "monto" in feature_name:
            risk_breakdown["amount_risk"]["score"] += factor["contribution"]
            risk_breakdown["amount_risk"]["factors"].append(factor["name"])
        elif "proveedor" in feature_name:
            risk_breakdown["provider_risk"]["score"] += factor["contribution"]
            risk_breakdown["provider_risk"]["factors"].append(factor["name"])
        elif "documento" in feature_name or "falta" in feature_name:
            risk_breakdown["documentation_risk"]["score"] += factor["contribution"]
            risk_breakdown["documentation_risk"]["factors"].append(factor["name"])
        elif "freq" in feature_name:
            risk_breakdown["frequency_risk"]["score"] += factor["contribution"]
            risk_breakdown["frequency_risk"]["factors"].append(factor["name"])
    
    # Sector comparison - simulate sector averages
    sector_avg = {
        "dias_entre_ocurrencia_reporte": 15,
        "monto_reclamado": 30000,
        "falta_documento_obligatorio": 0.05,
        "freq_asegurado_18m": 1.2,
        "proveedor_casos_observados_anio": 3,
        "documento_alterado": 0.02,
        "accidente_madrugada": 0.10,
    }
    
    # Calculate percentile for this claim
    claim_risk_score = (rule_score * 0.4) + (ml_prob * 100 * 0.6)
    percentile = min(95, max(5, int((claim_risk_score / 100) * 100)))  # 5-95 range
    
    return {
        "top_factors": top_factors,
        "sector_comparison": {
            "this_claim": {
                "dias_entre_ocurrencia_reporte": float(row.get("dias_entre_ocurrencia_reporte", 0)),
                "monto_reclamado": float(row.get("monto_reclamado", 0)),
                "falta_documento_obligatorio": float(row.get("falta_documento_obligatorio", 0)),
                "freq_asegurado_18m": float(row.get("freq_asegurado_18m", 0)),
            },
            "sector_avg": sector_avg,
            "percentile": percentile,
            "percentile_description": f"Peor que {percentile}% de los siniestros del sector"
        },
        "risk_factors_breakdown": risk_breakdown
    }


def calculate_what_if_scenario(row: pd.Series, modifications: Dict[str, float], rule_score: int, ml_prob: float) -> Dict[str, Any]:
    """Calculate what the risk score would be if certain features were different.
    
    modifications: {"feature_name": new_value, ...}
    """
    # Create a modified copy of the row
    modified_row = row.copy()
    for feature, new_value in modifications.items():
        if feature in modified_row.index:
            modified_row[feature] = new_value
    
    # Recalculate feature importance with modified values
    modified_importance = get_feature_importance_for_claim(modified_row, rule_score, ml_prob)
    
    # Simulate new score (simplified: adjust based on key changes)
    score_adjustment = 0
    for feature, new_value in modifications.items():
        if feature in row.index:
            old_value = float(row[feature]) if pd.notna(row[feature]) else 0
            new_value = float(new_value)
            
            if feature == "dias_entre_ocurrencia_reporte":
                # Longer delay = more risk
                change = (new_value - old_value) * 0.5  # 0.5 points per day
            elif feature == "monto_reclamado":
                # Higher monto = more risk
                change = (new_value - old_value) * 0.0001  # Based on amount
            elif feature in ["falta_documento_obligatorio", "documento_alterado", "narrativa_clonada"]:
                # Binary flag: -20 or +20 points
                change = (new_value - old_value) * 20
            elif feature == "freq_asegurado_18m":
                # Higher frequency = more risk
                change = (new_value - old_value) * 5
            else:
                change = 0
            
            score_adjustment += change
    
    new_combined_score = int(max(0, min(100, (rule_score * 0.4 + ml_prob * 100 * 0.6) + score_adjustment)))
    
    return {
        "modified_importance": modified_importance,
        "original_score": int(rule_score * 0.4 + ml_prob * 100 * 0.6),
        "new_score": new_combined_score,
        "score_change": new_combined_score - int(rule_score * 0.4 + ml_prob * 100 * 0.6),
        "modifications": modifications
    }
