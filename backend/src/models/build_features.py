# src/models/build_features.py
"""Feature Engineering script for fraud claims detection.

This script processes raw CSV files and generates the `siniestros_processed.csv` dataset.
It uses `sentence-transformers` to compute semantic similarity between claim descriptions
to identify potential "cloned" or highly suspicious duplicate narratives.
"""

import os
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.metrics.pairwise import cosine_similarity
# pyrefly: ignore [missing-import]
from sentence_transformers import SentenceTransformer

# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROC_DIR = PROJECT_ROOT / "data" / "processed"

from src.ingestion.load_data import load_siniestros, load_polizas

# Restrictive providers list
LISTA_RESTRICTIVA = ["Taller El Chueco", "Taller XYZ", "Clínica Trucha", "Perito Sospechoso"]

def build_features():
    print("Loading processed datasets...")
    try:
        df_sin = load_siniestros(processed=False)
        df_pol = load_polizas(processed=False)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return

    # Convert dates
    for col in ["fecha_ocurrencia", "fecha_reporte"]:
        if col in df_sin.columns:
            df_sin[col] = pd.to_datetime(df_sin[col], errors="coerce")
    for col in ["fecha_inicio", "fecha_fin"]:
        if col in df_pol.columns:
            df_pol[col] = pd.to_datetime(df_pol[col], errors="coerce")

    # Merge Siniestros with Polizas to get policy dates and suma_asegurada
    df_merged = pd.merge(df_sin, df_pol, on=["id_poliza", "id_asegurado"], how="left")

    print("Computing engineered features...")

    # Date-based features
    if "fecha_inicio" in df_merged.columns and "fecha_ocurrencia" in df_merged.columns:
        df_merged["dias_desde_inicio_poliza"] = (df_merged["fecha_ocurrencia"] - df_merged["fecha_inicio"]).dt.days
    else:
        df_merged["dias_desde_inicio_poliza"] = 999

    if "fecha_fin" in df_merged.columns and "fecha_ocurrencia" in df_merged.columns:
        df_merged["dias_desde_fin_poliza"] = (df_merged["fecha_fin"] - df_merged["fecha_ocurrencia"]).dt.days
    else:
        df_merged["dias_desde_fin_poliza"] = 999

    if "fecha_reporte" in df_merged.columns and "fecha_ocurrencia" in df_merged.columns:
        df_merged["dias_entre_ocurrencia_reporte"] = (df_merged["fecha_reporte"] - df_merged["fecha_ocurrencia"]).dt.days
    else:
        df_merged["dias_entre_ocurrencia_reporte"] = 0
        
    df_merged["accidente_madrugada"] = df_merged["fecha_ocurrencia"].dt.hour.apply(lambda h: 1 if 0 <= h <= 5 else 0)

    # Provider and categorical features
    df_merged["proveedor_lista_restrictiva"] = df_merged["beneficiario"].apply(lambda b: 1 if pd.notna(b) and any(bad in b for bad in LISTA_RESTRICTIVA) else 0)
    
    # Let's generate some realistic-looking frequencies since we don't have historical tables in this mock
    np.random.seed(42)
    df_merged["historial_siniestros_asegurado"] = np.random.randint(0, 5, size=len(df_merged))
    df_merged["freq_asegurado_18m"] = np.random.randint(0, 4, size=len(df_merged))
    df_merged["freq_vehiculo_18m"] = np.random.randint(0, 3, size=len(df_merged))
    df_merged["freq_conductor_18m"] = np.random.randint(0, 3, size=len(df_merged))
    df_merged["freq_solo_rc_previos"] = np.random.randint(0, 2, size=len(df_merged))
    df_merged["proveedor_casos_observados_anio"] = np.random.randint(0, 4, size=len(df_merged))
    
    # Text-based indicators
    df_merged["relato_ilogico"] = df_merged["descripcion"].apply(lambda x: 1 if pd.notna(x) and "imposible" in str(x).lower() else 0)
    df_merged["tercero_huye_sin_camaras"] = df_merged["descripcion"].apply(lambda x: 1 if pd.notna(x) and "huyó" in str(x).lower() else 0)
    
    # Financial indicators
    if "suma_asegurada" in df_merged.columns:
        df_merged["monto_cercano_suma_asegurada"] = (df_merged["monto_reclamado"] >= 0.95 * df_merged["suma_asegurada"]).astype(int)
    else:
        df_merged["monto_cercano_suma_asegurada"] = 0

    # Document-based features (simulated for now)
    if "etiqueta_fraude_simulada" in df_merged.columns:
        df_merged["documento_alterado"] = np.where(df_merged["etiqueta_fraude_simulada"] == 1, np.random.binomial(1, 0.4, size=len(df_merged)), 0)
        df_merged["falta_documento_obligatorio"] = np.where(df_merged["etiqueta_fraude_simulada"] == 1, np.random.binomial(1, 0.3, size=len(df_merged)), 0)
    else:
        df_merged["documento_alterado"] = 0
        df_merged["falta_documento_obligatorio"] = 0

    # NLP Semantic Similarity using Sentence-Transformers
    print("Loading sentence-transformer model (all-MiniLM-L6-v2) for NLP features...")
    # We use a fast, lightweight embedding model
    embedder = SentenceTransformer('all-MiniLM-L6-v2')
    
    descriptions = df_merged["descripcion"].fillna("").tolist()
    print("Computing embeddings for narratives...")
    embeddings = embedder.encode(descriptions, convert_to_tensor=False, show_progress_bar=True)
    
    print("Computing cosine similarity matrix to detect cloned narratives...")
    sim_matrix = cosine_similarity(embeddings)
    
    # For each claim, find the max similarity with any OTHER claim
    max_sims = []
    for i in range(len(sim_matrix)):
        sims = sim_matrix[i].copy()
        sims[i] = 0.0 # Ignore self
        max_sim = np.max(sims)
        max_sims.append(max_sim)
        
    df_merged["narrativa_similitud_score"] = max_sims
    # Clone threshold > 0.85
    df_merged["narrativa_clonada"] = (df_merged["narrativa_similitud_score"] > 0.85).astype(int)
    
    print(f"Identificadas {(df_merged['narrativa_clonada'] == 1).sum()} narrativas posiblemente clonadas.")

    # Save to processed directory
    PROC_DIR.mkdir(parents=True, exist_ok=True)
    output_path = PROC_DIR / "siniestros_processed.csv"
    
    # Save processed dataframe
    df_merged.to_csv(output_path, index=False)
    print(f"Feature engineering complete. Saved to: {output_path}")

if __name__ == "__main__":
    build_features()
