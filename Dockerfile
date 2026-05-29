# Usamos la imagen ligera de Python para producción
FROM python:3.11-slim
WORKDIR /app

# Instalar dependencias del sistema esenciales para fpdf2, SQLite, etc.
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copiar los requerimientos instalándolos en la raíz del contenedor
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copiar únicamente las carpetas que necesita el backend para operar
COPY backend/ ./backend/
COPY data/ ./data/
COPY docs/ ./docs/

# Forzamos a Gunicorn a escuchar en el puerto que Render asigne dinámicamente
CMD ["gunicorn", "--bind", "0.0.0.0:10000", "backend.app:create_app()"]