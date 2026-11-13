FROM python:3.12-slim

# FFmpeg (montage, analyse audio) + polices pour le logo par défaut
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

ENV DATA_DIR=/var/data \
    PYTHONUNBUFFERED=1 \
    COOKIE_SECURE=1
RUN mkdir -p /var/data

# 1 seul worker : les tâches de génération tournent dans ce processus.
# Plusieurs threads pour garder l'interface réactive pendant les rendus.
CMD gunicorn wsgi:app --workers 1 --threads 8 --timeout 300 --bind 0.0.0.0:${PORT:-10000}
