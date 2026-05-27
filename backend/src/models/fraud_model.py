# src/models/fraud_model.py
"""Script to train and persist the Machine Learning fraud classification model.

Uses RandomForestClassifier from Scikit-Learn to learn patterns of fraud.
Calculates performance metrics (Precision, Recall, F1, AUC) and saves the model to models/.
"""

import os
# pyrefly: ignore [missing-import]
import joblib
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, roc_auc_score, confusion_matrix

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"
MODEL_DIR = PROJECT_ROOT / "models"

# Features selected for model training
FEATURES = [
    "monto_reclamado",
    "monto_estimado",
    "dias_desde_inicio_poliza",
    "dias_desde_fin_poliza",
    "dias_entre_ocurrencia_reporte",
    "historial_siniestros_asegurado",
    "freq_asegurado_18m",
    "freq_vehiculo_18m",
    "freq_conductor_18m",
    "freq_solo_rc_previos",
    "proveedor_lista_restrictiva",
    "proveedor_casos_observados_anio",
    "documento_alterado",
    "falta_documento_obligatorio",
    "relato_ilogico",
    "accidente_madrugada",
    "tercero_huye_sin_camaras",
    "narrativa_similitud_score",
    "narrativa_clonada",
    "monto_cercano_suma_asegurada"
]

def load_data() -> pd.DataFrame:
    """Load the processed dataset containing engineered features."""
    csv_path = PROCESSED_DATA_DIR / "siniestros_processed.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"Processed features file not found at: {csv_path}. Run build_features first.")
    return pd.read_csv(csv_path)

def train_model():
    """Train, evaluate and save the fraud model."""
    df = load_data()
    
    # Target label
    target = "etiqueta_fraude_simulada"
    if target not in df.columns:
        raise ValueError(f"Target column '{target}' not found in the dataset.")
        
    # Prepare X and y
    # Ensure all required features are present
    missing_features = [f for f in FEATURES if f not in df.columns]
    if missing_features:
        raise ValueError(f"Features missing from processed data: {missing_features}")
        
    X = df[FEATURES].fillna(0)
    y = df[target]
    
    # Train-Test Split for evaluation
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    print(f"Training set size: {X_train.shape[0]} samples")
    print(f"Testing set size: {X_test.shape[0]} samples")
    print(f"Fraud prevalence in train: {y_train.mean():.2%}, test: {y_test.mean():.2%}")
    
    # Initialize Random Forest classifier
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        random_state=42,
        class_weight="balanced", # Handle class imbalance if any
        n_jobs=-1
    )
    
    # Fit model on training set
    model.fit(X_train, y_train)
    
    # Evaluate
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]
    
    print("\n--- Model Evaluation ---")
    print(classification_report(y_test, y_pred))
    
    auc = roc_auc_score(y_test, y_prob)
    print(f"ROC-AUC Score: {auc:.4f}")
    
    cm = confusion_matrix(y_test, y_pred)
    print("Confusion Matrix:")
    print(cm)
    
    # Fit model on full dataset for production/deployment
    print("\nFitting model on the entire dataset...")
    final_model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        random_state=42,
        class_weight="balanced",
        n_jobs=-1
    )
    final_model.fit(X, y)
    
    # Save the model
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    model_path = MODEL_DIR / "random_forest_fraud.joblib"
    joblib.dump(final_model, model_path)
    
    # Save feature list to ensure consistency in predictions
    feature_path = MODEL_DIR / "features.joblib"
    joblib.dump(FEATURES, feature_path)
    
    print(f"Trained model saved to: {model_path}")
    print(f"Features list saved to: {feature_path}")

if __name__ == "__main__":
    train_model()
