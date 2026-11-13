"""Fournisseur fal.ai : une seule clé API donne accès à Kling, Veo, Seedance,
Nano Banana, FLUX Kontext, etc. via une file d'attente (queue) REST.

API utilisée :
    POST https://queue.fal.run/<endpoint>        (Authorization: Key <FAL_KEY>)
      -> {request_id, status_url, response_url}
    GET  status_url   -> {"status": "IN_QUEUE" | "IN_PROGRESS" | "COMPLETED"}
    GET  response_url -> résultat (ex. {"video": {"url": ...}})

Les modèles sont décrits de façon déclarative ci-dessous. Les noms d'endpoint
et les tarifs évoluent souvent : vous pouvez les corriger/compléter SANS
toucher au code en créant DATA_DIR/models.json (même structure, fusionnée).
Vérifiez toujours les tarifs sur https://fal.ai/pricing.
"""
import base64
import copy
import io
import json
import time
from pathlib import Path

import requests
from PIL import Image

QUEUE_URL = "https://queue.fal.run/"

DEFAULT_MODELS = {
    "video": {
        "kling-2.6-pro": {
            "label": "Kling 2.6 Pro – image→vidéo (recommandé : visages et mains stables)",
            "endpoint": "fal-ai/kling-video/v2.6/pro/image-to-video",
            "image_field": "image_url",
            "durations": [5, 10],
            "duration_format": "{d}",
            "negative_field": "negative_prompt",
            "params": {"generate_audio": False},
            "price_per_second": 0.07,
            "output": "video.url",
        },
        "kling-2.5-turbo-pro": {
            "label": "Kling 2.5 Turbo Pro – image→vidéo (rapide, économique)",
            "endpoint": "fal-ai/kling-video/v2.5-turbo/pro/image-to-video",
            "image_field": "image_url",
            "durations": [5, 10],
            "duration_format": "{d}",
            "negative_field": "negative_prompt",
            "params": {"cfg_scale": 0.5},
            "price_per_second": 0.07,
            "output": "video.url",
        },
        "veo-3.1-fast": {
            "label": "Google Veo 3.1 Fast – image→vidéo (cinématique, 1080p)",
            "endpoint": "fal-ai/veo3.1/fast/image-to-video",
            "image_field": "image_url",
            "durations": [4, 6, 8],
            "duration_format": "{d}s",
            "negative_field": "negative_prompt",
            "aspect_field": "aspect_ratio",
            "params": {"generate_audio": False, "resolution": "1080p"},
            "price_per_second": 0.15,
            "output": "video.url",
        },
        "veo-3.1": {
            "label": "Google Veo 3.1 – image→vidéo (qualité max, cher)",
            "endpoint": "fal-ai/veo3.1/image-to-video",
            "image_field": "image_url",
            "durations": [4, 6, 8],
            "duration_format": "{d}s",
            "negative_field": "negative_prompt",
            "aspect_field": "aspect_ratio",
            "params": {"generate_audio": False, "resolution": "1080p"},
            "price_per_second": 0.40,
            "output": "video.url",
        },
        "seedance-1-pro": {
            "label": "ByteDance Seedance 1.0 Pro – image→vidéo (mouvements dynamiques)",
            "endpoint": "fal-ai/bytedance/seedance/v1/pro/image-to-video",
            "image_field": "image_url",
            "durations": [5, 10],
            "duration_format": "{d}",
            "params": {"resolution": "1080p"},
            "price_per_second": 0.12,
            "output": "video.url",
        },
    },
    "image": {
        "nano-banana-edit": {
            "label": "Google Nano Banana (Gemini Image) – édition fidèle au visage",
            "endpoint": "fal-ai/nano-banana/edit",
            "image_field": "image_urls",
            "multi_image": True,
            "aspect_field": "aspect_ratio",
            "params": {"num_images": 1, "output_format": "png"},
            "price_per_image": 0.04,
            "output": "images.0.url",
        },
        "seedream-4-edit": {
            "label": "ByteDance Seedream 4 Edit – multi-références",
            "endpoint": "fal-ai/bytedance/seedream/v4/edit",
            "image_field": "image_urls",
            "multi_image": True,
            "params": {"num_images": 1},
            "price_per_image": 0.03,
            "output": "images.0.url",
        },
        "flux-kontext-pro": {
            "label": "FLUX.1 Kontext Pro – édition contextuelle",
            "endpoint": "fal-ai/flux-pro/kontext",
            "image_field": "image_url",
            "aspect_field": "aspect_ratio",
            "params": {"output_format": "png"},
            "price_per_image": 0.04,
            "output": "images.0.url",
        },
    },
}


def load_models(data_dir) -> dict:
    models = copy.deepcopy(DEFAULT_MODELS)
    path = Path(data_dir) / "models.json"
    if path.exists():
        try:
            override = json.loads(path.read_text(encoding="utf-8"))
            for kind in ("video", "image"):
                for key, spec in (override.get(kind) or {}).items():
                    models[kind].setdefault(key, {}).update(spec)
        except (ValueError, OSError):
            pass
    return models


def image_to_data_uri(path: Path, max_side: int = 1536) -> str:
    img = Image.open(path)
    img = img.convert("RGB")
    img.thumbnail((max_side, max_side))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=92)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def _dig(obj, dotted: str):
    for part in dotted.split("."):
        obj = obj[int(part)] if isinstance(obj, list) else obj[part]
    return obj


class FalError(RuntimeError):
    pass


class FalProvider:
    name = "fal"

    def __init__(self, api_key: str | None, models: dict, config):
        self.key = api_key
        self.models = models
        self.timeout = config["GENERATION_TIMEOUT"]

    # ---------------------------------------------------------------- utils
    def _headers(self):
        if not self.key:
            raise FalError("Clé API fal.ai manquante : ajoutez-la dans Réglages → Clés API.")
        return {"Authorization": f"Key {self.key}", "Content-Type": "application/json"}

    def estimate(self, model: str, seconds: float) -> float:
        spec = self.models["video"].get(model) or {}
        return round(spec.get("price_per_second", 0) * seconds, 3)

    def submit(self, endpoint: str, payload: dict) -> dict:
        r = requests.post(QUEUE_URL + endpoint, headers=self._headers(), json=payload, timeout=60)
        if r.status_code >= 400:
            raise FalError(f"fal.ai a refusé la requête ({r.status_code}) : {r.text[:500]}")
        return r.json()

    def wait(self, job: dict, on_progress=None) -> dict:
        """Attend la fin d'un job (job = réponse de submit, ou {status_url, response_url})."""
        start = time.time()
        delay = 3
        while True:
            r = requests.get(job["status_url"], headers=self._headers(), timeout=30)
            if r.status_code >= 400:
                raise FalError(f"Statut fal.ai illisible ({r.status_code}) : {r.text[:300]}")
            st = r.json()
            status = st.get("status")
            if on_progress:
                on_progress(status, st.get("queue_position"))
            if status == "COMPLETED":
                break
            if status not in ("IN_QUEUE", "IN_PROGRESS"):
                raise FalError(f"Échec de génération : {json.dumps(st)[:400]}")
            if time.time() - start > self.timeout:
                raise FalError("Délai dépassé en attendant fal.ai (le job continue peut-être côté fal).")
            time.sleep(delay)
            delay = min(10, delay + 1)
        r = requests.get(job["response_url"], headers=self._headers(), timeout=60)
        if r.status_code >= 400:
            raise FalError(f"Erreur de génération ({r.status_code}) : {r.text[:500]}")
        return r.json()

    @staticmethod
    def download(url: str, out_path: Path) -> Path:
        with requests.get(url, stream=True, timeout=300) as r:
            r.raise_for_status()
            with open(out_path, "wb") as f:
                for chunk in r.iter_content(1 << 16):
                    f.write(chunk)
        return out_path

    # ------------------------------------------------------------ keyframes
    def generate_keyframe(self, prompt: str, reference_paths, out_path: Path, aspect: str,
                          model: str | None = None, on_job=None, on_progress=None):
        model = model or "nano-banana-edit"
        spec = self.models["image"].get(model)
        if not spec:
            raise FalError(f"Modèle d'image inconnu : {model}")
        uris = [image_to_data_uri(Path(p)) for p in reference_paths[:4]]
        payload = {"prompt": prompt, **spec.get("params", {})}
        payload[spec["image_field"]] = uris if spec.get("multi_image") else uris[0]
        if spec.get("aspect_field"):
            payload[spec["aspect_field"]] = aspect
        job = self.submit(spec["endpoint"], payload)
        if on_job:
            on_job(job)
        result = self.wait(job, on_progress)
        url = _dig(result, spec["output"])
        out_path = out_path.with_suffix(".png" if ".png" in url.split("?")[0] else ".jpg")
        return self.download(url, out_path)

    # ---------------------------------------------------------------- clips
    def build_clip_payload(self, shot: dict, image_path: Path, aspect: str, duration: int, model: str):
        spec = self.models["video"].get(model)
        if not spec:
            raise FalError(f"Modèle vidéo inconnu : {model}")
        allowed = spec.get("durations") or [duration]
        d = min(allowed, key=lambda a: (a < duration, abs(a - duration)))
        payload = {"prompt": shot["prompt"], **spec.get("params", {})}
        payload[spec["image_field"]] = image_to_data_uri(image_path)
        payload["duration"] = spec.get("duration_format", "{d}").format(d=d)
        if spec.get("negative_field") and shot.get("negative_prompt"):
            payload[spec["negative_field"]] = shot["negative_prompt"]
        if spec.get("aspect_field"):
            payload[spec["aspect_field"]] = aspect
        return spec, payload, d

    def generate_clip(self, shot: dict, image_path: Path, out_path: Path, aspect: str,
                      duration: int = 5, model: str | None = None, on_job=None, on_progress=None, **_):
        model = model or "kling-2.6-pro"
        spec, payload, d = self.build_clip_payload(shot, image_path, aspect, duration, model)
        job = self.submit(spec["endpoint"], payload)
        if on_job:
            on_job({**job, "model": model, "seconds": d})
        return self.finish_clip(job, model, out_path, on_progress)

    def finish_clip(self, job: dict, model: str, out_path: Path, on_progress=None):
        spec = self.models["video"][model]
        result = self.wait(job, on_progress)
        url = _dig(result, spec["output"])
        self.download(url, out_path)
        seconds = job.get("seconds") or 5
        return {"path": out_path, "cost": self.estimate(model, seconds)}
