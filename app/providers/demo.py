"""Fournisseur DÉMO : anime la photo (keyframe ou référence) avec FFmpeg.

Ce n'est PAS de la génération IA : c'est un « animatic » gratuit qui permet de
tester tout le pipeline (synchronisation, montage, logo, exports) avant de
dépenser des crédits sur Kling / Veo.
"""
import shutil
from pathlib import Path

from ..assembly import RenderError, run

FPS = 30

# Expressions zoompan par mouvement caméra (on = numéro de frame, d = total)
MOTIONS = {
    "static": ("1.05", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),
    "push_in": ("1+0.35*on/{d}", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),
    "pull_out": ("1.45-0.4*on/{d}", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),
    "orbit": ("1.2", "(iw-iw/zoom)*on/{d}", "ih/2-(ih/zoom/2)"),
    "crane_up": ("1.25-0.1*on/{d}", "iw/2-(iw/zoom/2)", "(ih-ih/zoom)*(1-on/{d})"),
    "handheld": ("1.15", "iw/2-(iw/zoom/2)+iw*0.012*sin(on*0.9)", "ih/2-(ih/zoom/2)+ih*0.01*cos(on*1.3)"),
    "low_angle": ("1.1+0.15*on/{d}", "iw/2-(iw/zoom/2)", "(ih-ih/zoom)"),
    "drone": ("1.4-0.35*on/{d}", "(iw-iw/zoom)*(1-on/{d})", "ih/2-(ih/zoom/2)"),
}

# Point de visée vertical selon le geste (le visage est généralement dans le tiers supérieur)
FOCUS_Y = {"closeup_face": 0.24, "look_camera": 0.30, "headphones": 0.30, "riser": 0.38}

ENV_TINT = {
    "festival": "colorbalance=rs=0.08:bs=-0.03",
    "club": "colorbalance=rs=0.12:gs=-0.04:bs=-0.04",
    "rooftop": "colorbalance=bs=0.08:rm=0.03",
    "studio": "colorbalance=rs=0.05",
    "futuristic": "colorbalance=bs=0.1:rs=0.05",
    "warehouse": "colorbalance=rs=0.1:gs=-0.05",
}


class DemoProvider:
    name = "demo"

    def __init__(self, config):
        self.ffmpeg = config["FFMPEG"]

    def estimate(self, model: str, seconds: float) -> float:
        return 0.0

    def generate_keyframe(self, prompt, reference_paths, out_path: Path, aspect: str, model: str | None = None, **_):
        src = Path(reference_paths[0])
        out_path = out_path.with_suffix(src.suffix.lower())
        shutil.copyfile(src, out_path)
        return out_path

    def generate_clip(self, shot: dict, image_path: Path, out_path: Path, aspect: str,
                      duration: int = 5, model: str | None = None, environment: str = "festival", **_):
        w, h = (1280, 720) if aspect == "16:9" else (720, 1280)
        frames = int(duration * FPS)
        z, x, y = MOTIONS.get(shot.get("camera"), MOTIONS["static"])
        z, x, y = (e.format(d=frames) for e in (z, x, y))
        fy = FOCUS_Y.get(shot.get("action"))
        if fy is not None and y == "ih/2-(ih/zoom/2)":
            y = f"max(0,min(ih-ih/zoom,ih*{fy}-ih/zoom/2))"
        tint = ENV_TINT.get(shot.get("environment") or environment, "null")
        # Image agrandie (cover) puis zoompan. Une seule image en entrée (pas de
        # -loop) : zoompan produit toutes les frames à partir d'elle, ce qui évite
        # d'accumuler des images en mémoire.
        sw, sh = int(w * 1.6) // 2 * 2, int(h * 1.6) // 2 * 2
        vf = (
            f"scale={sw}:{sh}:force_original_aspect_ratio=increase,"
            f"crop={sw}:{sh},setsar=1,"
            f"zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={w}x{h}:fps={FPS},"
            f"{tint},vignette=PI/5,"
            # légère pulsation de lumière pour simuler l'ambiance club
            f"eq=brightness='0.04*sin(2*PI*t*2.5)':eval=frame,format=yuv420p"
        )
        cmd = [self.ffmpeg, "-y", "-v", "error", "-i", str(image_path),
               "-vf", vf, "-frames:v", str(frames), "-c:v", "libx264", "-preset", "veryfast",
               "-crf", "20", "-pix_fmt", "yuv420p", str(out_path)]
        try:
            run(cmd)
        except RenderError as e:
            raise RuntimeError("FFmpeg (démo) : " + str(e)[-500:]) from None
        return {"path": out_path, "cost": 0.0}
