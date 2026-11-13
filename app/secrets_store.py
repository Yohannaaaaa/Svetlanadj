"""Stockage sécurisé des clés API.

Ordre de priorité :
  1. Variables d'environnement (recommandé sur Render : FAL_KEY, ...)
  2. Fichier chiffré DATA_DIR/secrets.enc (saisie depuis l'interface)

Le fichier est chiffré (Fernet / AES-128-CBC + HMAC-SHA256) avec une clé
dérivée de APP_SECRET_KEY. Les clés ne sont JAMAIS renvoyées au navigateur :
seule une version masquée (ex. "fa…9c3d") est affichée.
"""
import base64
import hashlib
import json
import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

# Clés gérées par l'application : nom -> variable d'environnement
KNOWN_KEYS = {
    "fal": "FAL_KEY",
}


class SecretStore:
    def __init__(self, data_dir: Path, app_secret: str):
        self.path = Path(data_dir) / "secrets.enc"
        self._fernet = None
        if app_secret:
            digest = hashlib.sha256(("svetlana-secrets:" + app_secret).encode()).digest()
            self._fernet = Fernet(base64.urlsafe_b64encode(digest))

    @property
    def can_store(self) -> bool:
        return self._fernet is not None

    def _load(self) -> dict:
        if not self._fernet or not self.path.exists():
            return {}
        try:
            return json.loads(self._fernet.decrypt(self.path.read_bytes()))
        except (InvalidToken, ValueError):
            # APP_SECRET_KEY a changé : les anciennes clés sont illisibles
            return {}

    def _save(self, data: dict):
        if not self._fernet:
            raise RuntimeError(
                "APP_SECRET_KEY n'est pas défini : impossible de chiffrer les clés. "
                "Définissez-le ou utilisez les variables d'environnement."
            )
        tmp = self.path.with_suffix(".tmp")
        tmp.write_bytes(self._fernet.encrypt(json.dumps(data).encode()))
        os.chmod(tmp, 0o600)
        os.replace(tmp, self.path)

    def get(self, name: str) -> str | None:
        env_name = KNOWN_KEYS.get(name)
        if env_name and os.environ.get(env_name):
            return os.environ[env_name]
        return self._load().get(name) or None

    def set(self, name: str, value: str):
        if name not in KNOWN_KEYS:
            raise ValueError("Clé inconnue")
        data = self._load()
        value = (value or "").strip()
        if value:
            data[name] = value
        else:
            data.pop(name, None)
        self._save(data)

    def status(self) -> dict:
        out = {}
        stored = self._load()
        for name, env_name in KNOWN_KEYS.items():
            value = os.environ.get(env_name) or stored.get(name)
            out[name] = {
                "configured": bool(value),
                "source": "env" if os.environ.get(env_name) else ("chiffré" if name in stored else None),
                "masked": mask(value) if value else None,
                "env_var": env_name,
            }
        return out


def mask(value: str) -> str:
    if len(value) <= 8:
        return "••••"
    return f"{value[:3]}…{value[-4:]}"
