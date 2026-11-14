"""Analyse musicale : BPM, grille de temps (beats), mesures, drops, énergie.

Implémentation en NumPy pur (décodage via FFmpeg) pour rester légère sur Render.
Optimisée pour la musique électronique à tempo fixe (hard techno, hardstyle,
rawstyle : 140–160 BPM).
"""
import subprocess

import numpy as np

SR = 22050
N_FFT = 2048
HOP = 512


def decode_audio(path: str, ffmpeg: str = "ffmpeg", sr: int = SR) -> np.ndarray:
    cmd = [ffmpeg, "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(sr),
           "-f", "f32le", "-"]
    proc = subprocess.run(cmd, capture_output=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError("Impossible de décoder l'audio : " + proc.stderr.decode(errors="ignore")[-400:])
    y = np.frombuffer(proc.stdout, dtype=np.float32)
    if y.size < sr:
        raise RuntimeError("Fichier audio trop court ou vide")
    return y


def _spectral_features(y: np.ndarray, sr: int):
    """Renvoie (onset_envelope, low_band_energy, rms) par trame."""
    n_frames = 1 + (len(y) - N_FFT) // HOP
    window = np.hanning(N_FFT).astype(np.float32)
    freqs = np.fft.rfftfreq(N_FFT, 1.0 / sr)
    low_mask = freqs < 150          # kick / basse
    prev = None
    flux = np.zeros(n_frames, dtype=np.float32)
    low = np.zeros(n_frames, dtype=np.float32)
    rms = np.zeros(n_frames, dtype=np.float32)
    chunk = 256  # petits blocs : pic mémoire réduit (Render 512 Mo)
    for start in range(0, n_frames, chunk):
        stop = min(n_frames, start + chunk)
        idx = np.arange(start, stop)[:, None] * HOP + np.arange(N_FFT)[None, :]
        frames = y[idx] * window
        mag = np.abs(np.fft.rfft(frames, axis=1))
        logmag = np.log1p(100.0 * mag)
        if prev is None:
            diff = np.zeros_like(logmag)
            diff[1:] = logmag[1:] - logmag[:-1]
        else:
            diff = logmag - np.vstack([prev[None, :], logmag[:-1]])
        flux[start:stop] = np.maximum(diff, 0).mean(axis=1)
        low[start:stop] = (mag[:, low_mask] ** 2).mean(axis=1)
        rms[start:stop] = np.sqrt((frames ** 2).mean(axis=1))
        prev = logmag[-1]
    # Normalisation de l'enveloppe d'onset (retrait de la tendance locale)
    k = 16
    kernel = np.ones(k) / k
    local = np.convolve(flux, kernel, mode="same")
    onset = np.maximum(flux - local, 0)
    if onset.max() > 0:
        onset /= onset.max()
    return onset, low, rms


def _estimate_tempo(onset: np.ndarray, fps: float, bpm_min=60, bpm_max=200, prior_bpm=150.0):
    o = onset - onset.mean()
    n = len(o)
    size = 1 << int(np.ceil(np.log2(2 * n)))
    spec = np.fft.rfft(o, size)
    ac = np.fft.irfft(spec * np.conj(spec))[:n]
    lag_min = int(fps * 60 / bpm_max)
    lag_max = int(fps * 60 / bpm_min)
    lags = np.arange(lag_min, min(lag_max, n - 1))
    bpms = 60.0 * fps / lags
    # Préférence douce (log-gaussienne) pour le tempo du genre
    prior = np.exp(-0.5 * (np.log2(bpms / prior_bpm) / 0.9) ** 2)
    score = ac[lags] * prior
    coarse = bpms[int(np.argmax(score))]
    # Affinage par filtre en peigne (0.05 BPM) autour de la valeur grossière
    best_bpm, best_score = coarse, -1.0
    for bpm in np.arange(coarse - 3, coarse + 3, 0.05):
        period = 60.0 * fps / bpm
        s, _ = _best_phase(onset, period)
        if s > best_score:
            best_bpm, best_score = bpm, s
    return float(best_bpm)


def _best_phase(onset: np.ndarray, period: float):
    n = len(onset)
    best, best_phase = -1.0, 0.0
    for phase in np.arange(0, period, 1.0):
        pos = np.round(np.arange(phase, n, period)).astype(int)
        pos = pos[pos < n]
        s = float(onset[pos].mean()) if len(pos) else 0.0
        if s > best:
            best, best_phase = s, phase
    return best, best_phase


def _refine_grid(y: np.ndarray, sr: int, bpm: float, coarse_phase: float):
    """Affine conjointement le tempo (±0.8 BPM, pas 0.01) et la phase (~3 ms)
    sur les attaques de l'enveloppe temporelle, plus précises que le flux
    spectral pour les kicks."""
    hop = 64
    n = len(y) // hop
    env = np.abs(y[: n * hop]).reshape(n, hop).max(axis=1)
    attack = np.maximum(np.diff(env, prepend=env[0]), 0)
    fps = sr / hop
    best = (-1.0, bpm, coarse_phase)
    for cand in np.arange(bpm - 0.8, bpm + 0.8, 0.01):
        period = 60.0 * fps / cand
        k = np.arange(0, n / period)
        for ph in np.arange(0, period, 1.0):
            pos = np.round(ph + k * period).astype(int)
            pos = pos[pos < n]
            s = float(attack[pos].mean())
            if s > best[0]:
                best = (s, cand, ph / fps)
    return float(best[1]), float(best[2])


def _smooth(x, k):
    if len(x) < k or k < 2:
        return x
    return np.convolve(x, np.ones(k) / k, mode="same")


def analyze(path: str, ffmpeg: str = "ffmpeg", prior_bpm: float = 150.0) -> dict:
    y = decode_audio(path, ffmpeg)
    sr = SR
    duration = len(y) / sr
    fps = sr / HOP
    onset, low, rms = _spectral_features(y, sr)
    n = len(onset)

    bpm = _estimate_tempo(onset, fps, prior_bpm=prior_bpm)
    period = 60.0 * fps / bpm
    _, phase = _best_phase(onset, period)
    bpm, phase_s = _refine_grid(y, sr, bpm, phase * HOP / sr)
    period = 60.0 * fps / bpm
    if phase_s - 60.0 / bpm > -0.03:   # le tout premier temps est à ~0 s
        phase_s = max(0.0, phase_s - 60.0 / bpm)
    phase = phase_s * fps
    beat_frames = np.arange(phase, n, period)
    beats = (beat_frames * HOP / sr).tolist()

    # Énergie par temps (beat)
    edges = np.append(np.round(beat_frames).astype(int), n)
    beat_low = np.array([low[a:b].mean() if b > a else 0 for a, b in zip(edges[:-1], edges[1:])])
    beat_rms = np.array([rms[a:b].mean() if b > a else 0 for a, b in zip(edges[:-1], edges[1:])])
    beat_onset = np.array([onset[a:b].max() if b > a else 0 for a, b in zip(edges[:-1], edges[1:])])

    # Premier temps de mesure : le décalage (0..3) qui maximise les changements
    # d'énergie sur les débuts de mesure (les phrases commencent sur le "1").
    novelty = np.abs(np.diff(np.log1p(beat_low * 1e3), prepend=0))
    bar_offset = int(np.argmax([novelty[o::4].mean() + beat_onset[o::4].mean() * 0.25 for o in range(4)]))
    downbeats = beats[bar_offset::4]

    # Énergie par mesure
    bars_low, bars_rms = [], []
    for i in range(bar_offset, len(beats), 4):
        bars_low.append(beat_low[i:i + 4].mean())
        bars_rms.append(beat_rms[i:i + 4].mean())
    bars_low = np.array(bars_low)
    bars_rms = np.array(bars_rms)
    ref = np.percentile(bars_low, 90) if len(bars_low) else 1.0
    bl = bars_low / (ref + 1e-9)

    # Drops : forte hausse de la basse après une section plus calme, qui se maintient
    drops = []
    w = 4
    scores = np.zeros(len(bl))
    for b in range(w, len(bl) - 2):
        before = bl[max(0, b - w):b].mean()
        after = bl[b:b + w].mean()
        scores[b] = (after - before) * min(1.0, after)
    order = np.argsort(-scores)
    taken = []
    for b in order:
        if scores[b] < 0.25:
            break
        if all(abs(b - t) >= 16 for t in taken):
            taken.append(int(b))
        if len(taken) >= 6:
            break
    for b in sorted(taken):
        t = downbeats[b] if b < len(downbeats) else None
        if t is not None:
            drops.append({"time": round(t, 3), "bar": b, "strength": round(float(min(1.0, scores[b])), 3)})

    # Breakdowns : chute nette de la basse
    breakdowns = []
    for b in range(w, len(bl) - w):
        if bl[b - w:b].mean() > 0.6 and bl[b:b + w].mean() < 0.3 and (not breakdowns or b - breakdowns[-1]["bar"] >= 16):
            breakdowns.append({"time": round(downbeats[b], 3), "bar": b})

    # Sections (haute / basse énergie) par mesure
    sections = []
    level = _smooth(bl, 3) > 0.5
    start = 0
    for b in range(1, len(level) + 1):
        if b == len(level) or level[b] != level[start]:
            sections.append({
                "start": round(downbeats[start], 3),
                "end": round(downbeats[b] if b < len(downbeats) else duration, 3),
                "energy": "high" if level[start] else "low",
            })
            start = b

    # Courbe d'énergie réduite pour l'affichage (≈ 600 points)
    pts = 600
    step = max(1, len(rms) // pts)
    env = rms[: (len(rms) // step) * step].reshape(-1, step).max(axis=1)
    env = (env / (env.max() + 1e-9)).round(3).tolist()

    return {
        "duration": round(duration, 3),
        "bpm": round(bpm, 2),
        "beat_period": round(60.0 / bpm, 4),
        "beats": [round(b, 3) for b in beats],
        "downbeats": [round(b, 3) for b in downbeats],
        "drops": drops,
        "breakdowns": breakdowns,
        "sections": sections,
        "envelope": env,
        "envelope_step": round(step * HOP / sr, 4),
    }


def suggest_start(analysis: dict, video_duration: float, drop_at: float) -> float:
    """Choisit le début de l'extrait pour que le drop principal tombe à `drop_at` s
    dans la vidéo, aligné sur un premier temps de mesure."""
    duration = analysis["duration"]
    drops = analysis.get("drops") or []
    if drops:
        main = max(drops, key=lambda d: d["strength"])
        start = main["time"] - drop_at
    else:
        # Sans drop détecté : la section la plus énergique
        highs = [s for s in analysis.get("sections", []) if s["energy"] == "high"]
        start = (highs[0]["start"] - drop_at) if highs else 0.0
    start = max(0.0, min(start, max(0.0, duration - video_duration)))
    return round(start, 3)
