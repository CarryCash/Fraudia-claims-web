# Fraudia Claims – Sistema de Triaje y Detección de Fraudes con IA Avanzada

Este repositorio contiene el prototipo final para el **HackIAthon 2026 – Reto Aseguradora del Sur**. 
El sistema abandona el enfoque clásico de "solo reglas" e incorpora 4 innovaciones tecnológicas avanzadas: **Modelos No Supervisados (Isolation Forest)**, **Búsqueda Semántica de Texto**, **Análisis de Grafos de Redes**, y un **Agente RAG con Text-to-SQL**.

## 🗂️ Estructura del proyecto
La aplicación está dividida en dos componentes principales: un Backend en Python (Flask) y un Frontend en React (Vite).

```text
fraudia-claims-web/
├─ README.md                 # ↗ este archivo
├─ backend/                  # API REST en Python (Flask)
│   ├─ requirements.txt      # Dependencias Python
│   ├─ app.py                # Punto de entrada del servidor Flask
│   ├─ data/                 # Base de datos SQLite y CSVs crudos
│   ├─ models/               # Modelos entrenados (.joblib)
│   └─ src/                  
│       ├─ api/              # Endpoints (claims.py, network.py, entities.py)
│       ├─ rules/            # Reglas duras y blandas tradicionales
│       ├─ ai_agent/         # Agente LLM Gemini con Text-to-SQL
│       ├─ explainability/   # Modelos Machine Learning e Isolation Forest
│       └─ storage/          # Gestor de base de datos relacional (SQLite)
├─ frontend/                 # Interfaz de Usuario en React + Vite
│   ├─ package.json          # Dependencias JS/TS
│   ├─ vite.config.ts        # Configuración de Vite y Proxy
│   └─ src/
│       ├─ components/       # Componentes visuales (Dashboard, Analizador)
│       └─ pages/            # Vistas principales
├─ .env                      # Variables de entorno (Gemini API, etc.)
└─ docs/                     # Documentación adicional
```

## 🚀 Inicio rápido (Cómo ejecutar la aplicación)

Para evaluar correctamente el prototipo, debes ejecutar **ambos servicios** (Backend y Frontend) en paralelo.

### 1. Configuración de Variables
Copia el archivo `.env.example` a `.env` en la raíz del proyecto y agrega tus claves:
```env
GEMINI_API_KEY="tu-clave-aqui"
NVIDIA_API_KEY="tu-clave-aqui"
```

### 2. Levantar el Backend (Servidor Flask)
El backend provee la API REST, la base de datos SQL y los modelos de IA.
```bash
# 1. Crear el entorno virtual e instalar dependencias
python -m venv venv
venv\Scripts\activate
pip install -r backend/requirements.txt

# 2. Levantar el servidor Flask
python backend/app.py
```
*El servidor correrá en `http://127.0.0.1:5000`.*

### 3. Levantar el Frontend (Interfaz React)
Abre **otra terminal** y ejecuta los siguientes comandos para levantar la aplicación web:
```bash
# 1. Entrar a la carpeta del frontend
cd frontend

# 2. Instalar dependencias
pnpm install

# 3. Levantar el entorno de desarrollo Vite
pnpm dev
```
*La interfaz estará disponible en `http://localhost:5173`.*

## 💡 Innovaciones Técnicas Implementadas
Este prototipo supera a un motor de reglas convencional mediante 4 pilares:
1. **Detección de Anomalías (Isolation Forest):** Un algoritmo matemático no supervisado capaz de detectar fraudes atípicos que ninguna regla humana previó, evaluando patrones dimensionales de los datos.
2. **Text-to-SQL Autónomo:** El agente Gemini puede consultar la base de datos transaccional en tiempo real para armar métricas complejas a pedido del analista.
3. **Embeddings Semánticos (Sentence Transformers):** Detección de "Narrativas Clonadas" mediante análisis vectorial de la descripción del accidente, imposibles de evadir cambiando palabras clave.
4. **Análisis de Redes de Fraude (NetworkX):** Exploración de grafos para detectar sub-redes cerradas ("Carruseles") entre asegurados, vehículos y talleres mecánicos repetitivos.

---
*Este proyecto mantiene la confidencialidad de datos al usar únicamente datasets sintéticos y ofuscados.*
