# Limitaciones, Ética y Prácticas Éticas – Fraudia Claims

Este documento describe las limitaciones del prototipo **Fraudia Claims**, las consideraciones sobre sesgos y falsos positivos, y las pautas éticas para su uso en **Aseguradora del Sur**.

---

## 1. Principio Clave del Sistema

> [!IMPORTANT]
> **La solución genera alertas de revisión, NO acusaciones automáticas de fraude.**
> 
> El propósito de Fraudia Claims es actuar como un copiloto inteligente de soporte para el analista humano, optimizando los tiempos de análisis y detectando patrones ocultos. En ningún escenario el sistema tomará decisiones automáticas de rechazo de pago, terminación de pólizas o imputaciones legales. Toda alerta crítica requiere la confirmación, investigación y firma de un analista especializado.

---

## 2. Limitaciones del Prototipo

### 2.1. Calidad y Origen de los Datos
- **Datos Sintéticos**: Para proteger el secreto comercial y la confidencialidad de la aseguradora, el prototipo ha sido entrenado y evaluado utilizando un dataset 100% sintético (aumentado desde una muestra de Kaggle). El modelo predictivo de ML debe ser re-entrenado con datos reales e históricos de la aseguradora antes de ser puesto en producción.
- **Sesgo de Representatividad**: Si los siniestros históricos reales contienen sesgos (por ejemplo, mayor propensión a revisar reclamos en ciertas zonas o de ciertos ramos), el modelo de Machine Learning podría replicar o amplificar estos sesgos.

### 2.2. Dependencias Técnicas y Operativas
- **Dependencia de la API de Gemini**: La justificación en lenguaje natural y el agente de consultas conversacional dependen del acceso a internet y de la disponibilidad de la API de Gemini. Si la API no está disponible, el sistema tiene una rutina de escape (fallback) que muestra la explicación básica basada en el motor de reglas determinista.
- **NLP Local Simplificado**: La similitud textual (para la regla de narrativas clonadas RF07) se calcula mediante matrices TF-IDF debido al rendimiento local y para evitar la descarga de dependencias pesadas de PyTorch (que dificultarían la ejecución en entornos limitados). Aunque es sumamente rápido, podría no detectar similitudes semánticas si se usan sinónimos muy distintos.

---

## 3. Manejo de Falsos Positivos

Las alertas en nivel **Amarillo** o **Rojo** no implican necesariamente un intento fraudulento. Existen situaciones normales que pueden activar alertas:
- **Vigencia Cercana (RF05)**: Un cliente que contrata un seguro legítimamente y sufre un accidente real 6 horas después debido a mala suerte.
- **Demora en Reporte (RF06)**: Un asegurado legítimo que sufre un robo de vehículo en una zona remota sin señal telefónica y tarda 5 días en viajar a una sucursal para asentar el siniestro.
- **Lista Restrictiva (RF03)**: Un taller legítimo con un nombre similar al de un proveedor observado.

Por lo tanto, la recomendación de auditoría es **iniciar siempre una revisión respetuosa y recopilar más evidencias antes de tomar medidas administrativas**.

---

## 4. Estándares Éticos y de Privacidad
- **Anonimización**: Todos los nombres de asegurados y cédulas de identidad generados en el dataset son 100% ficticios. En producción, la información de identificación personal (PII) debe encriptarse y los accesos a la base histórica deben regirse bajo estrictas políticas de control de acceso.
- **Explicabilidad Obligatoria**: No se permite el uso de algoritmos de "caja negra" sin explicabilidad. La combinación con el motor de reglas determinista asegura que el analista siempre pueda saber qué criterios exactos de negocio y qué variables influyeron en el cálculo de la alerta.
