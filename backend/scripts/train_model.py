# scripts/train_model.py
"""Ejecuta el pipeline completo: feature engineering → entrenamiento."""
import subprocess
import sys
from pathlib import Path

def run(cmd: str):
    print(f"$ {cmd}")
    result = subprocess.run(cmd, shell=True, check=True)
    return result

if __name__ == "__main__":
    # 1️⃣ Build features
    run("python src/features/build_features.py")
    # 2️⃣ Train model
    run("python src/models/fraud_model.py")
    print("\n✅ Entrenamiento completado. Modelos guardados en:", Path("models"))
