# src/ingestion/load_data.py
"""Utilities to load processed CSV datasets.

The backend works exclusively with `data/processed` and normalizes the processed
CSV headers into the canonical field names expected by the application.
"""

from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PROC_DIR = PROJECT_ROOT / "data" / "processed"


def _read_csv(filename: str) -> pd.DataFrame:
    path = PROC_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Processed data file not found at: {path}")

    df = pd.read_csv(path, sep=";", encoding="utf-8")
    df.columns = [str(col).strip() for col in df.columns]
    df = _normalize_columns(filename, df)
    return df


def _safe_int(col):
    return pd.to_numeric(col, errors="coerce").fillna(0).astype(int)


def _normalize_columns(filename: str, df: pd.DataFrame) -> pd.DataFrame:
    if filename in {"siniestros.csv", "siniestros_processed.csv"}:
        df = df.rename(columns={
            "ID Siniestro": "id_siniestro",
            "ID Póliza": "id_poliza",
            "ID Asegurado": "id_asegurado",
            "Ramo": "ramo",
            "Placa Vehículo Asegurado": "placa_vehiculo",
            "Cobertura": "cobertura",
            "Fecha Ocurrencia": "fecha_ocurrencia",
            "Fecha Reporte": "fecha_reporte",
            "Días Ocurr→Reporte": "dias_entre_ocurrencia_reporte",
            "Monto Reclamado ($)": "monto_reclamado",
            "Monto Estimado ($)": "monto_estimado",
            "Monto Pagado ($)": "monto_pagado",
            "Estado": "estado",
            "Sucursal": "sucursal",
            "ID Proveedor": "id_proveedor",
            "Descripción del Evento": "descripcion",
            "Docs Completos": "documentos_completos",
            "Prov. Lista Restrictiva": "proveedor_lista_restrictiva",
            "Días desde Inicio Póliza": "dias_desde_inicio_poliza",
            "Días hasta Fin Póliza": "dias_desde_fin_poliza",
            "N° Reclamos Previos Asegurado": "historial_siniestros_asegurado",
            "Suma Asegurada ($)": "suma_asegurada",
            "Similitud Narrativa Máx.": "narrativa_similitud_score",
            "Número Parte Policial": "numero_parte_policial",
        })

        if "proveedor_lista_restrictiva" in df.columns:
            df["proveedor_lista_restrictiva"] = df["proveedor_lista_restrictiva"].map(
                {"Sí": 1, "Si": 1, "Sí ": 1, "No": 0, "No ": 0}
            ).fillna(df["proveedor_lista_restrictiva"])
            df["proveedor_lista_restrictiva"] = _safe_int(df["proveedor_lista_restrictiva"]) 

        if "documentos_completos" in df.columns:
            df["documentos_completos"] = df["documentos_completos"].astype(str).str.strip()

        if "historial_siniestros_asegurado" in df.columns:
            df["historial_siniestros_asegurado"] = _safe_int(df["historial_siniestros_asegurado"])

        if "suma_asegurada" in df.columns:
            df["suma_asegurada"] = pd.to_numeric(df["suma_asegurada"], errors="coerce")

        if "narrativa_similitud_score" in df.columns:
            df["narrativa_similitud_score"] = pd.to_numeric(df["narrativa_similitud_score"].astype(str).str.replace(",", "."), errors="coerce").fillna(0.0)

        if "fecha_ocurrencia" in df.columns:
            df["fecha_ocurrencia"] = pd.to_datetime(df["fecha_ocurrencia"], errors="coerce")
        if "fecha_reporte" in df.columns:
            df["fecha_reporte"] = pd.to_datetime(df["fecha_reporte"], errors="coerce")

    if filename == "polizas.csv":
        df = df.rename(columns={
            "ID Póliza": "id_poliza",
            "ID Asegurado": "id_asegurado",
            "Ramo": "ramo",
            "Fecha Inicio": "fecha_inicio",
            "Fecha Fin": "fecha_fin",
            "Suma Asegurada ($)": "suma_asegurada",
            "Prima Anual ($)": "prima_anual",
            "Canal Venta": "canal_venta",
            "Estado Póliza": "estado_poliza",
        })
        if "fecha_inicio" in df.columns:
            df["fecha_inicio"] = pd.to_datetime(df["fecha_inicio"], errors="coerce")
        if "fecha_fin" in df.columns:
            df["fecha_fin"] = pd.to_datetime(df["fecha_fin"], errors="coerce")
        if "deducible" not in df.columns:
            df["deducible"] = ""

    if filename == "asegurados.csv":
        df = df.rename(columns={
            "ID Asegurado": "id_asegurado",
            "Nombres Asegurado": "nombre",
            "Segmento": "segmento",
            "Ciudad": "ciudad",
            "Antigüedad (años)": "antiguedad",
            "N° Pólizas Activas": "numero_de_polizas",
            "N° Reclamos Últimos 12 Meses": "reclamos_ultimos_12_meses",
            "N° Reclamos Histórico Total": "reclamos_historico_total",
            "Reclamos RC sin Tercero": "reclamos_rc_sin_tercero",
            "Perfil Riesgo Histórico": "perfil_riesgo_historico",
        })
        if "cedula" not in df.columns:
            df["cedula"] = ""

    if filename == "proveedores.csv":
        df = df.loc[:, df.columns != ""]
        df = df.rename(columns={
            "ID Proveedor": "id_proveedor",
            "Nombre Proveedor": "nombre",
            "Tipo": "tipo_proveedor",
            "Ciudad": "ciudad",
            "N° Siniestros Asociados": "numero_siniestros_asociados",
            "En Lista Restrictiva": "en_lista_restrictiva",
            "Motivo Restricción": "motivo_restriccion",
            "Promedio Monto ($)": "promedio_monto",
        })
        if "en_lista_restrictiva" in df.columns:
            df["en_lista_restrictiva"] = df["en_lista_restrictiva"].astype(str).str.strip()
        if "tipo_proveedor" not in df.columns and "tipo" in df.columns:
            df["tipo_proveedor"] = df["tipo"]

    if filename == "documentos.csv":
        df = df.loc[:, df.columns != ""]
        df = df.rename(columns={
            "ID Documento": "id_documento",
            "ID Siniestro": "id_siniestro",
            "Tipo Documento": "tipo_documento",
            "Nombre Archivo PDF": "archivo_pdf",
        })
        if "entregado" not in df.columns:
            df["entregado"] = df["archivo_pdf"].fillna("").astype(str).apply(lambda x: "Sí" if x.strip() else "No")
        if "legible" not in df.columns:
            df["legible"] = "Sí"
        if "inconsistencia_detectada" not in df.columns:
            df["inconsistencia_detectada"] = "No"
        if "observacion" not in df.columns:
            df["observacion"] = ""

    return df


def load_siniestros(processed: bool = False) -> pd.DataFrame:
    """Load the Siniestros dataset from processed CSV files."""
    if processed:
        try:
            df = _read_csv("siniestros_processed.csv")
        except FileNotFoundError:
            df = _read_csv("siniestros.csv")
    else:
        df = _read_csv("siniestros.csv")

    if "id_proveedor" in df.columns and "beneficiario" not in df.columns:
        try:
            providers = load_proveedores()
            if "id_proveedor" in providers.columns and "nombre" in providers.columns:
                prov_map = providers.set_index("id_proveedor")["nombre"].to_dict()
                df["beneficiario"] = df["id_proveedor"].astype(str).map(prov_map).fillna(df["id_proveedor"].astype(str))
            else:
                df["beneficiario"] = df["id_proveedor"].astype(str)
        except FileNotFoundError:
            df["beneficiario"] = df["id_proveedor"].astype(str)

    for col in ["fecha_ocurrencia", "fecha_reporte"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


def load_polizas(processed: bool = False) -> pd.DataFrame:
    """Load the Pólizas dataset from processed CSV files."""
    df = _read_csv("polizas.csv")
    for col in ["fecha_inicio", "fecha_fin"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


def load_asegurados(processed: bool = False) -> pd.DataFrame:
    """Load the Asegurados dataset from processed CSV files."""
    df = _read_csv("asegurados.csv")
    if "cedula" not in df.columns:
        df["cedula"] = ""
    return df


def load_proveedores(processed: bool = False) -> pd.DataFrame:
    """Load the Proveedores dataset from processed CSV files."""
    df = _read_csv("proveedores.csv")
    if "tipo_proveedor" not in df.columns and "tipo" in df.columns:
        df["tipo_proveedor"] = df["tipo"]
    return df


def load_documentos(processed: bool = False) -> pd.DataFrame:
    """Load the Documentos dataset from processed CSV files."""
    df = _read_csv("documentos.csv")
    if "fecha_emision" in df.columns:
        df["fecha_emision"] = pd.to_datetime(df["fecha_emision"], errors="coerce")
    return df
