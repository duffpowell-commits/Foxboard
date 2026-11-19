"""Art loop scorer: flags the faults Claude kept seeing by eye in Forge takes.

Synthetic figures on a #00FF00 key: a clean one passes, and each fault
(holes punched by the key, floor shadow, watermark, cropped head, seam) is flagged.
Run: python tests/test_art_loop.py   (needs pillow)
"""
import pathlib, sys, tempfile, os
from PIL import Image, ImageDraw
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools" / "claude"))
import art_loop

fails = 0
def check(name, ok, extra=""):
    global fails
    print(("PASS " if ok else "FAIL ") + name + (f"  ({extra})" if extra else ""))
    fails += 0 if ok else 1

KEY = (0, 255, 0); INK = (32, 45, 64); COAT = (51, 68, 90); BOOT = (42, 23, 10)

def figure(holes=False, shadow=False, mark=False, crop=False):
    im = Image.new("RGB", (256, 512), KEY); d = ImageDraw.Draw(im)
    top = -10 if crop else 40
    d.ellipse([100, top, 156, top + 70], fill=INK)              # hooded head
    d.rectangle([84, top + 60, 172, 330], fill=COAT)            # body
    d.rectangle([92, 330, 124, 470], fill=COAT)                 # left leg
    d.rectangle([132, 330, 164, 470], fill=COAT)                # right leg (gap between = legit)
    d.rectangle([88, 470, 128, 490], fill=BOOT); d.rectangle([128, 470, 168, 490], fill=BOOT)
    if holes:
        for y in range(120, 320, 24):                           # key colour punched through the torso
            d.rectangle([92, y, 164, y + 12], fill=KEY)
    if shadow:
        d.ellipse([20, 478, 236, 505], fill=(8, 8, 10))         # wide dark floor shadow
        d.rectangle([88, 470, 168, 490], fill=BOOT)
    if mark:
        d.rectangle([200, 486, 248, 500], fill=(200, 200, 200)) # corner watermark
    return im

def score(im, kind="sprite", aspect=None):
    p = os.path.join(tempfile.mkdtemp(), "0.png"); im.save(p)
    return art_loop.score_one(p, "lethemoor", kind, aspect, "#00FF00")

clean = score(figure(), aspect=0.2)
check("clean figure has no flags", clean["flags"] == [], clean["flags"])
r = score(figure(holes=True)); check("holes punched by the key are flagged", any("ate the subject" in f for f in r["flags"]), r["flags"])
check("eaten figure scores below clean", r["score"] < clean["score"], f"{r['score']} vs {clean['score']}")
r = score(figure(shadow=True)); check("floor shadow flagged", any("floor shadow" in f for f in r["flags"]), r["flags"])
r = score(figure(mark=True)); check("watermark flagged", any("stray" in f for f in r["flags"]), r["flags"])
r = score(figure(crop=True)); check("cropped head flagged", "head/top cut off" in r["flags"], r["flags"])

# textures: a tiling pattern passes the seam check, a left-dark/right-light ramp fails it
tile = Image.new("RGB", (256, 256), (20, 29, 43)); d = ImageDraw.Draw(tile)
for i in range(0, 256, 32):
    d.rectangle([i, i, i + 16, i + 16], fill=(51, 68, 90))
check("seamless texture passes", not any("seamless" in f for f in score(tile, "texture")["flags"]))
ramp = Image.new("RGB", (256, 256)); ramp.putdata([(x // 2, x // 2, x // 2) for y in range(256) for x in range(256)])
check("seam flagged on a ramp", any("seamless" in f for f in score(ramp, "texture")["flags"]))

print(f"\n{'ALL PASS' if not fails else f'{fails} FAILED'}")
sys.exit(1 if fails else 0)
