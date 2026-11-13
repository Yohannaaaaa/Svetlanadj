"""Génère un logo SVETLANA par défaut (PNG transparent, chrome + lueur rouge)
si l'utilisateur n'a pas encore importé son propre logo."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]


def _font(size):
    for p in FONT_CANDIDATES:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default(size=size)


def make_default_logo(out_path: Path, text: str = "SVETLANA", subtitle: str = "HARD TECHNO • HARDSTYLE") -> Path:
    size = 220
    font = _font(size)
    sub_font = _font(int(size * 0.2))
    spacing = int(size * 0.18)
    widths = [font.getbbox(ch)[2] - font.getbbox(ch)[0] for ch in text]
    text_w = sum(widths) + spacing * (len(text) - 1)
    pad = 120
    W, H = text_w + pad * 2, int(size * 1.9) + pad
    base_y = pad // 2

    mask = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(mask)
    x = pad
    for ch, cw in zip(text, widths):
        d.text((x - font.getbbox(ch)[0], base_y), ch, font=font, fill=255)
        x += cw + spacing
    sub_w = d.textlength(subtitle, font=sub_font)
    d.text(((W - sub_w) / 2, base_y + size * 1.25), subtitle, font=sub_font, fill=200)

    # Dégradé chrome vertical
    chrome = Image.new("RGBA", (W, H))
    cd = ImageDraw.Draw(chrome)
    stops = [(0.0, (255, 255, 255)), (0.45, (190, 196, 205)), (0.5, (120, 126, 136)),
             (0.62, (225, 230, 236)), (1.0, (150, 155, 165))]
    for yy in range(H):
        r = (yy - base_y) / (size * 1.2)
        r = min(1.0, max(0.0, r))
        for (a, ca), (b, cb) in zip(stops[:-1], stops[1:]):
            if a <= r <= b:
                k = (r - a) / (b - a)
                col = tuple(int(ca[i] + (cb[i] - ca[i]) * k) for i in range(3))
                break
        cd.line([(0, yy), (W, yy)], fill=col + (255,))

    glow = Image.new("RGBA", (W, H), (230, 20, 40, 0))
    glow.putalpha(mask.filter(ImageFilter.GaussianBlur(28)).point(lambda v: int(v * 0.9)))
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    out = Image.alpha_composite(out, glow)
    letters = chrome.copy()
    letters.putalpha(mask)
    out = Image.alpha_composite(out, letters)
    out = out.crop(out.getbbox())
    out.save(out_path)
    return out_path
