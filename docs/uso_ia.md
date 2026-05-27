# Uso de Inteligencia Artificial – Fraudia Claims

Este documento detalla el rol, diseño e integración de los componentes de **Inteligencia Artificial** en **Fraudia Claims** (Reto Aseguradora del Sur).

---

## 1. Enfoque Híbrido de Inteligencia Artificial

Fraudia Claims utiliza un sistema híbrido que complementa la rigidez del análisis basado en reglas con el poder adaptativo del aprendizaje automático y los modelos de lenguaje a gran escala (LLM).

```
   ┌─────────────────────────────────────────────────────────────┐
   │                     DATOS DE SINIESTROS                     │
   └──────────────────────────────┬──────────────────────────────┘
                                  ▼
                ┌─────────────────┴─────────────────┐
                ▼                                   ▼
      ┌──────────────────┐                ┌──────────────────┐
      │   Reglas Duras   │                │  Características │
      │   y Blandas      │                │   Estructuradas  │
      └─────────┬────────┘                └─────────┬────────┘
                │ (40% Peso)                        │
                ▼                                   ▼
      ┌──────────────────┐                ┌──────────────────┐
      │  Puntos Reglas   │                │   Random Forest  │
      │     (0-100)      │                │   Probabilidad   │
      └─────────┬────────┘                └─────────┬────────┘
                │                                   │ (60% Peso)
                └─────────────────┬─────────────────┘
                                  ▼
                        ┌──────────────────┐
                        │  Score de Riesgo │ (0-100)
                        │    y Semáforo    │
                        └─────────┬────────┘
                                  ▼
                        ┌──────────────────┐
                        │   Gemini 1.5     │
                        │ Explica & Chatea │
                        └──────────────────┘
```

---

## 2. Componentes de IA Implementados

### 2.1. Procesamiento de Lenguaje Natural (NLP) - Detección de Narrativas Clonadas
- **Objetivo**: Detectar si la descripción de un reclamo ha sido copiada o "clonada" de otro reclamo preexistente (bandera crítica de fraude organizado o colisiones falsificadas).
- **Tecnología**: Vectorización mediante **TF-IDF (Term Frequency-Inverse Document Frequency)** y cálculo de la matriz de **similitud de coseno** global.
- **Funcionamiento**: En la etapa de ingeniería de características, cada narrativa se compara con el resto de la base histórica. Si se supera el 85% de similitud, se activa la regla **RF07** (Amarillo) y se agregan **8 puntos** en las reglas blandas. Si está entre 70% y 84%, se agregan **4 puntos**.

### 2.2. Machine Learning - Clasificador de Riesgo Supervisado
- **Objetivo**: Detectar patrones sutiles, dependencias cruzadas de variables y anomalías que escapan a las reglas lógicas tradicionales.
- **Tecnología**: `RandomForestClassifier` de Scikit-Learn.
- **Lógica**: Se entrena sobre las variables estructuradas e indicadores procesados de siniestros, pólizas, asegurados y proveedores. Su salida es una probabilidad matemática continua entre `0.0` y `1.0` de que el caso represente una anomalía o fraude.
- **Salida**: Representa el 60% del peso en la fusión del score final de riesgo de Fraudia Claims.

### 2.3. Explicabilidad Generativa con Gemini 1.5 Flash
- **Objetivo**: Traducir métricas técnicas complejas y banderas de alerta a una justificación en lenguaje natural redactada para analistas humanos, mejorando la confianza y reduciendo el tiempo de revisión.
- **Lógica**: Cuando un usuario inspecciona un siniestro en el dashboard, se genera un prompt estructurado que contiene los detalles de la colisión, las reglas activadas, el score y la probabilidad de IA.
- **Generación**: Gemini redacta una explicación técnica y objetiva en español dividida en:
  1. *Resumen de Alertas*
  2. *Factores de Riesgo Clave*
  3. *Recomendaciones para el Analista Humano*

### 2.4. Agente Conversacional Antifraude (RAG Agent)
- **Objetivo**: Responder consultas libres y complejas del analista (ej. estadísticas agregadas, tendencias, búsquedas cruzadas) en lenguaje natural.
- **Lógica**: `ClaimsAgent` utiliza un enfoque de **RAG Estructurado**. Pre-calcula resúmenes ejecutivos, rankings de proveedores de riesgo, estadísticas por ramo y por ciudad.
- **Resolución**: Al recibir una pregunta:
  - Si es una pregunta general o analítica, utiliza los resúmenes tabulares pre-generados en su prompt de contexto.
  - Si pregunta por un siniestro específico, recupera la ficha completa y su estado de documentos.
  - Gemini procesa la información y responde con total precisión y contextualización local.
