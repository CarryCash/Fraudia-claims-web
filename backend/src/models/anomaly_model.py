# src/models/anomaly_model.py
"""Script to train and persist the Anomaly Detection (Isolation Forest) model.

Uses IsolationForest from Scikit-Learn to detect outliers/anomalies in the data.
"""

import os
# pyrefly: ignore [missing-import]
import joblib
import pandas as pd
from pathlib import Path
from sklearn.ensemble import IsolationForest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"
MODEL_DIR = PROJECT_ROOT / "models"

# Features selected for anomaly detection (typically numerical/continuous)
ANOMALY_FEATURES = [
    "monto_reclamado",
    "monto_estimado",
    "dias_desde_inicio_poliza",
    "dias_desde_fin_poliza",
    "dias_entre_ocurrencia_reporte",
    "freq_asegurado_18m",
    "freq_vehiculo_18m",
    "freq_conductor_18m",
    "freq_solo_rc_previos",
    "proveedor_casos_observados_anio",
    "narrativa_similitud_score"
]

def load_data() -> pd.DataFrame:
    """Load the processed dataset containing engineered features."""
    csv_path = PROCESSED_DATA_DIR / "siniestros_processed.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"Processed features file not found at: {csv_path}. Run build_features first.")
    return pd.read_csv(csv_path)

def train_anomaly_model():
    """Train and save the Isolation Forest model."""
    print("Loading data for Anomaly Detection...")
    df = load_data()
    
    missing_features = [f for f in ANOMALY_FEATURES if f not in df.columns]
    if missing_features:
        raise ValueError(f"Features missing from processed data: {missing_features}")
        
    X = df[ANOMALY_FEATURES].fillna(0)
    
    print(f"Training Isolation Forest with {X.shape[0]} samples and {X.shape[1]} features...")
    
    # Initialize Isolation Forest
    # contamination is the expected proportion of outliers (frauds or weird cases)
    # 0.05 means we expect roughly 5% of cases to be anomalous
    model = IsolationForest(
        n_estimators=100,
        contamination=0.05,
        random_state=42,
        n_jobs=-1
    )
    
    # Fit model on full dataset
    model.fit(X)
    
    # Evaluate (just to show how many it flagged)
    predictions = model.predict(X)
    anomalies_count = (predictions == -1).sum()
    print(f"Number of anomalies detected in training data: {anomalies_count} ({(anomalies_count / len(X)):.2%})")
    
    # Save the model
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    model_path = MODEL_DIR / "isolation_forest.joblib"
    joblib.dump(model, model_path)
    
    # Save feature list to ensure consistency in predictions
    feature_path = MODEL_DIR / "anomaly_features.joblib"
    joblib.dump(ANOMALY_FEATURES, feature_path)
    
    print(f"Trained Isolation Forest model saved to: {model_path}")
    print(f"Anomaly features list saved to: {feature_path}")

if __name__ == "__main__":
    train_anomaly_model()
