"""Forge key pass: the background must end up exactly the key colour, including
enclosed key-tinted patches (e.g. shadow between legs), without eating the subject.

Run: python tests/test_forge_key.py   (needs pillow)
"""
import pathlib, sys
from PIL import Image, ImageDraw
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "forge"))
from keyfix import keyfix

fails = 0
def check(name, ok, extra=""):
    global fails
    print(("PASS " if ok else "FAIL ") + name + (f"  ({extra})" if extra else ""))
    fails += 0 if ok else 1

def synth(key, bg, patch, subject, skin=None):
    im = Image.new("RGB", (128, 128), bg); d = ImageDraw.Draw(im)
    d.rectangle([40, 20, 88, 110], fill=subject)        # body
    d.rectangle([56, 80, 72, 110], fill=patch)          # enclosed gap between legs
    d.rectangle([56, 110, 72, 112], fill=subject)       # boots close the gap
    if skin: d.rectangle([44, 24, 52, 32], fill=skin)   # a small key-ish detail on the subject
    return im

# 1. real e2e render: enclosed olive shadow patch between the legs
real = ROOT / "forge/results/e2etest01/1.png"
if real.exists():
    im = keyfix(Image.open(real), "#00FF00"); px = im.load()
    left = [px[x, 470] for x in range(225, 260) if px[x, 470][1] > 120 and px[x, 470] != (0, 255, 0)]
    check("e2e #1: olive patch between legs keyed", len(left) <= 2, f"{len(left)} px left")
    dark = sum(1 for x in range(im.width) for y in range(im.height) if max(px[x, y]) < 60)
    check("e2e #1: dark subject pixels kept", dark > 5000, f"{dark}")

# 2. synthetic green key, olive enclosed patch, dark ink subject
im = keyfix(synth("#00FF00", (6, 250, 4), (118, 150, 44), (30, 28, 36)), "#00FF00"); px = im.load()
check("green: border exact key", px[0, 0] == (0, 255, 0) and px[127, 127] == (0, 255, 0))
check("green: enclosed olive patch keyed", px[64, 95] == (0, 255, 0), str(px[64, 95]))
check("green: subject untouched", px[48, 60] == (30, 28, 36), str(px[48, 60]))

# 3. magenta key: a green subject must survive (key is per-game)
im = keyfix(synth("#FF00FF", (250, 4, 250), (150, 60, 140), (60, 160, 70)), "#FF00FF"); px = im.load()
check("magenta: enclosed mauve patch keyed", px[64, 95] == (255, 0, 255), str(px[64, 95]))
check("magenta: green subject untouched", px[48, 60] == (60, 160, 70), str(px[48, 60]))

# 4. subject with a dark-green coat on a green key keeps its coat
im = keyfix(synth("#00FF00", (0, 255, 0), (0, 255, 0), (36, 47, 43), skin=(60, 70, 50)), "#00FF00"); px = im.load()
check("green: dark green coat kept", px[48, 60] == (36, 47, 43), str(px[48, 60]))
check("green: muted detail kept", px[46, 26] == (60, 70, 50), str(px[46, 26]))

print("ALL PASS" if not fails else f"{fails} FAILED"); sys.exit(1 if fails else 0)
