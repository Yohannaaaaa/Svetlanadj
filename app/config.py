"""Configuration centrale de SVETLANA AI DJ STUDIO.

Tout passe par des variables d'environnement (compatibles Render).
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    # Dossier de données persistant (sur Render : monter un disque sur /var/data)
    DATA_DIR = Path(os.environ.get("DATA_DIR", BASE_DIR / "data")).resolve()

    # Clé secrète Flask + chiffrement des clés API stockées via l'interface
    SECRET_KEY = os.environ.get("APP_SECRET_KEY", "")

    # Mot de passe d'accès au studio (protège vos crédits API payants)
    STUDIO_PASSWORD = os.environ.get("STUDIO_PASSWORD", "")

    # Taille maximale d'upload (WAV de 10 min ≈ 100 Mo)
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_UPLOAD_MB", "200")) * 1024 * 1024

    # Fournisseur vidéo par défaut : "demo" (gratuit, local) ou "fal"
    DEFAULT_PROVIDER = os.environ.get("DEFAULT_PROVIDER", "demo")

    # Délai max d'attente d'une génération distante (secondes)
    GENERATION_TIMEOUT = int(os.environ.get("GENERATION_TIMEOUT", "1200"))

    FFMPEG = os.environ.get("FFMPEG_BIN", "ffmpeg")
    FFPROBE = os.environ.get("FFPROBE_BIN", "ffprobe")

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "0") == "1"


ALLOWED_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_AUDIO_EXT = {".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg"}
