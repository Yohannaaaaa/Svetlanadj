"""Stockage sur disque : identité, projets, fichiers médias.

Structure :
    DATA_DIR/
      identity/identity.json, reference.<ext>, logo.png
      projects/<id>/project.json, audio.<ext>, clips/, keyframes/, exports/
      secrets.enc
"""
import json
import os
import re
import shutil
import threading
import time
import uuid
from pathlib import Path

_lock = threading.RLock()


class Storage:
    def __init__(self, data_dir: Path):
        self.root = Path(data_dir)
        self.identity_dir = self.root / "identity"
        self.projects_dir = self.root / "projects"
        for d in (self.root, self.identity_dir, self.projects_dir):
            d.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ JSON
    @staticmethod
    def _read_json(path: Path, default):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return default

    @staticmethod
    def _write_json(path: Path, data):
        tmp = path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)

    # -------------------------------------------------------------- Identité
    def get_identity(self) -> dict:
        default = {
            "name": "SVETLANA",
            "description": (
                "SVETLANA, a glamorous mysterious female DJ, very long wavy polar "
                "white-blonde hair, platinum white eyebrows, luminous ice-blue eyes, "
                "flawless professional makeup, futuristic black and metallic silver "
                "outfit, professional DJ headphones, photorealistic"
            ),
            "reference_image": None,
            "extra_references": [],
            "logo": None,
            "updated_at": None,
        }
        data = self._read_json(self.identity_dir / "identity.json", {})
        default.update(data)
        return default

    def save_identity(self, data: dict) -> dict:
        with _lock:
            current = self.get_identity()
            current.update(data)
            current["updated_at"] = time.time()
            self._write_json(self.identity_dir / "identity.json", current)
            return current

    def identity_file(self, name: str | None) -> Path | None:
        if not name:
            return None
        p = self.identity_dir / safe_name(name)
        return p if p.exists() else None

    # --------------------------------------------------------------- Projets
    def project_dir(self, pid: str) -> Path:
        if not re.fullmatch(r"[a-f0-9]{12}", pid or ""):
            raise ValueError("Identifiant de projet invalide")
        return self.projects_dir / pid

    def list_projects(self) -> list[dict]:
        out = []
        for d in self.projects_dir.iterdir():
            if d.is_dir():
                p = self._read_json(d / "project.json", None)
                if p:
                    out.append(p)
        return sorted(out, key=lambda p: p.get("created_at", 0), reverse=True)

    def create_project(self, data: dict) -> dict:
        pid = uuid.uuid4().hex[:12]
        d = self.project_dir(pid)
        for sub in ("clips", "keyframes", "exports", "work"):
            (d / sub).mkdir(parents=True, exist_ok=True)
        project = {"id": pid, "created_at": time.time(), **data}
        self._write_json(d / "project.json", project)
        return project

    def get_project(self, pid: str) -> dict | None:
        return self._read_json(self.project_dir(pid) / "project.json", None)

    def update_project(self, pid: str, updater) -> dict:
        """updater : dict à fusionner, ou fonction(project) -> None (mutation)."""
        with _lock:
            p = self.get_project(pid)
            if p is None:
                raise KeyError(pid)
            if callable(updater):
                updater(p)
            else:
                p.update(updater)
            p["updated_at"] = time.time()
            self._write_json(self.project_dir(pid) / "project.json", p)
            return p

    def delete_project(self, pid: str):
        shutil.rmtree(self.project_dir(pid), ignore_errors=True)


def safe_name(name: str) -> str:
    """Empêche toute traversée de répertoire."""
    name = os.path.basename(name or "")
    name = re.sub(r"[^A-Za-z0-9._-]", "_", name)
    if not name or name.startswith("."):
        raise ValueError("Nom de fichier invalide")
    return name
