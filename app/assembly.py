"""Montage final avec FFmpeg : découpe sur les temps, transitions, effets
synchronisés au BPM, logo, musique, exports 9:16 / 16:9.

Principe :
  1. Chaque plan est rendu en morceaux (« pieces ») au format cible, avec les
     effets calculés sur la grille de temps de la musique (flash, zoom punch…).
     Les plans marqués « beat_cuts » sont découpés à chaque temps et alternent
     plusieurs sources (montage de drop).
  2. Les plans sont enchaînés avec des transitions xfade calées pour que la
     durée totale reste exacte (la fin d'un plan est prolongée de la durée de
     la transition).
  3. Logo, fondu final, musique (normalisée à -14 LUFS pour les réseaux).
"""
import json
import subprocess
from pathlib import Path

FPS = 30
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp"}

FORMATS = {
    "vertical": {"label": "Vertical 9:16 (TikTok, Reels, Shorts)", "w": 1080, "h": 1920, "aspect": "9:16"},
    "horizontal": {"label": "Horizontal 16:9 (YouTube)", "w": 1920, "h": 1080, "aspect": "16:9"},
}

TRANSITION_DURATION = {"fade": 0.4, "fadeblack": 0.4, "fadewhite": 0.25, "zoomin": 0.35,
                       "pixelize": 0.3, "hblur": 0.3}


class RenderError(RuntimeError):
    pass


def run(cmd: list[str]):
    proc = subprocess.run(cmd, capture_output=True)
    if proc.returncode != 0:
        raise RenderError("FFmpeg : " + proc.stderr.decode(errors="ignore")[-1200:])
    return proc


def probe_duration(path: Path, ffprobe: str = "ffprobe") -> float:
    if Path(path).suffix.lower() in IMAGE_EXT:
        return float("inf")
    out = subprocess.run([ffprobe, "-v", "error", "-show_entries", "format=duration",
                          "-of", "json", str(path)], capture_output=True, text=True)
    try:
        return float(json.loads(out.stdout)["format"]["duration"])
    except (KeyError, ValueError, json.JSONDecodeError):
        raise RenderError(f"Durée illisible : {path}")


def fit_filter(w: int, h: int, mode: str) -> str:
    """Filtre (entrée [src] -> sortie [fit]) pour remplir le cadre."""
    if mode == "blur":
        return (
            f"[src]split[a][b];"
            f"[a]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},"
            f"boxblur=40:3,eq=brightness=-0.18[bg];"
            f"[b]scale={w}:{h}:force_original_aspect_ratio=decrease[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1[fit]"
        )
    return f"[src]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1[fit]"


def beat_expr(offset: float, phase: float, period: float) -> str:
    """Temps écoulé depuis le dernier temps (beat), en secondes, pour une
    expression FFmpeg évaluée image par image (variable t)."""
    base = offset - phase + 1000 * period
    return f"mod(t+{base:.4f}\\,{period:.4f})"


def build_piece_filter(w, h, fit, effects, offset, phase, period, speed, need, fade_in=None):
    chain = [fit_filter(w, h, fit)]
    v = "[fit]"
    steps = [f"fps={FPS}"]
    if "shake" in effects:
        steps.append(
            "crop=iw*0.94:ih*0.94:x='(iw-ow)/2+iw*0.022*sin(t*29)':y='(ih-oh)/2+ih*0.02*cos(t*23)',"
            f"scale={w}:{h}"
        )
    if "zoom_punch" in effects:
        be = beat_expr(offset, phase, period)
        steps.append(
            f"zoompan=z='1+0.07*exp(-{be.replace('t+', 'it+')}/0.10)':"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={w}x{h}:fps={FPS}"
        )
    if "red_grade" in effects:
        steps.append("colorbalance=rs=0.22:gs=-0.06:bs=-0.08:rm=0.10,eq=contrast=1.12:saturation=1.15")
    if "beat_flash" in effects:
        be = beat_expr(offset, phase, period)
        steps.append(f"eq=brightness='0.22*exp(-{be}/0.06)':eval=frame")
    if fade_in:
        steps.append(f"fade=in:st=0:d={fade_in}")
    steps.append("format=yuv420p,setsar=1")
    head = f"[0:v]setpts=(PTS-STARTPTS)*{speed:.4f},tpad=stop_mode=clone:stop_duration={need + 1:.3f}[src];"
    return head + chain[0] + ";" + v + ",".join(steps) + "[v]"


def plan_pieces(shots, sources, beats_v, period, slot_tails):
    """Découpe chaque plan en morceaux ; renvoie la liste des morceaux par plan."""
    plans = []
    for i, shot in enumerate(shots):
        start, end = float(shot["start"]), float(shot["end"])
        L = end - start + slot_tails[i]
        src = sources[i]
        pieces = []
        if "beat_cuts" in (shot.get("effects") or []):
            cuts = [b for b in beats_v if start + 0.05 < b < start + L - 0.05]
            bounds = [start] + cuts + [start + L]
            others = [s for j, s in enumerate(sources) if j != i and s["path"] != src["path"]]
            for j, (a, b) in enumerate(zip(bounds[:-1], bounds[1:])):
                if j % 2 == 1 and others and (b - a) > 0.08:
                    o = others[(j // 2) % len(others)]
                    avail = o["duration"] if o["duration"] != float("inf") else 5.0
                    off = ((j * 0.83) % max(0.01, avail - (b - a) - 0.05))
                    pieces.append({"src": o, "t0": a, "t1": b, "src_off": off})
                else:
                    pieces.append({"src": src, "t0": a, "t1": b, "src_off": a - start})
        else:
            pieces.append({"src": src, "t0": start, "t1": start + L, "src_off": 0.0})
        plans.append(pieces)
    return plans


def render_project(project: dict, pdir: Path, fmt_key: str, logo_path: Path | None,
                   fallback_image: Path | None, ffmpeg="ffmpeg", ffprobe="ffprobe",
                   fit: str = "cover", progress=None) -> Path:
    fmt = FORMATS[fmt_key]
    w, h = fmt["w"], fmt["h"]
    work = pdir / "work"
    work.mkdir(exist_ok=True)
    (pdir / "exports").mkdir(exist_ok=True)
    duration = float(project["duration"])
    shots = sorted(project["shots"], key=lambda s: float(s["start"]))
    if not shots:
        raise RenderError("Aucun plan à monter")

    # -------- grille de temps dans le référentiel de la vidéo
    analysis = project.get("analysis") or {}
    audio_start = float(project.get("audio_start") or 0)
    bpm = analysis.get("bpm") or 150.0
    period = 60.0 / bpm
    beats_abs = analysis.get("beats") or []
    beats_v = [round(b - audio_start, 4) for b in beats_abs if -period <= b - audio_start <= duration + period]
    if not beats_v:
        beats_v = [k * period for k in range(int(duration / period) + 2)]
    phase = beats_v[0] % period if beats_v else 0.0

    # -------- sources de chaque plan (clip > keyframe > référence)
    sources = []
    for s in shots:
        cand = None
        for key, folder in (("clip", "clips"), ("keyframe", "keyframes")):
            if s.get(key) and (pdir / folder / s[key]).exists():
                cand = pdir / folder / s[key]
                break
        cand = cand or fallback_image
        if not cand:
            raise RenderError(f"Le plan « {s.get('label')} » n'a ni clip, ni image.")
        sources.append({"path": cand, "duration": probe_duration(cand, ffprobe)})

    # -------- prolongations pour les transitions
    trans = [s.get("transition_in") or "cut" for s in shots]
    tails = []
    for i in range(len(shots)):
        nxt = trans[i + 1] if i + 1 < len(shots) else "cut"
        tails.append(TRANSITION_DURATION.get(nxt, 0.0))
    # le dernier plan va jusqu'à la fin de la vidéo
    shots[-1] = {**shots[-1], "end": duration}

    plans = plan_pieces(shots, sources, beats_v, period, tails)
    total_pieces = sum(len(p) for p in plans)
    done = 0

    shot_files = []
    for i, pieces in enumerate(plans):
        piece_files = []
        effects = set(shots[i].get("effects") or [])
        frames_cursor = round(pieces[0]["t0"] * FPS)
        for j, pc in enumerate(pieces):
            end_frame = round(pc["t1"] * FPS)
            n = max(1, end_frame - frames_cursor)
            frames_cursor = end_frame
            need = n / FPS
            src = pc["src"]
            is_img = Path(src["path"]).suffix.lower() in IMAGE_EXT
            speed = 1.0
            if "slowmo" in effects:
                speed = 1.6
            if not is_img:
                avail = max(0.05, src["duration"] - pc["src_off"])
                if avail * speed < need:
                    speed = min(2.0, need / avail)
            fade_in = None
            if i == 0 and j == 0 and trans[0] in ("fadeblack", "fade"):
                fade_in = TRANSITION_DURATION.get(trans[0], 0.4)
            elif i == 0 and j == 0 and trans[0] == "fadewhite":
                fade_in = 0.25
            vf = build_piece_filter(w, h, fit, effects, pc["t0"], phase, period, speed, need, fade_in)
            out = work / f"{fmt_key}_p{i:02d}_{j:03d}.mp4"
            inp = (["-loop", "1", "-framerate", str(FPS), "-t", f"{need + 1:.3f}", "-i", str(src["path"])]
                   if is_img else ["-ss", f"{max(0.0, pc['src_off']):.3f}", "-i", str(src["path"])])
            run([ffmpeg, "-y", "-v", "error", *inp, "-filter_complex", vf, "-map", "[v]",
                 "-frames:v", str(n), "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "16",
                 "-pix_fmt", "yuv420p", "-r", str(FPS), str(out)])
            piece_files.append(out)
            done += 1
            if progress:
                progress(done / (total_pieces + 2), f"Plan {i + 1} – morceau {j + 1}/{len(pieces)}")
        shot_file = work / f"{fmt_key}_shot{i:02d}.mp4"
        if len(piece_files) == 1:
            piece_files[0].replace(shot_file)
        else:
            lst = work / f"{fmt_key}_shot{i:02d}.txt"
            lst.write_text("".join(f"file '{p.name}'\n" for p in piece_files))
            run([ffmpeg, "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
                 "-c", "copy", str(shot_file)])
        shot_files.append(shot_file)

    # -------- assemblage final
    if progress:
        progress((total_pieces + 1) / (total_pieces + 2), "Assemblage, logo et musique")
    inputs = []
    for f in shot_files:
        inputs += ["-i", str(f)]
    filters = []
    for i in range(len(shot_files)):
        filters.append(f"[{i}:v]fps={FPS},format=yuv420p,setsar=1,settb=AVTB,setpts=PTS-STARTPTS[s{i}]")
    acc = "[s0]"
    for i in range(1, len(shot_files)):
        t = trans[i]
        out = f"[x{i}]"
        if t in TRANSITION_DURATION:
            off = float(shots[i]["start"])
            filters.append(f"{acc}[s{i}]xfade=transition={t}:duration={TRANSITION_DURATION[t]}:offset={off:.3f}{out}")
        else:
            filters.append(f"{acc}[s{i}]concat=n=2:v=1:a=0{out}")
        acc = out

    idx = len(shot_files)
    logo_cfg = project.get("logo") or {}
    mode = logo_cfg.get("mode", "drop")
    if logo_path and Path(logo_path).exists() and mode != "none":
        inputs += ["-loop", "1", "-t", f"{duration:.3f}", "-i", str(logo_path)]
        at = float(logo_cfg.get("at", project.get("drop_at") or 0))
        layers = []
        if mode == "both":
            filters.append(f"[{idx}:v]split[lgw][lgb]")
            wm_src, big_src = "[lgw]", "[lgb]"
        else:
            wm_src = big_src = f"[{idx}:v]"
        if mode in ("watermark", "both"):
            ww = int(w * (0.22 if w < h else 0.14))
            end_wm = at if mode == "both" else duration
            filters.append(f"{wm_src}scale={ww}:-1,format=rgba,colorchannelmixer=aa=0.85[wm]")
            layers.append(("[wm]", f"W-w-{int(w * 0.04)}", f"{int(h * 0.03)}", f"between(t,0,{end_wm:.3f})"))
        if mode in ("drop", "both"):
            bw = int(w * (0.72 if w < h else 0.42))
            filters.append(f"{big_src}scale={bw}:-1,format=rgba,fade=in:st={at:.3f}:d=0.35:alpha=1[big]")
            y = "(H-h)/2" if w > h else "H*0.62-h/2"
            layers.append(("[big]", "(W-w)/2", y, f"gte(t,{at:.3f})"))
        for k, (lbl, x, y, en) in enumerate(layers):
            out = f"[lo{k}]"
            filters.append(f"{acc}{lbl}overlay=x={x}:y={y}:enable='{en}':format=auto{out}")
            acc = out
        idx += 1
    fade_out = min(0.5, duration / 10)
    filters.append(f"{acc}fade=out:st={duration - fade_out:.3f}:d={fade_out:.3f},format=yuv420p[vout]")

    audio = project.get("audio")
    if audio and (pdir / audio).exists():
        inputs += ["-ss", f"{audio_start:.3f}", "-t", f"{duration + 0.5:.3f}", "-i", str(pdir / audio)]
        fo = min(0.8, duration / 6)
        filters.append(
            f"[{idx}:a]atrim=0:{duration:.3f},asetpts=PTS-STARTPTS,afade=in:d=0.02,"
            f"afade=out:st={duration - fo:.3f}:d={fo:.3f},loudnorm=I=-14:TP=-1.0:LRA=11,"
            f"aresample=48000[aout]"
        )
    else:
        inputs += ["-f", "lavfi", "-t", f"{duration:.3f}", "-i", "anullsrc=r=48000:cl=stereo"]
        filters.append(f"[{idx}:a]anull[aout]")

    slug = "".join(c if c.isalnum() else "_" for c in project.get("title", "svetlana").lower()).strip("_")[:40]
    out = pdir / "exports" / f"{slug}_{fmt_key}.mp4"
    run([ffmpeg, "-y", "-v", "error", *inputs, "-filter_complex", ";".join(filters),
         "-map", "[vout]", "-map", "[aout]", "-t", f"{duration:.3f}",
         "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-profile:v", "high",
         "-pix_fmt", "yuv420p", "-r", str(FPS), "-c:a", "aac", "-b:a", "320k", "-ar", "48000",
         "-movflags", "+faststart", str(out)])

    # Miniature (juste après le drop)
    thumb_t = min(duration - 0.1, float(project.get("drop_at") or 0) + 0.7)
    run([ffmpeg, "-y", "-v", "error", "-ss", f"{thumb_t:.2f}", "-i", str(out), "-frames:v", "1",
         "-q:v", "2", str(out.with_suffix(".jpg"))])

    for f in work.glob(f"{fmt_key}_*"):
        f.unlink(missing_ok=True)
    if progress:
        progress(1.0, "Terminé")
    return out
