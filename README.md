# Fraudia Claims – Detector de Posibles Fraudes en Siniestros

Este repositorio contiene el prototipo solicitado para el **HackIAthon 2026 – Reto Aseguradora del Sur**.

## 🗂️ Estructura del proyecto
```
fraudia-claims/
├─ README.md                 # ↗ este archivo
├─ requirements.txt          # Dependencias Python
├─ .env.example              # Variables de entorno (Gemini API, etc.)
├─ data/
│   ├─ raw/                 # Datasets sintéticos (CSV)
│   └─ processed/           # Datasets listos para modelado
├─ notebooks/
│   ├─ synthetic/           # Generación de datos sintéticos
│   ├─ 01_exploracion_datos.ipynb
│   ├─ 02_modelo_fraude.ipynb
│   └─ 03_evaluacion_modelo.ipynb
├─ src/
│   ├─ ingestion/load_data.py
│   ├─ features/build_features.py
│   ├─ rules/fraud_rules.py
│   ├─ models/fraud_model.py
│   ├─ explainability/explain_score.py
│   ├─ ai_agent/claims_agent.py
│   └─ app/main.py
├─ docs/
│   ├─ arquitectura.md
│   ├─ modelo_datos.md
│   ├─ reglas_negocio.md
│   ├─ uso_ia.md
│   └─ limitaciones.md
├─ tests/
│   └─ test_rules.py
└─ presentation/pitch.pdf
```

## 🚀 Inicio rápido
1. **Crear entorno virtual**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```
2. **Instalar dependencias**
   ```bash
   pip install -r backend/requirements.txt
   ```
3. **Configurar variables** – Copia `.env.example` a `.env` y agrega tu clave de Gemini API.
4. **Generar datos sintéticos** – Abre el notebook `notebooks/synthetic/generate_synthetic.ipynb` en Google Colab y ejecútalo.
5. **Ejecutar la app**
   ```bash
   streamlit run src/app/main.py
   ```
   La UI está basada en Streamlit + Tailwind CSS (via CDN).

## 📚 Documentación adicional
- `docs/arquitectura.md` – Diagrama y descripción de la arquitectura.
- `docs/uso_ia.md` – Cómo funciona el agente explicativo (RAG con Gemini 1.5 Flash).

---
*Este proyecto mantiene la confidencialidad de datos al usar únicamente datasets sintéticos.*
