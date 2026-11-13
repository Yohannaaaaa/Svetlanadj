"""Génère une piste de test hard techno synthétique (kick + hats + build + drop)."""
import subprocess
import numpy as np

def make_track(path, bpm=152.0, sr=44100, intro_bars=8, break_bars=8, drop_bars=12):
    beat = 60.0 / bpm
    total_beats = (intro_bars + break_bars + drop_bars) * 4
    n = int((total_beats * beat + 1) * sr)
    y = np.zeros(n, dtype=np.float32)
    t = np.arange(int(0.25 * sr)) / sr
    kick = (np.sin(2 * np.pi * (45 + 120 * np.exp(-t * 25)) * t) * np.exp(-t * 9)).astype(np.float32)
    rng = np.random.default_rng(0)
    hat = (rng.standard_normal(int(0.04 * sr)) * np.exp(-np.arange(int(0.04 * sr)) / (0.008 * sr)) * 0.25).astype(np.float32)
    for i in range(total_beats):
        pos = int(i * beat * sr)
        bar = i // 4
        in_break = intro_bars <= bar < intro_bars + break_bars
        if not in_break:
            gain = 1.0 if bar >= intro_bars + break_bars else 0.6
            y[pos:pos + len(kick)] += kick[: n - pos] * gain
        hp = pos + int(beat * sr / 2)
        if hp + len(hat) < n:
            y[hp:hp + len(hat)] += hat
    y /= np.abs(y).max()
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "f32le", "-ar", str(sr), "-ac", "1", "-i", "-", str(path)],
                   input=(y * 0.9).tobytes(), check=True)
    return (intro_bars + break_bars) * 4 * beat  # temps du drop
