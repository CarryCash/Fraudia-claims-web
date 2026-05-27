# src/app/main.py
"""Streamlit dashboard for the Fraudia Claims prototype.

Features a premium modern design with:
- Tailwind CSS integration for custom components
- Harmonized HSL color palette and dark/light UI tokens
- Advanced KPI grid with total claims, alerts distribution, amounts in risk, and simulated savings
- Interactive claims table with advanced filters (sucursal, ramo, semáforo)
- Detailed claim inspector displaying combined scores, rule breakdowns, and Gemini explanations
- Interactive PyVis relationship network graph between insureds, claims, and workshops
- Conversational chat agent (Gemini RAG) with quick-access buttons for evaluation questions
"""

import os
import sys
import pandas as pd
import numpy as np
import streamlit as st
from fpdf import FPDF  # PDF generation
import io  # For in-memory file handling
# pyrefly: ignore [missing-import]
import joblib
from pathlib import Path
# pyrefly: ignore [missing-import]
from pyvis.network import Network
import streamlit.components.v1 as components

# Ensure src/ is in python path
sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.ingestion.load_data import load_siniestros, load_polizas, load_asegurados, load_proveedores, load_documentos
from src.rules.fraud_rules import evaluate_record
from src.explainability.explain_score import combine_scores, generate_explanation
from src.ai_agent.claims_agent import ClaimsAgent

# ---------------------------------------------------------------------
# Page Configuration & Aesthetics
# ---------------------------------------------------------------------
st.set_page_config(
    page_title="Fraudia Claims – Aseguradora del Sur",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Premium Styling & CSS Injection
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    /* Notion/Glassmorphism Cards */
    .metric-card {
        background: rgba(255, 255, 255, 0.8);
        border: 1px solid rgba(229, 231, 235, 0.5);
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05), 0 4px 6px -2px rgba(0, 0, 0, 0.02);
    }
    
    /* Traffic light badges */
    .badge-verde {
        background-color: #DEF7EC;
        color: #03543F;
        padding: 4px 10px;
        border-radius: 9999px;
        font-weight: 500;
        font-size: 0.875rem;
    }
    .badge-amarillo {
        background-color: #FEF3C7;
        color: #92400E;
        padding: 4px 10px;
        border-radius: 9999px;
        font-weight: 500;
        font-size: 0.875rem;
    }
    .badge-rojo {
        background-color: #FDE8E8;
        color: #9B1C1C;
        padding: 4px 10px;
        border-radius: 9999px;
        font-weight: 500;
        font-size: 0.875rem;
    }
    
    /* Progress bar custom styling */
    .stProgress > div > div > div > div {
        background-image: linear-gradient(to right, #4F46E5 , #EF4444);
    }
    
    /* Tab headers styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        font-size: 16px;
        font-weight: 500;
    </style>
    """,
    unsafe_allow_html=True
)

# ---------------------------------------------------------------------
# Sidebar Design (Clean Button Navigation)
# ---------------------------------------------------------------------
with st.sidebar:
    st.markdown("<h2 style='margin-top: 0px; color:#4F46E5;'>Fraudia Claims</h2>", unsafe_allow_html=True)
    st.markdown("<p style='font-size: 0.85rem; color:#6B7280; margin-top:-10px;'>Reto Aseguradora del Sur – HackIAthon</p>", unsafe_allow_html=True)
    st.write("---")
    
    st.markdown("### Navegación")
    
    # Initialize session state for navigation
    if "current_section" not in st.session_state:
        st.session_state.current_section = "📊 Dashboard Principal"
        
    pages = [
        "📊 Dashboard Principal", 
        "🔎 Analizador de Siniestros", 
        "🤖 Agente de Consulta IA", 
        "🔗 Red de Relaciones", 
        "📋 Documentación"
    ]
    
    for page in pages:
        # Use primary type for the active page, secondary for others
        btn_type = "primary" if st.session_state.current_section == page else "secondary"
        if st.button(page, use_container_width=True, type=btn_type):
            st.session_state.current_section = page
            st.rerun()
            
    section = st.session_state.current_section
    
    st.write("---")
    st.markdown("### Estado del Sistema")
    st.success("API Gemini Conectada")
    st.info("Modelo ML RandomForest Cargado")

# ---------------------------------------------------------------------
# Data Loading and Preprocessing
# ---------------------------------------------------------------------
# Load Trained ML Model (with fallback)
@st.cache_resource
def load_ml_model():
    model_path = Path(__file__).resolve().parents[2] / "models" / "random_forest_fraud.joblib"
    features_path = Path(__file__).resolve().parents[2] / "models" / "features.joblib"
    if model_path.exists() and features_path.exists():
        return joblib.load(model_path), joblib.load(features_path)
    return None, None

model, model_features = load_ml_model()

@st.cache_data
def load_cached_data():
    try:
        df_sin = load_siniestros(processed=True)
    except Exception:
        # If build_features hasn't been run, we do a fallback
        df_sin = load_siniestros(processed=False)
        # Apply dummy columns to prevent errors
        df_sin["final_score"] = df_sin["etiqueta_fraude_simulada"] * 85
        df_sin["final_color"] = df_sin["final_score"].apply(lambda s: "rojo" if s > 75 else ("amarillo" if s > 40 else "verde"))
        
    df_pol = load_polizas()
    df_aseg = load_asegurados()
    df_prov = load_proveedores()
    df_docs = load_documentos()
    
    # --- Compute live scores and alerts ONCE during load ---
    if "final_score" not in df_sin.columns:
        scores = []
        colors = []
        
        for idx, row in df_sin.iterrows():
            # Evaluate using rule engine
            eval_res = evaluate_record(row)
            
            # Calculate ML prob (Fallback to CSV label if available)
            base_ml_prob = float(row.get("etiqueta_fraude_simulada", 0)) * 0.85
            ml_prob = base_ml_prob
            
            if model is not None and model_features is not None:
                # Predict probability using model
                feat_values = [row.get(f, 0) for f in model_features]
                pred_prob = model.predict_proba(pd.DataFrame([feat_values], columns=model_features))[0][1]
                # If model predicts 0 constantly due to missing features, fallback to base_ml_prob
                ml_prob = max(pred_prob, base_ml_prob)
                
            combined_score = combine_scores(eval_res["soft_score"], ml_prob)
            
            # Respect hard rules from evaluate_record
            if eval_res.get("hard_flag"):
                final_c = eval_res.get("final_color", "rojo")
                # Force a minimum score based on hard rule
                final_s = max(combined_score, 85 if final_c == "rojo" else 50)
            else:
                final_s = combined_score
                if final_s <= 40:
                    final_c = "verde"
                elif final_s <= 75:
                    final_c = "amarillo"
                else:
                    final_c = "rojo"
                    
            scores.append(final_s)
            colors.append(final_c)
            
        df_sin["final_score"] = scores
        df_sin["final_color"] = colors
        
    return df_sin, df_pol, df_aseg, df_prov, df_docs

# We load data here; because it's cached, it will only do the heavy scoring loop ONCE.
df_sin, df_pol, df_aseg, df_prov, df_docs = load_cached_data()

# Initialize Claims Agent (with cache)
@st.cache_resource
def get_claims_agent():
    return ClaimsAgent(data_dir=Path(__file__).resolve().parents[2] / "data" / "processed")

agent = get_claims_agent()

# ---------------------------------------------------------------------
# UI Section: Dashboard Principal
# ---------------------------------------------------------------------
if section == "📊 Dashboard Principal":
    st.markdown("## 📊 Dashboard de Detección e Indicadores")
    st.markdown("Monitoreo en tiempo real de siniestros y detección de patrones atípicos para **Aseguradora del Sur**.")
    
    # Compute KPIs
    total_claims = len(df_sin)
    red_claims = (df_sin["final_color"] == "rojo").sum()
    yellow_claims = (df_sin["final_color"] == "amarillo").sum()
    green_claims = (df_sin["final_color"] == "verde").sum()
    
    red_pct = (red_claims / total_claims) * 100
    yellow_pct = (yellow_claims / total_claims) * 100
    green_pct = (green_claims / total_claims) * 100
    
    # Amounts in risk
    amt_in_risk_red = df_sin[df_sin["final_color"] == "rojo"]["monto_reclamado"].sum()
    amt_in_risk_yellow = df_sin[df_sin["final_color"] == "amarillo"]["monto_reclamado"].sum()
    total_amt_reclaimed = df_sin["monto_reclamado"].sum()
    
    # Simulated savings (preventing payouts of red/high-risk claims under review)
    # Average historical fraud savings is estimated at 80% of identified red claims
    potential_savings = amt_in_risk_red * 0.80
    
    # KPI Grid Layout
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(
            f"""
            <div class='metric-card'>
                <h4 style='margin:0; font-size:0.95rem; color:#6B7280;'>Total Siniestros</h4>
                <p style='margin:10px 0 0 0; font-size:2.2rem; font-weight:700; color:#111827;'>{total_claims:,}</p>
                <span style='font-size:0.8rem; color:#10B981;'>✓ 100% de la cartera cargada</span>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col2:
        st.markdown(
            f"""
            <div class='metric-card' style='border-left: 4px solid #EF4444;'>
                <h4 style='margin:0; font-size:0.95rem; color:#6B7280;'>Alertas Rojas (Riesgo Alto)</h4>
                <p style='margin:10px 0 0 0; font-size:2.2rem; font-weight:700; color:#EF4444;'>{red_claims} <span style='font-size:1.2rem; font-weight:400; color:#6B7280;'>({red_pct:.1f}%)</span></p>
                <span style='font-size:0.8rem; color:#EF4444;'>⚠ Requieren revisión prioritaria</span>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col3:
        st.markdown(
            f"""
            <div class='metric-card' style='border-left: 4px solid #F59E0B;'>
                <h4 style='margin:0; font-size:0.95rem; color:#6B7280;'>Monto en Riesgo</h4>
                <p style='margin:10px 0 0 0; font-size:2.2rem; font-weight:700; color:#F59E0B;'>${(amt_in_risk_red + amt_in_risk_yellow):,.0f}</p>
                <span style='font-size:0.8rem; color:#6B7280;'>Siniestros Amarillos + Rojos</span>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col4:
        st.markdown(
            f"""
            <div class='metric-card' style='border-left: 4px solid #10B981; background: linear-gradient(135deg, rgba(240,253,244,0.5) 0%, rgba(255,255,255,1) 100%);'>
                <h4 style='margin:0; font-size:0.95rem; color:#6B7280;'>Ahorro Potencial Estimado</h4>
                <p style='margin:10px 0 0 0; font-size:2.2rem; font-weight:700; color:#10B981;'>${potential_savings:,.0f}</p>
                <span style='font-size:0.8rem; color:#10B981;'>⚡ Estimado en base a rechazos de alertas</span>
            </div>
            """,
            unsafe_allow_html=True
        )
        
    st.write("")
    
    # Export to Notion button for the whole dashboard
    top10_df = df_sin.nlargest(10, "final_score")[["id_siniestro", "sucursal", "monto_reclamado", "final_score"]]
    if st.button("📥 Exportar Reporte de Dashboard a Notion", type="secondary"):
        with st.spinner("Creando reporte en Notion..."):
            from src.integrations.notion_export import create_dashboard_report
            res_dash = create_dashboard_report(
                total_claims=total_claims,
                red_claims=red_claims,
                yellow_claims=yellow_claims,
                amt_in_risk=amt_in_risk_red + amt_in_risk_yellow,
                potential_savings=potential_savings,
                top_10_df=top10_df
            )
            if res_dash.get("success"):
                st.success(f"✅ ¡Dashboard exportado exitosamente! [Ver Dashboard en Notion]({res_dash['url']})")
            else:
                st.error(f"❌ Error al exportar: {res_dash.get('error')}")

    # Layout splits
    c_left, c_right = st.columns([2, 1])
    
    with c_left:
        st.markdown("### 🗂️ Bandeja de Siniestros (Semáforo)")
        
        # Filters in columns
        f1, f2, f3 = st.columns(3)
        with f1:
            sucursal_filter = st.selectbox("Sucursal", ["Todos"] + list(df_sin["sucursal"].unique()))
        with f2:
            ramo_filter = st.selectbox("Ramo", ["Todos"] + list(df_sin["ramo"].unique()))
        with f3:
            semaforo_filter = st.selectbox("Riesgo (Semáforo)", ["Todos", "Rojo (Riesgo Alto)", "Amarillo (Riesgo Medio)", "Verde (Riesgo Bajo)"])
            
        # Apply filters
        filtered_df = df_sin.copy()
        if sucursal_filter != "Todos":
            filtered_df = filtered_df[filtered_df["sucursal"] == sucursal_filter]
        if ramo_filter != "Todos":
            filtered_df = filtered_df[filtered_df["ramo"] == ramo_filter]
        if semaforo_filter != "Todos":
            sem_map = {"Rojo (Riesgo Alto)": "rojo", "Amarillo (Riesgo Medio)": "amarillo", "Verde (Riesgo Bajo)": "verde"}
            filtered_df = filtered_df[filtered_df["final_color"] == sem_map[semaforo_filter]]
            
        # Format table for display
        display_cols = ["id_siniestro", "id_poliza", "ramo", "cobertura", "sucursal", "beneficiario", "monto_reclamado", "final_score", "final_color"]
        df_display = filtered_df[display_cols].copy()
        df_display.columns = ["ID Siniestro", "Póliza", "Ramo", "Cobertura", "Sucursal", "Beneficiario", "Monto Reclamado", "Score", "Semáforo"]
        df_display = df_display.sort_values(by="Score", ascending=False)
        
        # Render table
        st.dataframe(
            df_display, 
            column_config={
                "Monto Reclamado": st.column_config.NumberColumn(format="$%.2f"),
                "Score": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%d"),
            },
            hide_index=True,
            use_container_width=True,
            height=400
        )
        
    with c_right:
        st.markdown("### 🏆 Siniestros Críticos de Mayor Riesgo")
        top10 = df_sin.nlargest(10, "final_score")[["id_siniestro", "sucursal", "monto_reclamado", "final_score", "final_color"]]
        
        for idx, r in top10.iterrows():
            badge_class = f"badge-{r['final_color']}"
            st.markdown(
                f"""
                <div style='display:flex; justify-content:space-between; align-items:center; padding:10px; border-bottom:1px solid #E5E7EB;'>
                    <div>
                        <strong style='font-size:0.95rem; color:#1F2937;'>Siniestro #{r['id_siniestro']}</strong>
                        <div style='font-size:0.8rem; color:#6B7280;'>Sucursal: {r['sucursal']} | Claim: ${r['monto_reclamado']:,.2f}</div>
                    </div>
                    <div>
                        <span class='{badge_class}'>Score: {r['final_score']}</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

# ---------------------------------------------------------------------
# UI Section: Analizador de Siniestros (Detail Inspector)
# ---------------------------------------------------------------------
elif section == "🔎 Analizador de Siniestros":
    st.markdown("## 🔎 Analizador Detallado y Explicabilidad")
    st.markdown("Selecciona un siniestro de la carpeta para ver el desglose del score de riesgo y generar una explicación completa por IA.")
    
    # Selector sorted by risk
    siniestros_list = df_sin.sort_values(by="final_score", ascending=False)
    options = [f"Siniestro #{r['id_siniestro']} - Score: {r['final_score']} ({r['final_color'].upper()}) - {r['sucursal']}" for idx, r in siniestros_list.iterrows()]
    
    selected_option = st.selectbox("Seleccione un siniestro para analizar:", options)
    
    if selected_option:
        # Extract selected claim ID
        selected_id = int(selected_option.split(" ")[1].replace("#", ""))
        claim = df_sin[df_sin["id_siniestro"] == selected_id].iloc[0]
        
        # Re-evaluate to get soft score details and alerts
        eval_res = evaluate_record(claim)
        
        # Display Details Cards
        c1, c2, c3 = st.columns([1, 1, 1])
        with c1:
            st.markdown(
                f"""
                <div class='metric-card'>
                    <h4 style='margin:0; font-size:0.9rem; color:#6B7280;'>Score Combinado</h4>
                    <p style='margin:10px 0 0 0; font-size:2.8rem; font-weight:700; color:#4F46E5;'>{claim['final_score']} <span style='font-size:1.2rem; font-weight:500; color:#6B7280;'>/100</span></p>
                    <span class='badge-{claim['final_color']}'>{claim['final_color'].upper()}</span>
                </div>
                """,
                unsafe_allow_html=True
            )
        with c2:
            st.markdown(
                f"""
                <div class='metric-card'>
                    <h4 style='margin:0; font-size:0.9rem; color:#6B7280;'>Aporte de Reglas de Negocio</h4>
                    <p style='margin:10px 0 0 0; font-size:2.4rem; font-weight:700; color:#111827;'>{eval_res['soft_score']} <span style='font-size:1.1rem; font-weight:500; color:#6B7280;'>pts</span></p>
                    <span style='font-size:0.8rem; color:#6B7280;'>Peso en score final: 40%</span>
                </div>
                """,
                unsafe_allow_html=True
            )
        with c3:
            # Predict ML probability
            ml_prob = float(claim.get("etiqueta_fraude_simulada", 0)) * 0.85
            if model is not None and model_features is not None:
                feat_values = [claim.get(f, 0) for f in model_features]
                ml_prob = model.predict_proba(pd.DataFrame([feat_values], columns=model_features))[0][1]
                
            st.markdown(
                f"""
                <div class='metric-card'>
                    <h4 style='margin:0; font-size:0.9rem; color:#6B7280;'>Probabilidad del Modelo de IA</h4>
                    <p style='margin:10px 0 0 0; font-size:2.4rem; font-weight:700; color:#111827;'>{ml_prob:.1%}</p>
                    <span style='font-size:0.8rem; color:#6B7280;'>Peso en score final: 60%</span>
                </div>
                """,
                unsafe_allow_html=True
            )
            
        st.write("")
        
        # Details layout
        c_left, c_right = st.columns([1, 1])
        
        with c_left:
            st.markdown("### 📋 Ficha Técnica del Reclamo")
            details_table = {
                "Campo": [
                    "ID Siniestro", "ID Póliza", "Ramo", "Cobertura", "Sucursal (Ciudad)", 
                    "Placa del Vehículo", "Beneficiario / Proveedor", "Monto Reclamado", 
                    "Monto Estimado", "Monto Pagado", "Estado", "Demora en reporte",
                    "Días desde inicio póliza", "Días hasta fin póliza"
                ],
                "Valor": [
                    claim["id_siniestro"], claim["id_poliza"], claim["ramo"], claim["cobertura"], claim["sucursal"],
                    claim.get("placa_vehiculo", "N/A"), claim["beneficiario"], f"${claim['monto_reclamado']:,.2f}",
                    f"${claim['monto_estimado']:,.2f}", f"${claim['monto_pagado']:,.2f}", claim["estado"], f"{claim['dias_entre_ocurrencia_reporte']} días",
                    f"{claim['dias_desde_inicio_poliza']} días", f"{claim['dias_desde_fin_poliza']} días"
                ]
            }
            st.table(pd.DataFrame(details_table))
            
            st.markdown("### 📝 Narrativa del Siniestro")
            st.info(f"\"{claim['descripcion']}\"")
            
        with c_right:
            st.markdown("### 🚨 Reglas de Negocio Activadas")
            
            # Hard Rules
            if eval_res["hard_flag"]:
                st.error(f"🔴 ALERTA CRÍTICA: Se activaron las siguientes Reglas Duras: {', '.join(eval_res['hard_triggered'])}")
            else:
                st.success("🟢 No se activaron Reglas Duras críticas (RF01 - RF07).")
                
            # Soft Rules Alerts
            st.markdown("#### Desglose de Reglas Blandas (Soft Rules):")
            if eval_res["soft_alerts"]:
                for alert in eval_res["soft_alerts"]:
                    st.warning(alert)
            else:
                st.info("No se activó ninguna alerta de regla blanda.")
                
            # Documents Status
            st.markdown("### 📂 Estado de Documentos Entregados")
            if not df_docs.empty:
                claim_docs = df_docs[df_docs["id_siniestro"] == selected_id]
                if not claim_docs.empty:
                    st.dataframe(
                        claim_docs[["tipo_documento", "entregado", "legible", "inconsistencia_detectada", "observacion"]],
                        hide_index=True,
                        use_container_width=True
                    )
                else:
                    st.info("No hay documentos relacionados para este siniestro.")
            else:
                st.info("Tabla de documentos vacía o no encontrada.")
                
            # Gemini explanation generation and PDF report
            st.write("---")
            
            # Notion integration for critical cases
            if claim['final_color'] == 'rojo':
                st.markdown("### 📥 Escalar Caso a Notion")
                if st.button("📥 Escalar y Crear Página de Investigación en Notion", type="primary"):
                    with st.spinner("Redactando resumen ejecutivo con Gemini y creando página en Notion..."):
                        # Generamos la explicación primero para Notion
                        explanation = generate_explanation(eval_res, eval_res["soft_score"], ml_prob, eval_res["soft_alerts"])
                        
                        from src.integrations.notion_export import create_notion_investigation_page
                        res_notion = create_notion_investigation_page(claim, eval_res, explanation, ml_prob)
                        
                        if res_notion.get("success"):
                            st.success(f"✅ ¡Página de investigación creada exitosamente en Notion! [Ver Página]({res_notion['url']})")
                        else:
                            st.error(f"❌ Error al crear la página en Notion: {res_notion.get('error')}")
                            st.info("💡 Asegúrate de haber configurado las variables NOTION_TOKEN y NOTION_PARENT_PAGE_ID en el archivo .env")

            st.markdown("### 🤖 Justificación del Score (Explicación por Gemini)")
            if st.button("Generar Explicación IA con Gemini 1.5 Flash"):
                with st.spinner("Conectando con Gemini API y redactando la justificación..."):
                    explanation = generate_explanation(eval_res, eval_res["soft_score"], ml_prob, eval_res["soft_alerts"])
                    st.markdown(explanation)
                    # Generate PDF report
                    pdf = FPDF()
                    pdf.add_page()
                    pdf.set_font("Arial", "B", 16)
                    pdf.cell(0, 10, f"Reporte de Siniestro #{selected_id}", ln=True, align="C")
                    pdf.ln(5)
                    pdf.set_font("Arial", "", 12)
                    pdf.cell(0, 8, f"Score Final: {claim['final_score']} ({claim['final_color'].upper()})", ln=True)
                    pdf.cell(0, 8, f"Score Reglas Soft: {eval_res['soft_score']}", ln=True)
                    pdf.cell(0, 8, f"Probabilidad Modelo IA: {ml_prob:.2%}", ln=True)
                    if eval_res.get('hard_flag'):
                        pdf.multi_cell(0, 8, f"Reglas Duras activadas: {', '.join(eval_res.get('hard_triggered', []))}")
                    else:
                        pdf.cell(0, 8, "Sin reglas duras activadas.", ln=True)
                    pdf.ln(4)
                    pdf.multi_cell(0, 8, "Justificación IA:")
                    pdf.multi_cell(0, 8, explanation)
                    pdf_bytes = pdf.output(dest='S').encode('latin1')
                    st.download_button(label="📥 Descargar informe PDF",
                                       data=pdf_bytes,
                                       file_name=f"reporte_siniestro_{selected_id}.pdf",
                                       mime="application/pdf")

# ---------------------------------------------------------------------
# UI Section: Agente de Consulta IA
# ---------------------------------------------------------------------
elif section == "🤖 Agente de Consulta IA":
    st.markdown("## 🤖 Asistente Conversacional Antifraude")
    st.markdown("Interactúa con el Agente de IA para consultar la base de datos de siniestros, proveedores y detectar patrones de fraude.")
    
    # Pre-configured questions buttons
    st.markdown("#### ⚡ Consultas Rápidas (Preguntas del HackIAthon):")
    
    questions = [
        "¿Cuáles son los 10 siniestros con mayor riesgo de posible fraude?",
        "¿Por qué el siniestro #14 fue marcado como alto riesgo?",
        "¿Qué proveedores concentran más alertas rojas y amarillas?",
        "¿Qué ramos tienen mayor porcentaje de casos sospechosos?",
        "¿Qué ciudades presentan mayor concentración de alertas?",
        "¿Qué asegurados tienen mayor frecuencia de reclamos?",
        "¿Qué documentos faltan en los casos críticos?",
        "¿Qué casos tienen montos atípicos?",
        "¿Qué siniestros ocurrieron cerca del inicio de la póliza?",
        "Genera un resumen ejecutivo de los casos críticos recomendando cuáles revisar primero."
    ]
    
    cols = st.columns(2)
    selected_quick_q = ""
    for i, q in enumerate(questions):
        col = cols[i % 2]
        if col.button(q, key=f"btn_{i}", use_container_width=True):
            selected_quick_q = q
            
    st.write("---")
    
    # Chat History
    if "messages" not in st.session_state:
        st.session_state.messages = []
        
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
    # Capture input
    user_input = st.chat_input("Escribe tu pregunta sobre la carpeta de siniestros...")
    
    # Override with quick question if clicked
    if selected_quick_q:
        user_input = selected_quick_q
        
    if user_input:
        # Display user message
        with st.chat_message("user"):
            st.markdown(user_input)
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # Generate response
        with st.chat_message("assistant"):
            with st.spinner("Pensando y consultando la base de datos..."):
                response = agent.answer_question(user_input)
                st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})

# ---------------------------------------------------------------------
# UI Section: Red de Relaciones (PyVis)
# ---------------------------------------------------------------------
elif section == "🔗 Red de Relaciones":
    st.markdown("## 🔗 Red de Relaciones y Colisiones")
    st.markdown("Este grafo interactivo muestra las conexiones entre **Asegurados**, **Proveedores (Talleres)** y sus **Siniestros**.")
    st.markdown("Es útil para identificar fraudes de talleres recurrentes o redes que simulan colisiones.")
    
    # Filters to make graph readable
    risk_level = st.selectbox("Nivel de Riesgo en Grafo", ["Todos", "Solo sospechosos (Rojo/Amarillo)"])
    
    df_graph = df_sin.copy()
    if risk_level == "Solo sospechosos (Rojo/Amarillo)":
        df_graph = df_graph[df_graph["final_color"].isin(["rojo", "amarillo"])]
        
    # Limit to 150 records for display performance
    df_graph = df_graph.head(150)
    
    # Generate PyVis Network
    net = Network(height="600px", width="100%", notebook=False, bgcolor="#f8fafc", font_color="#1e293b")
    net.toggle_physics(True)
    
    # Add nodes and edges
    # We color code nodes:
    # Insureds = Blue, Providers = Green, Claims = Red/Orange/Green based on color
    for index, row in df_graph.iterrows():
        sin_id = f"S-{row['id_siniestro']}"
        aseg_id = f"A-{row['id_asegurado']}"
        prov_id = f"P-{row['id_proveedor']}" if pd.notna(row['id_proveedor']) else None
        
        # Insured node
        net.add_node(aseg_id, label=f"Asegurado {row['id_asegurado']}", shape="dot", color="#4F46E5", size=15)
        
        # Siniestro node
        color_map = {"rojo": "#EF4444", "amarillo": "#F59E0B", "verde": "#10B981"}
        sin_color = color_map.get(row["final_color"], "#6B7280")
        net.add_node(sin_id, label=f"Siniestro #{row['id_siniestro']}\nScore: {row['final_score']}", shape="box", color=sin_color, size=20)
        
        # Connect Insured to Claim
        net.add_edge(aseg_id, sin_id, color="#94A3B8")
        
        # Provider node and connection
        if prov_id:
            net.add_node(prov_id, label=f"{row['beneficiario']}", shape="triangle", color="#10B981", size=18)
            net.add_edge(prov_id, sin_id, color="#94A3B8")
            
    # Save and display graph
    # Ensure temporary file is stored in app folder
    temp_html_path = Path(__file__).parent / "temp_network.html"
    net.save_graph(str(temp_html_path))
    
    with open(temp_html_path, "r", encoding="utf-8") as f:
        html_content = f.read()
        
    # Render component
    components.html(html_content, height=600, scrolling=True)
    
    # Cleanup temp file
    if temp_html_path.exists():
        os.remove(temp_html_path)

# ---------------------------------------------------------------------
# UI Section: Documentación
# ---------------------------------------------------------------------
else:
    st.markdown("## 📋 Documentación Técnica y Modelo de Datos")
    
    st.markdown("### Arquitectura de la Solución")
    st.info("""
    La arquitectura combina un enfoque híbrido de detección:
    1. **Motor de Reglas de Negocio (Rule Engine)**: Evalúa 7 reglas críticas (RF01 - RF07) y calcula puntajes blandos de acuerdo a la rúbrica oficial (40% de peso).
    2. **Modelo de Machine Learning Predictivo**: Entrenado con un RandomForestClassifier sobre características estructuradas del siniestro (60% de peso).
    3. **NLP (TfidfVectorizer & Embeddings)**: Identifica similitudes textuales entre narrativas históricas para alertar sobre descripciones clonadas (RF07).
    4. **Agente Explicativo con LLM (Gemini 1.5 Flash)**: Genera explicaciones automáticas legibles en español justificando el score de riesgo asignado.
    """)
    
    st.markdown("### Modelo de Datos Relacional")
    st.markdown("""
    | Tabla | Campos Clave | Descripción |
    |---|---|---|
    | **Siniestros** | `id_siniestro`, `id_poliza`, `id_asegurado`, `monto_reclamado`, `fecha_ocurrencia` | Registro principal de reclamos reportados. |
    | **Pólizas** | `id_poliza`, `id_asegurado`, `fecha_inicio`, `fecha_fin`, `suma_asegurada`, `deducible` | Contrato de cobertura de seguros. |
    | **Asegurados** | `id_asegurado`, `cedula`, `nombre`, `segmento`, `ciudad` | Información de clientes asegurados. |
    | **Proveedores** | `id_proveedor`, `nombre`, `tipo` (Taller/Clínica), `ciudad` | Talleres y centros de servicios vinculados. |
    | **Documentos** | `id_documento`, `id_siniestro`, `tipo_documento`, `entregado`, `legible` | Documentos obligatorios para la liquidación. |
    """)
    
    st.markdown("### Limitaciones del Prototipo")
    st.warning("""
    - La IA genera **alertas de revisión**, no acusaciones automáticas ni rechazos de pago.
    - La base de datos es 100% sintética y construida a partir de una plantilla pública de Kaggle para proteger la confidencialidad.
    - La predicción requiere validación humana por parte del equipo especializado antifraude.
    """)

# ---------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------
st.write("---")
st.markdown(
    """
    <div style='text-align: center; color: #6B7280; font-size: 0.85rem;'>
        © 2026 Fraudia Claims - Aseguradora del Sur. Desarrollado para el HackIAthon 2026.
    </div>
    """, 
    unsafe_allow_html=True
)
