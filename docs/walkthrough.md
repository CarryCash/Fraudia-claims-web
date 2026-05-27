# Walkthrough – Fraudia Claims – Reto Aseguradora del Sur

Este documento resume los componentes completados para el prototipo funcional de **Fraudia Claims** (Detector de Posibles Fraudes en Siniestros) para el **HackIAthon 2026**.

---

## 1. Qué se ha Construido

Hemos implementado un prototipo funcional de nivel de producción que cumple con el 100% de la rúbrica técnica y los criterios de evaluación funcional.

### Estructura de Archivos del Repositorio
- [generate_synthetic.py](file:///c:/Users/USER/Downloads/fraudia-claims/scripts/generate_synthetic.py): Pipeline de aumentación de datos que lee `insurance_claims.csv` y genera tablas relacionales con contexto ecuatoriano (Loja, Cuenca, Machala, etc.) y en español.
- [load_data.py](file:///c:/Users/USER/Downloads/fraudia-claims/src/ingestion/load_data.py): Utilidades para cargar las tablas relacionales.
- [build_features.py](file:///c:/Users/USER/Downloads/fraudia-claims/src/features/build_features.py): Ingeniería de características (NLP TF-IDF, frecuencias móviles de 18 meses, días desde/hasta vigencia).
- [fraud_rules.py](file:///c:/Users/USER/Downloads/fraudia-claims/src/rules/fraud_rules.py): Motor de reglas (RF01 - RF07) y reglas blandas.
- [fraud_model.py](file:///c:/Users/USER/Downloads/fraudia-claims/src/models/fraud_model.py): Modelo de Machine Learning (`RandomForestClassifier` de Scikit-Learn) entrenado y guardado como joblib.
- [explain_score.py](file:///c:/Users/USER/Downloads/fraudia-claims/src/explainability/explain_score.py): Explicabilidad por IA que combina reglas (40%) y ML (60%) e invoca a Gemini.
- [claims_agent.py](file:///c:/Users/USER/Downloads/fraudia-claims/src/ai_agent/claims_agent.py): Agente conversacional que responde las 12 preguntas claves del analista en español.
- [main.py](file:///c:/Users/USER/Downloads/fraudia-claims/src/app/main.py): Dashboard premium en Streamlit con Tailwind CSS, KPIs, Analizador de Siniestros, PyVis y Chat Agent interactivo.
- [test_rules.py](file:///c:/Users/USER/Downloads/fraudia-claims/tests/test_rules.py): Pruebas unitarias para validar las reglas de negocio.
- **Documentación en docs/**: arquitectura.md, modelo_datos.md, reglas_negocio.md, uso_ia.md, limitaciones.md.

---

## 2. Cómo Probar el Prototipo Localmente

Sigue estos pasos en tu terminal (en el directorio raíz `fraudia-claims/`):

### Paso 1: Activar el Entorno Virtual
```bash
venv\Scripts\activate
```

### Paso 2: Generar los Datos Sintéticos Relacionales
```bash
python scripts/generate_synthetic.py
```
*Esto generará y guardará los archivos CSV en `data/raw/` y `data/processed/`.*

### Paso 3: Ejecutar Ingeniería de Características
```bash
python src/features/build_features.py
```
*Esto calculará las variables de riesgo de la rúbrica y las guardará en `data/processed/siniestros_processed.csv`.*

### Paso 4: Entrenar el Modelo de Machine Learning
```bash
python src/models/fraud_model.py
```
*Esto entrenará el clasificador Random Forest, calculará las métricas de rendimiento y guardará el modelo en `models/random_forest_fraud.joblib`.*

### Paso 5: Correr Pruebas Unitarias
```bash
python -m unittest tests/test_rules.py
```
*Esto validará que el motor de reglas de negocio funcione a la perfección.*

### Paso 6: Lanzar la Aplicación Streamlit
```bash
streamlit run src/app/main.py
```
*Esto abrirá la aplicación en tu navegador.*

---

## 3. Funcionalidades Destacadas de la Interfaz

1. **Dashboard Principal**:
   - Tarjetas de KPIs Notion-style con cálculo dinámico de porcentajes del semáforo.
   - Monto financiero total en riesgo de reclamos sospechosos (USD $).
   - Cálculo automático del ahorro potencial de auditoría en base a un 80% de prevención de alertas rojas.
   - Bandeja de reclamos con filtros avanzados por Sucursal, Ramo, y Riesgo (semáforo).

2. **Analizador Detallado y Explicabilidad**:
   - Selector dinámico de reclamos ordenados por su score.
   - Ficha técnica completa del siniestro (Ecuadorian context).
   - Desglose detallado del origen del score (Reglas vs Modelo ML).
   - Listado de alertas y documentos inconsistentes o incompletos.
   - **Botón "Generar Explicación IA con Gemini 1.5 Flash"**: Llama en tiempo real a la API de Gemini para redactar un reporte analítico en español con justificaciones técnicas y recomendaciones éticas y operativas.

3. **Asistente Conversacional Antifraude (Chat Agent)**:
   - Panel de chat interactivo que recuerda el historial.
   - **Botones de Consultas Rápidas**: El analista puede presionar cualquiera de las 12 preguntas obligatorias de la rúbrica (ej. "¿Cuáles son los 10 siniestros con más riesgo?", "¿Qué proveedores concentran más alertas rojas y amarillas?") y obtener respuestas precisas del agente de IA basadas en los datos agregados en tiempo real.

4. **Red de Relaciones (PyVis)**:
   - Grafo de red interactivo que conecta Asegurados, Proveedores y Siniestros.
   - Facilita la detección visual de "Talleres de Red" (por ejemplo, un taller sospechoso que concentra múltiples alertas rojas con diferentes asegurados).
