"""Magic edit: repaint only the brushed area of an existing picture, keeping everything else.

How: crop a box around the mask (so the model sees the area big, plus enough of its surroundings),
ask FLUX.2 klein 4B (Apache-2.0, a real image-EDIT model) to change that crop using the crop itself as
the reference image, then paste the new pixels back through a soft-edged copy of the mask.
Pixels outside the mask are never touched; the original alpha channel is kept.
"""
import subprocess
from PIL import Image, ImageFilter


def mask_box(m, W, H, side=768):
    """Crop box around the mask: mask size plus generous context, at least 1/3 of the picture."""
    bb = m.point(lambda v: 255 if v > 127 else 0).getbbox()
    if not bb:
        return None
    x0, y0, x1, y1 = bb
    bw, bh = x1 - x0, y1 - y0
    s = max(bw, bh) * 1.8 + 48
    s = max(s, min(W, H) / 3)
    s = min(s, max(W, H))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    w, h = min(W, s), min(H, s)
    l = int(max(0, min(W - w, cx - w / 2)))
    t = int(max(0, min(H - h, cy - h / 2)))
    return (l, t, int(l + w), int(t + h))


def snap(v, lo=256, hi=1024):
    return max(lo, min(hi, int(round(v / 64)) * 64))


def instruction(prompt):
    p = prompt.strip().rstrip(".")
    return (f"{p}. Change only that part of the picture. Keep everything else exactly the same: "
            "same framing, same pose, same lighting, same colours and same painting style.")


def run(sd, env, init, mask, prompt, seed, out_png, side=768, steps=4):
    """Returns (ok, log). Writes out_png at the original size (RGBA)."""
    orig = Image.open(init).convert("RGBA")
    W, H = orig.size
    m = Image.open(mask).convert("L").resize((W, H), Image.NEAREST)
    box = mask_box(m, W, H)
    if not box:
        return False, "empty mask"
    crop = orig.crop(box)
    cw, ch = crop.size
    k = side / max(cw, ch)
    gw, gh = snap(cw * k), snap(ch * k)
    flat = crop.convert("RGB")  # keeps the painted colour under any transparency
    flat.resize((gw, gh), Image.LANCZOS).save("me_ref.png")
    cmd = [sd, "-t", str(env.get("THREADS", 4)), "-o", "me_out.png",
           "--diffusion-model", env["KLEIN"], "--vae", env["VAE2"], "--llm", env["QWEN"],
           "-r", "me_ref.png", "-p", instruction(prompt), "--cfg-scale", "1.0",
           "--sampling-method", "euler", "--steps", str(steps), "-W", str(gw), "-H", str(gh),
           "--seed", str(seed)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    log = (r.stdout + r.stderr)[-3000:]
    try:
        gen = Image.open("me_out.png").convert("RGBA").resize((cw, ch), Image.LANCZOS)
    except Exception:
        return False, log
    # soft edge: grow the mask a little, then feather it, so the seam disappears
    mc = m.crop(box)
    feather = max(2, min(cw, ch) // 60)
    mc = mc.filter(ImageFilter.MaxFilter(feather * 2 + 1)).filter(ImageFilter.GaussianBlur(feather))
    newc = Image.composite(gen, crop, mc)
    newc.putalpha(crop.getchannel("A"))  # never change the cut-out shape
    res = orig.copy()
    res.paste(newc, box[:2])
    res.save(out_png)
    return True, log
