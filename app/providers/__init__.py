"""Fournisseurs de génération d'images et de vidéos."""
from .demo import DemoProvider
from .fal import FalProvider, load_models


def get_provider(name: str, app_config, secrets, data_dir):
    if name == "fal":
        return FalProvider(secrets.get("fal"), load_models(data_dir), app_config)
    return DemoProvider(app_config)


def provider_catalog(data_dir) -> dict:
    models = load_models(data_dir)
    return {
        "demo": {
            "label": "Démo locale (gratuit, aperçu animé – pas d'IA)",
            "video_models": {"demo": {"label": "Animation de l'image (FFmpeg)", "price_per_second": 0, "durations": [5]}},
            "image_models": {"demo": {"label": "Copie de la photo de référence", "price_per_image": 0}},
        },
        "fal": {
            "label": "fal.ai (Kling, Veo, Seedance, Nano Banana…) – payant",
            "video_models": models["video"],
            "image_models": models["image"],
        },
    }
