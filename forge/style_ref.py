"""Style-reference helper for Forge.

Why a workaround, not IP-Adapter: stable-diffusion.cpp's --ip-adapter path only
supports SD 1.5 and SDXL. Forge's default model is FLUX.1-schnell, which has no
IP-Adapter or FLUX Redux hook in sd.cpp. Running a second SDXL stack just for
references would be a different look and a tight fit on a 16 GB free runner.
Kontext / FLUX.2 are different models and are already reserved for Magic edit.

What this does: shuffles overlapping crops of the reference into a WxH "style
board" (so a character silhouette does not sit in the same place), then
render_one.py img2imgs from that board at a fairly high strength so the text
prompt still leads. Palette and brushwork can bleed through. This will not
hold a character the way Grok's attached reference does. Use a style-only crop
(brushwork and outlines, no identity) when you can.
"""
from __future__ import annotations

import io
import random
from pathlib import Path

from PIL import Image, ImageFilter, ImageOps


def load_b64(path: str | Path) -> Image.Image:
    text = Path(path).read_text().strip()
    kind, data = text.split(":", 1)
    import base64
    im = Image.open(io.BytesIO(base64.b64decode(data)))
    return im.convert("RGB")


def clamp_ref_strength(value, default=0.55) -> float:
    try:
        v = float(value)
    except (TypeError, ValueError):
        v = default
    return max(0.15, min(0.85, v))


def img2img_strength(ref_strength, default=0.55) -> float:
    """Map 'how hard to follow the style image' to FLUX img2img strength.

    Higher ref_strength -> closer to the style board (lower img2img strength).
    The floor is 0.72 so the prompt still composes a new picture (a flat
    sketch at <=0.7 can come back almost unchanged; runner A/Bs Nov 19).
    The ceiling is 0.92 so a weak reference almost acts like txt2img.
    """
    r = clamp_ref_strength(ref_strength, default)
    # 0.15 -> 0.92, 0.85 -> 0.72
    t = (r - 0.15) / 0.70
    return round(0.92 - 0.20 * t, 2)


def style_board(im: Image.Image, w: int, h: int, seed: int, tiles: int = 16) -> Image.Image:
    """Build a WxH canvas of random overlapping crops. Same seed => same board."""
    src = im.convert("RGB")
    if src.width < 8 or src.height < 8:
        return src.resize((w, h), Image.Resampling.LANCZOS)
    rng = random.Random(int(seed) ^ 0xA5A5)
    # Fill with a slightly blurred shrink of the whole ref so empty gaps keep the palette.
    base = ImageOps.fit(src, (w, h), method=Image.Resampling.LANCZOS)
    base = base.filter(ImageFilter.GaussianBlur(radius=max(2, min(w, h) // 40)))
    out = base.copy()
    short = min(src.width, src.height)
    for _ in range(tiles):
        frac = rng.uniform(0.18, 0.42)
        cw = max(8, int(short * frac))
        ch = max(8, int(short * frac * rng.uniform(0.7, 1.3)))
        cw = min(cw, src.width)
        ch = min(ch, src.height)
        x0 = rng.randint(0, src.width - cw)
        y0 = rng.randint(0, src.height - ch)
        crop = src.crop((x0, y0, x0 + cw, y0 + ch))
        # Scale the crop so several of them cover the board, not a 1:1 paste of the figure.
        tw = max(8, int(w * rng.uniform(0.28, 0.55)))
        th = max(8, int(h * rng.uniform(0.28, 0.55)))
        patch = crop.resize((tw, th), Image.Resampling.LANCZOS)
        px = rng.randint(-tw // 5, w - tw + tw // 5)
        py = rng.randint(-th // 5, h - th + th // 5)
        out.paste(patch, (px, py))
    return out
