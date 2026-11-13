"""Orchestration des tâches longues (keyframes, clips IA, rendu) en arrière-plan.

Les états sont écrits dans project.json, ce qui permet à l'interface de suivre
la progression et de reprendre les jobs fal.ai après un redémarrage.
"""
import math
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import assembly, branding
from .providers import get_provider
from .providers.fal import FalProvider

HASHTAGS = {
    "tiktok": "#hardtechno #hardstyle #rawstyle #techno #dj #virtualdj #aiartist #rave #svetlana",
    "instagram": "#hardtechno #hardstyle #rawstyle #industrialtechno #reversebass #djlife #virtualartist #festival #svetlana",
    "youtube": "#hardtechno #hardstyle #shorts #svetlana",
}


class Pipeline:
    def __init__(self, app_config, storage, secrets, workers: int = 3):
        self.config = app_config
        self.storage = storage
        self.secrets = secrets
        self.pool = ThreadPoolExecutor(max_workers=workers)
        self.render_pool = ThreadPoolExecutor(max_workers=1)  # FFmpeg est gourmand

    # --------------------------------------------------------------- helpers
    def provider(self, project):
        return get_provider(project.get("provider", "demo"), self.config, self.secrets, self.config["DATA_DIR"])

    def _shot_update(self, pid, sid, **fields):
        def mut(p):
            for s in p["shots"]:
                if s["id"] == sid:
                    s.update(fields)
        return self.storage.update_project(pid, mut)

    def _shot(self, project, sid):
        for s in project["shots"]:
            if s["id"] == sid:
                return s
        raise KeyError(sid)

    def references(self):
        ident = self.storage.get_identity()
        refs = [self.storage.identity_file(ident.get("reference_image"))]
        refs += [self.storage.identity_file(n) for n in ident.get("extra_references", [])]
        refs = [r for r in refs if r]
        if not refs:
            raise RuntimeError("Importez d'abord la photo officielle de SVETLANA (onglet Identité).")
        return refs

    def logo_path(self) -> Path:
        ident = self.storage.get_identity()
        p = self.storage.identity_file(ident.get("logo"))
        if p:
            return p
        default = self.storage.identity_dir / "logo_default.png"
        if not default.exists():
            branding.make_default_logo(default)
        return default

    @staticmethod
    def requested_duration(shot) -> int:
        need = float(shot["end"]) - float(shot["start"]) + 0.5
        return max(4, math.ceil(need))

    # ------------------------------------------------------------- keyframe
    def start_keyframe(self, pid, sid):
        self._shot_update(pid, sid, status="keyframe_running", error=None, progress="En file d'attente")
        self.pool.submit(self._run_keyframe, pid, sid)

    def _run_keyframe(self, pid, sid):
        try:
            project = self.storage.get_project(pid)
            shot = self._shot(project, sid)
            prov = self.provider(project)
            out = self.storage.project_dir(pid) / "keyframes" / f"{sid}_{int(time.time())}.png"
            path = prov.generate_keyframe(
                shot["keyframe_prompt"], self.references(), out, project.get("aspect", "9:16"),
                model=project.get("image_model"),
                on_progress=lambda st, q: self._shot_update(pid, sid, progress=f"{st} {'#' + str(q) if q else ''}"),
            )
            cost = 0.0
            if isinstance(prov, FalProvider):
                cost = prov.models["image"].get(project.get("image_model") or "nano-banana-edit", {}).get("price_per_image", 0)
            self._add_cost(pid, cost)

            def mut(p):
                s = self._shot(p, sid)
                s["keyframe"] = Path(path).name
                s.setdefault("keyframe_takes", []).append(Path(path).name)
                s["status"] = "keyframe_ready"
                s["progress"] = None
            self.storage.update_project(pid, mut)
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            self._shot_update(pid, sid, status="error", error=str(e), progress=None)

    # ----------------------------------------------------------------- clip
    def start_clip(self, pid, sid):
        self._shot_update(pid, sid, status="generating", error=None, progress="En file d'attente")
        self.pool.submit(self._run_clip, pid, sid)

    def _source_image(self, pid, shot) -> Path:
        pdir = self.storage.project_dir(pid)
        if shot.get("use_keyframe", True) and shot.get("keyframe"):
            p = pdir / "keyframes" / shot["keyframe"]
            if p.exists():
                return p
        return self.references()[0]

    def _run_clip(self, pid, sid):
        try:
            project = self.storage.get_project(pid)
            shot = self._shot(project, sid)
            prov = self.provider(project)
            image = self._source_image(pid, shot)
            out = self.storage.project_dir(pid) / "clips" / f"{sid}_{int(time.time())}.mp4"
            result = prov.generate_clip(
                shot, image, out, project.get("aspect", "9:16"),
                duration=self.requested_duration(shot),
                model=project.get("video_model"),
                environment=project.get("environment"),
                on_job=lambda job: self._shot_update(pid, sid, job={
                    "status_url": job.get("status_url"), "response_url": job.get("response_url"),
                    "model": job.get("model"), "seconds": job.get("seconds"), "out": out.name}),
                on_progress=lambda st, q: self._shot_update(pid, sid, progress=f"{st} {'#' + str(q) if q else ''}"),
            )
            self._clip_done(pid, sid, out, result.get("cost", 0))
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            self._shot_update(pid, sid, status="error", error=str(e), progress=None)

    def _clip_done(self, pid, sid, out: Path, cost: float):
        self._add_cost(pid, cost)

        def mut(p):
            s = self._shot(p, sid)
            s["clip"] = out.name
            s.setdefault("takes", []).append(out.name)
            s["status"] = "ready"
            s["progress"] = None
            s["job"] = None
        self.storage.update_project(pid, mut)

    def _add_cost(self, pid, cost):
        if cost:
            self.storage.update_project(pid, lambda p: p.update(spent=round(p.get("spent", 0) + cost, 3)))

    def resume_pending(self):
        """Au démarrage : reprend l'attente des jobs fal.ai interrompus."""
        for project in self.storage.list_projects():
            for s in project.get("shots", []):
                if s.get("status") not in ("generating", "keyframe_running", "rendering"):
                    continue
                job = s.get("job") or {}
                if s["status"] == "generating" and job.get("response_url") and project.get("provider") == "fal":
                    self.pool.submit(self._resume_clip, project["id"], s["id"], job)
                else:
                    self._shot_update(project["id"], s["id"], status="error", progress=None,
                                      error="Interrompu par un redémarrage du serveur – relancez.")
            r = project.get("render") or {}
            if r.get("status") == "running":
                self.storage.update_project(project["id"], {"render": {**r, "status": "error",
                                                                       "message": "Interrompu – relancez le rendu."}})

    def _resume_clip(self, pid, sid, job):
        try:
            project = self.storage.get_project(pid)
            prov = self.provider(project)
            out = self.storage.project_dir(pid) / "clips" / (job.get("out") or f"{sid}_{int(time.time())}.mp4")
            result = prov.finish_clip(job, job.get("model") or project.get("video_model") or "kling-2.6-pro", out)
            self._clip_done(pid, sid, out, result.get("cost", 0))
        except Exception as e:  # noqa: BLE001
            self._shot_update(pid, sid, status="error", error=str(e), progress=None)

    # --------------------------------------------------------------- render
    def start_render(self, pid, formats):
        formats = [f for f in formats if f in assembly.FORMATS] or ["vertical"]
        self.storage.update_project(pid, {"render": {"status": "running", "progress": 0,
                                                     "message": "En file d'attente", "formats": formats}})
        self.render_pool.submit(self._run_render, pid, formats)

    def _run_render(self, pid, formats):
        try:
            project = self.storage.get_project(pid)
            pdir = self.storage.project_dir(pid)
            outputs = []
            try:
                fallback = self.references()[0]
            except RuntimeError:
                fallback = None
            for k, fmt in enumerate(formats):
                def prog(frac, msg, k=k, fmt=fmt):
                    total = (k + frac) / len(formats)
                    self.storage.update_project(pid, lambda p: p["render"].update(
                        progress=round(total, 3), message=f"{assembly.FORMATS[fmt]['label']} – {msg}"))
                out = assembly.render_project(
                    project, pdir, fmt, self.logo_path(), fallback,
                    ffmpeg=self.config["FFMPEG"], ffprobe=self.config["FFPROBE"],
                    fit=project.get("fit", "cover"), progress=prog)
                outputs.append({"format": fmt, "video": out.name, "thumbnail": out.with_suffix(".jpg").name,
                                "label": assembly.FORMATS[fmt]["label"]})
            captions = self._write_captions(project, pdir)
            self.storage.update_project(pid, {"render": {
                "status": "done", "progress": 1, "message": "Vidéos prêtes",
                "outputs": outputs, "captions": captions, "finished_at": time.time()}})
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            self.storage.update_project(pid, {"render": {"status": "error", "progress": 0, "message": str(e)}})

    def _write_captions(self, project, pdir: Path) -> str:
        title = project.get("title", "SVETLANA")
        bpm = (project.get("analysis") or {}).get("bpm")
        bpm_txt = f" • {round(bpm)} BPM" if bpm else ""
        track = project.get("track_title") or ""
        lines = [
            f"=== TikTok ===\n{title}{bpm_txt} ⚡ {track}\n{HASHTAGS['tiktok']}\n",
            f"=== Instagram Reels ===\n{title}\n🎧 {track}{bpm_txt}\nVirtual AI DJ • Hard Techno / Hardstyle\n{HASHTAGS['instagram']}\n",
            f"=== YouTube (Shorts : fichier vertical / vidéo : horizontal) ===\nTitre : {title}{bpm_txt}\n"
            f"Description : SVETLANA – virtual AI DJ. {track}\n{HASHTAGS['youtube']}\n",
            "=== Transparence ===\nPensez à activer la mention « contenu généré par IA » "
            "(TikTok : 'AI-generated content', Instagram : 'Étiquette IA', YouTube : 'Contenu modifié ou synthétique').\n",
        ]
        name = "captions.txt"
        (pdir / "exports" / name).write_text("\n".join(lines), encoding="utf-8")
        return name
