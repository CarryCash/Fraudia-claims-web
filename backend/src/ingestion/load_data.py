# src/ingestion/load_data.py
"""Utilities to load raw or processed CSV datasets.

Provides functions to load Siniestros, Pólizas, Asegurados, Proveedores, and Documentos.
"""

import os
# pyrefly: ignore [missing-import]
import pandas as pd
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).resolve().parents[3]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROC_DIR = PROJECT_ROOT / "data" / "processed"

def _get_dir(processed: bool) -> Path:
    return PROC_DIR if processed else RAW_DIR

def load_siniestros(processed: bool = False) -> pd.DataFrame:
    """Load the Siniestros dataset."""
    path = _get_dir(processed) / "siniestros.csv"
    if not path.exists():
        # Try processed features path if it's processed
        if processed:
            path = PROC_DIR / "siniestros_processed.csv"
        if not path.exists():
            raise FileNotFoundError(f"Claims data file not found at: {path}")
            
    df = pd.read_csv(path)
    # Parse dates if they exist
    for col in ["fecha_ocurrencia", "fecha_reporte"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df

def load_polizas(processed: bool = False) -> pd.DataFrame:
    """Load the Pólizas dataset."""
    path = _get_dir(processed) / "polizas.csv"
    if not path.exists():
        raise FileNotFoundError(f"Policies data file not found at: {path}")
    df = pd.read_csv(path)
    for col in ["fecha_inicio", "fecha_fin"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df

def load_asegurados(processed: bool = False) -> pd.DataFrame:
    """Load the Asegurados dataset."""
    path = _get_dir(processed) / "asegurados.csv"
    if not path.exists():
        raise FileNotFoundError(f"Insureds data file not found at: {path}")
    return pd.read_csv(path)

def load_proveedores(processed: bool = False) -> pd.DataFrame:
    """Load the Proveedores dataset."""
    path = _get_dir(processed) / "proveedores.csv"
    if not path.exists():
        raise FileNotFoundError(f"Providers data file not found at: {path}")
    return pd.read_csv(path)

def load_documentos(processed: bool = False) -> pd.DataFrame:
    """Load the Documentos dataset."""
    path = _get_dir(processed) / "documentos.csv"
    if not path.exists():
        raise FileNotFoundError(f"Documents data file not found at: {path}")
    df = pd.read_csv(path)
    if "fecha_emision" in df.columns:
        df["fecha_emision"] = pd.to_datetime(df["fecha_emision"], errors="coerce")
    return df
