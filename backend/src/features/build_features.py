# src/features/build_features.py
"""Feature engineering for the fraud detection prototype.

Loads relational tables (siniestros, polizas, asegurados, proveedores, documentos)
and derives numeric, temporal, relational and NLP features (using TF-IDF for similarity)
to be used in the rule engine and the ML model.
"""

import os
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Paths
DATA_DIR = os.getenv("DATA_DIR", "data")
RAW_DIR = os.getenv("RAW_DATA_DIR", os.path.join(DATA_DIR, "raw"))
PROC_DIR = os.getenv("PROCESSED_DATA_DIR", os.path.join(DATA_DIR, "processed"))

def build_features(save: bool = True) -> pd.DataFrame:
    """Load raw relational datasets, compute engineered features, and save processed data."""
    # Ensure processed folder exists
    Path(PROC_DIR).mkdir(parents=True, exist_ok=True)
    
    # 1. Load raw tables
    siniestros_path = Path(RAW_DIR) / "siniestros.csv"
    polizas_path = Path(RAW_DIR) / "polizas.csv"
    asegurados_path = Path(RAW_DIR) / "asegurados.csv"
    proveedores_path = Path(RAW_DIR) / "proveedores.csv"
    documentos_path = Path(RAW_DIR) / "documentos.csv"
    
    if not all(p.exists() for p in [siniestros_path, polizas_path, asegurados_path, proveedores_path, documentos_path]):
        raise FileNotFoundError("Relational raw tables are missing. Please run scripts/generate_synthetic.py first.")
        
    df_sin = pd.read_csv(siniestros_path)
    df_pol = pd.read_csv(polizas_path)
    df_aseg = pd.read_csv(asegurados_path)
    df_prov = pd.read_csv(proveedores_path)
    df_docs = pd.read_csv(documentos_path)
    
    # Ensure dates are datetime objects
    df_sin["fecha_ocurrencia"] = pd.to_datetime(df_sin["fecha_ocurrencia"])
    df_sin["fecha_reporte"] = pd.to_datetime(df_sin["fecha_reporte"])
    df_pol["fecha_inicio"] = pd.to_datetime(df_pol["fecha_inicio"])
    df_pol["fecha_fin"] = pd.to_datetime(df_pol["fecha_fin"])
    
    # 2. Relational mappings & lookup features
    # Match suma_asegurada from policies
    pol_dict = df_pol.set_index("id_poliza")["suma_asegurada"].to_dict()
    df_sin["suma_asegurada"] = df_sin["id_poliza"].map(pol_dict)
    
    # Match provider info
    prov_restrict_dict = df_prov.set_index("id_proveedor")["porcentaje_de_casos_observados"].to_dict()
    prov_name_dict = df_prov.set_index("id_proveedor")["nombre"].to_dict()
    
    # Blacklisted providers
    blacklist = ["Taller El Chueco", "Taller XYZ", "Clínica Trucha", "Perito Sospechoso"]
    df_sin["proveedor_lista_restrictiva"] = df_sin["beneficiario"].apply(
        lambda x: 1 if any(b in str(x) for b in blacklist) else 0
    )
    
    # 3. Document check features (from documentos table)
    # Check if any document has an inconsistency
    inc_docs = df_docs[df_docs["inconsistencia_detectada"] == "Sí"]["id_siniestro"].unique()
    df_sin["documento_alterado"] = df_sin["id_siniestro"].apply(lambda x: 1 if x in inc_docs else 0)
    
    # Check if a critical document is missing (delivered == "No" and documents_completos == "No")
    df_sin["falta_documento_obligatorio"] = df_sin["documentos_completos"].apply(lambda x: 1 if str(x).lower() == "no" else 0)
    
    # 4. Frequencies in rolling 18 months (540 days)
    # For each claim, we count claims of the same entity within [occurrence_date - 540 days, occurrence_date]
    freq_aseg_18m = []
    freq_veh_18m = []
    
    for idx, row in df_sin.iterrows():
        aseg_id = row["id_asegurado"]
        placa = row["placa_vehiculo"]
        date = row["fecha_ocurrencia"]
        
        # Insured
        claims_aseg = df_sin[
            (df_sin["id_asegurado"] == aseg_id) & 
            (df_sin["fecha_ocurrencia"] <= date) & 
            (df_sin["fecha_ocurrencia"] >= date - pd.Timedelta(days=540))
        ]
        freq_aseg_18m.append(len(claims_aseg))
        
        # Vehicle
        if pd.notna(placa):
            claims_veh = df_sin[
                (df_sin["placa_vehiculo"] == placa) & 
                (df_sin["fecha_ocurrencia"] <= date) & 
                (df_sin["fecha_ocurrencia"] >= date - pd.Timedelta(days=540))
            ]
            freq_veh_18m.append(len(claims_veh))
        else:
            freq_veh_18m.append(1)
            
    df_sin["freq_asegurado_18m"] = freq_aseg_18m
    df_sin["freq_vehiculo_18m"] = freq_veh_18m
    df_sin["freq_conductor_18m"] = freq_aseg_18m # Conductor is usually the insured
    
    # Freq of previous RC (Responsabilidad Civil) claims for the same insured
    # We count previous claims where cobertura is "Choque" (which represents RC claims here)
    freq_rc_prev = []
    for idx, row in df_sin.iterrows():
        aseg_id = row["id_asegurado"]
        date = row["fecha_ocurrencia"]
        claims_rc = df_sin[
            (df_sin["id_asegurado"] == aseg_id) & 
            (df_sin["fecha_ocurrencia"] < date) & 
            (df_sin["cobertura"] == "Choque")
        ]
        freq_rc_prev.append(len(claims_rc))
    df_sin["freq_solo_rc_previos"] = freq_rc_prev
    
    # 5. Provider cases in the same year
    df_sin["anio_siniestro"] = df_sin["fecha_ocurrencia"].dt.year
    df_sin["proveedor_casos_observados_anio"] = df_sin.groupby(["id_proveedor", "anio_siniestro"])["id_siniestro"].transform("count")
    
    # 6. Dynamic / Narrative features (NLP)
    desc_lower = df_sin["descripcion"].astype(str).str.lower()
    df_sin["relato_ilogico"] = desc_lower.apply(
        lambda x: 1 if any(kw in x for kw in ["volcadura", "desplome", "imposible", "inconsistente"]) else 0
    )
    df_sin["accidente_madrugada"] = desc_lower.apply(
        lambda x: 1 if any(kw in x for kw in ["madrugada", "01:", "02:", "03:", "04:", "05:"]) else 0
    )
    df_sin["tercero_huye_sin_camaras"] = desc_lower.apply(
        lambda x: 1 if ("huye" in x or "huyó" in x or "se dio a la fuga" in x) and ("cámara" not in x and "camara" not in x) else 0
    )
    
    # 7. Text Similarity between all narratives (RF07 cloned narratives)
    # Using TF-IDF Vectorizer (scikit-learn is already installed, avoids sentence-transformers weight)
    vectorizer = TfidfVectorizer(stop_words=None)
    tfidf_matrix = vectorizer.fit_transform(df_sin["descripcion"].astype(str))
    sim_matrix = cosine_similarity(tfidf_matrix)
    
    max_sims = []
    for i in range(len(df_sin)):
        sim_scores = sim_matrix[i].copy()
        sim_scores[i] = 0 # Ignore self-similarity
        max_sims.append(sim_scores.max())
        
    df_sin["narrativa_similitud_score"] = max_sims
    df_sin["narrativa_clonada"] = df_sin["narrativa_similitud_score"].apply(lambda x: 1 if x >= 0.85 else 0)
    
    # 8. Monto cercano a suma asegurada (>= 95%)
    df_sin["monto_cercano_suma_asegurada"] = (df_sin["monto_reclamado"] >= 0.95 * df_sin["suma_asegurada"]).astype(int)
    
    # Save processed dataframe
    if save:
        out_path = Path(PROC_DIR) / "siniestros_processed.csv"
        df_sin.to_csv(out_path, index=False)
        print(f"Processed features saved to: {out_path}")
        
    return df_sin

if __name__ == "__main__":
    build_features()
