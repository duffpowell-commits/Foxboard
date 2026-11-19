"""Magic edit (forge/magic_edit.py): only brushed pixels change, cut-out alpha is kept, crop box hugs the mask.
Uses a fake sd binary that paints the whole frame red, so no model download.
Run: python tests/test_magic_edit.py   (needs pillow)"""
import os, pathlib, stat, sys, tempfile
from PIL import Image, ImageDraw
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "forge"))
import magic_edit as me
fails = 0
def check(name, ok, info=""):
    global fails
    print(("PASS " if ok else "FAIL ") + name, "" if ok else info); fails += 0 if ok else 1
d = pathlib.Path(tempfile.mkdtemp()); os.chdir(d)
fake = d / "sd"
fake.write_text("#!/usr/bin/env python3\nimport sys\nfrom PIL import Image\na=sys.argv\nW=int(a[a.index('-W')+1]);H=int(a[a.index('-H')+1])\n"
                "Image.new('RGB',(W,H),(255,0,0)).save(a[a.index('-o')+1])\n")
fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
im = Image.new("RGBA", (600, 400), (20, 40, 60, 255)); ImageDraw.Draw(im).rectangle([0, 0, 599, 60], fill=(20, 40, 60, 0))  # transparent strip
im.save("init.png")
m = Image.new("L", (600, 400), 0); ImageDraw.Draw(m).rectangle([280, 180, 340, 240], fill=255); m.save("mask.png")
ok, log = me.run(str(fake), {"KLEIN": "k", "VAE2": "v", "QWEN": "q"}, "init.png", "mask.png", "a red apple", 1, "out.png")
check("run succeeds", ok, log)
out = Image.open("out.png").convert("RGBA")
check("same size", out.size == im.size, out.size)
check("centre of mask repainted", out.getpixel((310, 210))[:3] == (255, 0, 0), out.getpixel((310, 210)))
check("far outside mask untouched", out.getpixel((50, 350)) == (20, 40, 60, 255) and out.getpixel((590, 390)) == (20, 40, 60, 255))
check("transparent strip stays transparent", out.getpixel((300, 30))[3] == 0, out.getpixel((300, 30)))
b = me.mask_box(m, 600, 400)
check("crop box contains mask with context", b[0] < 280 and b[1] < 180 and b[2] > 340 and b[3] > 240 and (b[2] - b[0]) < 600, b)
check("empty mask refused", me.mask_box(Image.new("L", (10, 10), 0), 10, 10) is None)
print("ALL PASS" if not fails else f"{fails} FAILED"); sys.exit(1 if fails else 0)
