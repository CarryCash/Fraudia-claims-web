# scripts/check_model.py
"""Carga y muestra información del modelo entrenado."""
from pathlib import Path
# pyrefly: ignore [missing-import]
import joblib

def main() -> None:
    model_path = Path("models") / "random_forest_fraud.joblib"
    features_path = Path("models") / "features.joblib"

    model = joblib.load(model_path)
    features = joblib.load(features_path)

    print("✔️ Modelo cargado sin errores")
    print("Tipo de modelo:", type(model))
    print("Número de características usadas:", len(features))
    print("Nombres de features (primeros 5):", features[:5])

if __name__ == "__main__":
    main()
