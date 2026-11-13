"""Routes HTTP : pages, API JSON et fichiers médias."""
import hmac
import time
from functools import wraps
from pathlib import Path

from flask import (Blueprint, abort, current_app, jsonify, redirect, render_template,
                   request, send_from_directory, session, url_for)

from . import assembly, audio_analysis, presets
from .config import ALLOWED_AUDIO_EXT, ALLOWED_IMAGE_EXT
from .providers import provider_catalog
from .storage import safe_name

bp = Blueprint("studio", __name__)


# ------------------------------------------------------------------ helpers
def storage():
    return current_app.extensions["storage"]


def pipeline():
    return current_app.extensions["pipeline"]


def secret_store():
    return current_app.extensions["secrets"]


def auth_enabled():
    return bool(current_app.config.get("STUDIO_PASSWORD"))


def login_required(view):
    @wraps(view)
    def wrapper(*a, **kw):
        if auth_enabled() and not session.get("auth"):
            if request.path.startswith("/api/") or request.path.startswith("/media/"):
                return jsonify(error="Non authentifié"), 401
            return redirect(url_for("studio.login"))
        # Protection CSRF : toute écriture API exige l'en-tête X-Studio
        # (impossible à poser depuis un site tiers sans CORS).
        if request.method not in ("GET", "HEAD") and request.path.startswith("/api/"):
            if request.headers.get("X-Studio") != "1":
                return jsonify(error="Requête refusée (CSRF)"), 403
        return view(*a, **kw)
    return wrapper


def err(msg, code=400):
    return jsonify(error=msg), code


def _ext(filename, allowed):
    ext = Path(filename or "").suffix.lower()
    if ext not in allowed:
        raise ValueError(f"Format non accepté ({ext or 'aucun'}). Formats : {', '.join(sorted(allowed))}")
    return ext


def get_project_or_404(pid):
    try:
        p = storage().get_project(pid)
    except ValueError:
        abort(404)
    if not p:
        abort(404)
    return p


# -------------------------------------------------------------------- pages
@bp.route("/login", methods=["GET", "POST"])
def login():
    if not auth_enabled():
        return redirect(url_for("studio.index"))
    error = None
    if request.method == "POST":
        pw = request.form.get("password", "")
        if hmac.compare_digest(pw.encode(), current_app.config["STUDIO_PASSWORD"].encode()):
            session.clear()
            session["auth"] = True
            session.permanent = True
            return redirect(url_for("studio.index"))
        time.sleep(1)
        error = "Mot de passe incorrect"
    return render_template("login.html", error=error)


@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("studio.login"))


@bp.route("/")
@login_required
def index():
    return render_template("index.html")


@bp.route("/healthz")
def healthz():
    return {"ok": True}


# ---------------------------------------------------------------- état global
@bp.get("/api/state")
@login_required
def api_state():
    cfg = current_app.config
    warnings = []
    if cfg.get("EPHEMERAL_SECRET"):
        warnings.append("APP_SECRET_KEY non défini : les clés API ne peuvent pas être enregistrées "
                        "depuis l'interface (utilisez la variable FAL_KEY).")
    if not auth_enabled():
        warnings.append("STUDIO_PASSWORD non défini : le studio est accessible sans mot de passe. "
                        "Définissez-le avant tout déploiement public.")
    return jsonify(
        identity=storage().get_identity(),
        catalog=presets.catalog(),
        formats={k: v["label"] for k, v in assembly.FORMATS.items()},
        providers=provider_catalog(cfg["DATA_DIR"]),
        secrets=secret_store().status(),
        can_store_secrets=secret_store().can_store,
        projects=[_summary(p) for p in storage().list_projects()],
        default_provider=cfg["DEFAULT_PROVIDER"],
        warnings=warnings,
    )


def _summary(p):
    return {"id": p["id"], "title": p.get("title"), "created_at": p.get("created_at"),
            "template": p.get("template"), "spent": p.get("spent", 0),
            "render": (p.get("render") or {}).get("status")}


# ----------------------------------------------------------------- identité
@bp.post("/api/identity")
@login_required
def api_identity():
    st = storage()
    ident = st.get_identity()
    updates = {}
    try:
        ref = request.files.get("reference")
        if ref and ref.filename:
            ext = _ext(ref.filename, ALLOWED_IMAGE_EXT)
            name = f"reference_{int(time.time())}{ext}"
            ref.save(st.identity_dir / name)
            updates["reference_image"] = name
        extras = request.files.getlist("extra")
        if extras and any(f.filename for f in extras):
            names = list(ident.get("extra_references", []))
            for i, f in enumerate(extras):
                if f.filename:
                    ext = _ext(f.filename, ALLOWED_IMAGE_EXT)
                    name = f"extra_{int(time.time())}_{i}{ext}"
                    f.save(st.identity_dir / name)
                    names.append(name)
            updates["extra_references"] = names[-6:]
        logo = request.files.get("logo")
        if logo and logo.filename:
            if Path(logo.filename).suffix.lower() != ".png":
                raise ValueError("Le logo doit être un PNG (idéalement avec transparence).")
            name = f"logo_{int(time.time())}.png"
            logo.save(st.identity_dir / name)
            updates["logo"] = name
    except ValueError as e:
        return err(str(e))
    for field in ("name", "description"):
        if field in request.form:
            updates[field] = request.form[field].strip()[:1500]
    if request.form.get("remove_extra"):
        updates["extra_references"] = [n for n in ident.get("extra_references", [])
                                       if n != request.form["remove_extra"]]
    if request.form.get("reset_logo"):
        updates["logo"] = None
    return jsonify(identity=st.save_identity(updates))


# ------------------------------------------------------------------- clés API
@bp.post("/api/secrets")
@login_required
def api_secrets():
    data = request.get_json(force=True)
    try:
        secret_store().set(data.get("name", ""), data.get("value", ""))
    except (ValueError, RuntimeError) as e:
        return err(str(e))
    return jsonify(secrets=secret_store().status())


# ------------------------------------------------------------------- projets
@bp.post("/api/projects")
@login_required
def api_create_project():
    data = request.get_json(force=True) or {}
    ident = storage().get_identity()
    base = presets.instantiate_template(data.get("template", "awakening"), ident["description"],
                                        data.get("environment"))
    if data.get("title"):
        base["title"] = data["title"][:120]
    provider = data.get("provider") or current_app.config["DEFAULT_PROVIDER"]
    base.update(
        aspect=data.get("aspect", "9:16"),
        provider=provider,
        video_model=data.get("video_model") or ("demo" if provider == "demo" else "kling-2.6-pro"),
        image_model=data.get("image_model") or ("demo" if provider == "demo" else "nano-banana-edit"),
        fit="cover", spent=0, audio=None, analysis=None, audio_start=0.0, render=None,
    )
    project = storage().create_project(base)
    return jsonify(project=project)


@bp.get("/api/projects/<pid>")
@login_required
def api_get_project(pid):
    return jsonify(project=get_project_or_404(pid))


EDITABLE = {"title", "environment", "duration", "drop_at", "audio_start", "logo", "aspect",
            "provider", "video_model", "image_model", "fit", "track_title"}
SHOT_EDITABLE = {"label", "start", "end", "action", "camera", "environment", "transition_in",
                 "effects", "prompt", "keyframe_prompt", "negative_prompt", "use_keyframe",
                 "extra", "clip", "keyframe"}


@bp.patch("/api/projects/<pid>")
@login_required
def api_update_project(pid):
    get_project_or_404(pid)
    data = request.get_json(force=True) or {}

    def mut(p):
        for k in EDITABLE & data.keys():
            p[k] = data[k]
        for k in ("duration", "drop_at", "audio_start"):
            if k in p and p[k] is not None:
                p[k] = max(0.0, float(p[k]))
        p["duration"] = min(max(p["duration"], 1.0), 180.0)
        if "shots" in data:
            existing = {s["id"]: s for s in p["shots"]}
            new_shots = []
            for i, s in enumerate(data["shots"]):
                cur = existing.get(s.get("id")) or {
                    "id": f"s{int(time.time() * 1000) % 10_000_000}{i}", "status": "draft",
                    "clip": None, "keyframe": None, "error": None, "effects": [],
                    "use_keyframe": True, "negative_prompt": presets.NEGATIVE,
                }
                for k in SHOT_EDITABLE & s.keys():
                    cur[k] = s[k]
                cur["start"] = float(cur.get("start", 0))
                cur["end"] = max(cur["start"] + 0.2, float(cur.get("end", cur["start"] + 3)))
                new_shots.append(cur)
            p["shots"] = new_shots
    return jsonify(project=storage().update_project(pid, mut))


@bp.post("/api/projects/<pid>/rebuild_prompts")
@login_required
def api_rebuild_prompts(pid):
    get_project_or_404(pid)
    desc = storage().get_identity()["description"]
    only = (request.get_json(silent=True) or {}).get("shot")

    def mut(p):
        for s in p["shots"]:
            if only and s["id"] != only:
                continue
            s["prompt"] = presets.build_video_prompt(s, p["environment"], desc)
            s["keyframe_prompt"] = presets.build_keyframe_prompt({**s, "keyframe_prompt": ""}, p["environment"], desc)
    return jsonify(project=storage().update_project(pid, mut))


@bp.delete("/api/projects/<pid>")
@login_required
def api_delete_project(pid):
    get_project_or_404(pid)
    storage().delete_project(pid)
    return jsonify(ok=True)


# ------------------------------------------------------------------ musique
@bp.post("/api/projects/<pid>/audio")
@login_required
def api_audio(pid):
    project = get_project_or_404(pid)
    f = request.files.get("audio")
    if not f or not f.filename:
        return err("Aucun fichier audio")
    try:
        ext = _ext(f.filename, ALLOWED_AUDIO_EXT)
    except ValueError as e:
        return err(str(e))
    pdir = storage().project_dir(pid)
    for old in pdir.glob("audio.*"):
        old.unlink()
    name = f"audio{ext}"
    f.save(pdir / name)
    try:
        analysis = audio_analysis.analyze(pdir / name, current_app.config["FFMPEG"])
    except RuntimeError as e:
        return err(str(e))
    start = audio_analysis.suggest_start(analysis, project["duration"], project.get("drop_at") or 0)
    title = Path(f.filename).stem[:120]
    p = storage().update_project(pid, {"audio": name, "analysis": analysis,
                                       "audio_start": start, "track_title": title})
    return jsonify(project=p)


# ----------------------------------------------------------- génération IA
@bp.post("/api/projects/<pid>/shots/<sid>/keyframe")
@login_required
def api_keyframe(pid, sid):
    get_project_or_404(pid)
    try:
        pipeline().references()
    except RuntimeError as e:
        return err(str(e))
    pipeline().start_keyframe(pid, sid)
    return jsonify(project=storage().get_project(pid))


@bp.post("/api/projects/<pid>/shots/<sid>/clip")
@login_required
def api_clip(pid, sid):
    get_project_or_404(pid)
    try:
        pipeline().references()
    except RuntimeError as e:
        return err(str(e))
    pipeline().start_clip(pid, sid)
    return jsonify(project=storage().get_project(pid))


@bp.post("/api/projects/<pid>/shots/<sid>/upload")
@login_required
def api_upload_shot_media(pid, sid):
    """Import manuel d'un clip (ex. généré sur l'app web Kling / Runway / Veo)
    ou d'une keyframe."""
    get_project_or_404(pid)
    f = request.files.get("file")
    kind = request.form.get("kind", "clip")
    if not f or not f.filename:
        return err("Aucun fichier")
    try:
        if kind == "clip":
            ext = _ext(f.filename, {".mp4", ".mov", ".webm", ".m4v"})
            folder, field, takes = "clips", "clip", "takes"
        else:
            ext = _ext(f.filename, ALLOWED_IMAGE_EXT)
            folder, field, takes = "keyframes", "keyframe", "keyframe_takes"
    except ValueError as e:
        return err(str(e))
    name = f"{sid}_upload_{int(time.time())}{ext}"
    f.save(storage().project_dir(pid) / folder / name)

    def mut(p):
        for s in p["shots"]:
            if s["id"] == sid:
                s[field] = name
                s.setdefault(takes, []).append(name)
                s["status"] = "ready" if kind == "clip" else "keyframe_ready"
                s["error"] = None
    return jsonify(project=storage().update_project(pid, mut))


@bp.post("/api/projects/<pid>/generate_all")
@login_required
def api_generate_all(pid):
    project = get_project_or_404(pid)
    data = request.get_json(silent=True) or {}
    try:
        pipeline().references()
    except RuntimeError as e:
        return err(str(e))
    what = data.get("what", "clips")
    for s in project["shots"]:
        if s.get("status") in ("generating", "keyframe_running"):
            continue
        if what == "keyframes":
            pipeline().start_keyframe(pid, s["id"])
        elif not s.get("clip") or data.get("overwrite"):
            pipeline().start_clip(pid, s["id"])
    return jsonify(project=storage().get_project(pid))


@bp.post("/api/projects/<pid>/render")
@login_required
def api_render(pid):
    project = get_project_or_404(pid)
    if (project.get("render") or {}).get("status") == "running":
        return err("Un rendu est déjà en cours")
    formats = (request.get_json(silent=True) or {}).get("formats") or ["vertical"]
    pipeline().start_render(pid, formats)
    return jsonify(project=storage().get_project(pid))


# -------------------------------------------------------------------- médias
@bp.get("/media/identity/<name>")
@login_required
def media_identity(name):
    try:
        name = safe_name(name)
    except ValueError:
        abort(404)
    if name == "logo_default.png":
        pipeline().logo_path()
    return send_from_directory(storage().identity_dir, name, max_age=0)


@bp.get("/media/p/<pid>/<folder>/<name>")
@login_required
def media_project(pid, folder, name):
    if folder not in ("clips", "keyframes", "exports", "audio"):
        abort(404)
    get_project_or_404(pid)
    try:
        name = safe_name(name)
    except ValueError:
        abort(404)
    base = storage().project_dir(pid)
    directory = base if folder == "audio" else base / folder
    download = request.args.get("dl") == "1"
    return send_from_directory(directory, name, as_attachment=download, max_age=0)
