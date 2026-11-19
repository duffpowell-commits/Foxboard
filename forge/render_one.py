"""Render one version of one Forge job with FLUX.1-schnell (stable-diffusion.cpp, CPU) and commit it."""
import base64, io, json, os, pathlib, re, subprocess, sys, time
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from keyfix import keyfix
jid, k = sys.argv[1], int(sys.argv[2])
job = json.loads(pathlib.Path(f"forge/jobs/{jid}.json").read_text())
env = dict(l.strip().split("=", 1) for l in open("models.env") if "=" in l)
W = max(256, min(1024, int(job.get("w", 768)) // 64 * 64)); H = max(256, min(1024, int(job.get("h", 768)) // 64 * 64))
seed = int(job.get("seed", 1)) + k
prompt = str(job.get("prompt", ""))[:1500]
out = pathlib.Path(f"forge/results/{jid}"); out.mkdir(parents=True, exist_ok=True)
png = out / f"{k}.png"
mode = str(job.get("mode", "new"))
def b64file(rel, dst):
    t = pathlib.Path(rel).read_text().strip(); kind, data = t.split(":", 1)
    pathlib.Path(dst).write_bytes(base64.b64decode(data)); return dst
base = [os.environ["SD"], "-t", str(os.cpu_count()), "-o", str(png)]
flux = ["--diffusion-model", env.get("DIFF", ""), "--vae", env.get("VAE", ""), "--clip_l", env.get("CLIP", ""), "--t5xxl", env.get("T5GGUF", env.get("T5FP16", "")),
        "--cfg-scale", "1.0", "--sampling-method", "euler", "--seed", str(seed)]
if job.get("tile"): flux += ["--circular"]  # seamless: wraps left/right and top/bottom
def strength(default):
    try: return max(0.2, min(0.98, float(job.get("strength", default))))
    except Exception: return default
init = mask = None
if mode in ("edit", "expand", "upscale", "sketch"):
    init = b64file(job["init"], "init.png")
    if job.get("mask"): mask = b64file(job["mask"], "mask.png")
if mode == "edit":
    # magic edit: FLUX.2 klein repaints a zoomed crop around the brushed area; only masked pixels change
    import magic_edit
    if os.environ.get("FORGE_DRY"): print(json.dumps(["magic_edit", "klein", int(job.get("side", 512))])); sys.exit(0)
    t0 = time.time(); ok, log = magic_edit.run(os.environ["SD"], env, init, mask, prompt, seed, str(png), side=int(job.get("side", 512)))
    mins = (time.time() - t0) / 60
    r = subprocess.CompletedProcess([], 0 if ok else 1, log, "")
elif mode == "upscale":
    cmd = base + ["-M", "upscale", "--upscale-model", env.get("ESRGAN", ""), "--init-img", init]
elif mode == "expand":
    im = Image.open(init).convert("RGB"); ow, oh = im.size
    im.resize((W, H), Image.LANCZOS).save("init_s.png")
    Image.open(mask).convert("L").resize((W, H), Image.NEAREST).save("mask_s.png")
    if not prompt.strip(): prompt = " "  # words here get painted as text, so no default caption
    cmd = base + flux + ["-p", prompt, "--steps", "8", "-W", str(W), "-H", str(H), "--init-img", "init_s.png", "--mask", "mask_s.png", "--strength", "0.78" if mode == "expand" else "0.92"]  # expand: init edges are already filled on the phone, FLUX adds detail
elif mode == "sketch":
    # sketch -> art (also "vary" a take): img2img from the whole init, no mask. Lower strength = closer to the sketch.
    Image.open(init).convert("RGB").resize((W, H), Image.LANCZOS).save("init_s.png")
    cmd = base + flux + ["-p", prompt, "--steps", "8", "-W", str(W), "-H", str(H), "--init-img", "init_s.png", "--strength", f"{strength(0.7):.2f}"]
else:
    cmd = base + flux + ["-p", prompt, "--steps", "4", "-W", str(W), "-H", str(H)]
if os.environ.get("FORGE_DRY") and mode != "edit":  # tests: show the command, render nothing
    print(json.dumps(cmd)); sys.exit(0)
if mode != "edit":
    t0 = time.time(); r = subprocess.run(cmd, capture_output=True, text=True); mins = (time.time() - t0) / 60
if mode == "upscale" and (r.returncode != 0 or not png.exists()):
    # fallback so an upscale never comes back empty: Lanczos 4x + light sharpen
    from PIL import ImageFilter
    src = Image.open(init); f = int(job.get("scale", 4))
    src.resize((src.width * f, src.height * f), Image.LANCZOS).filter(ImageFilter.UnsharpMask(2, 80, 2)).save(png)
    (out / f"{k}.note.txt").write_text("ESRGAN failed, used Lanczos:\n" + (r.stdout + r.stderr)[-1500:])
if mode == "expand" and png.exists():
    # keep every untouched pixel exactly as it was; blend the new paint in with a soft edge
    from PIL import ImageFilter
    orig = Image.open(init).convert("RGBA"); ow, oh = orig.size
    gen = Image.open(png).convert("RGBA").resize((ow, oh), Image.LANCZOS)
    m = Image.open(mask).convert("L").resize((ow, oh), Image.NEAREST).filter(ImageFilter.GaussianBlur(max(1, min(ow, oh) // 200)))
    Image.composite(gen, orig, m).save(png)
if r.returncode != 0 or not png.exists():
    (out / f"{k}.error.txt").write_text((r.stdout + r.stderr)[-3000:])
else:
    key = job.get("key")
    if key and re.fullmatch(r"#[0-9A-Fa-f]{6}", key):
        im = keyfix(Image.open(png), key)
        im.save(png)
    raw = png.read_bytes()
    kind = "png"
    if len(raw) > 700_000:  # the GitHub connector reads files up to ~1 MB; ship a smaller copy for the app
        im0 = Image.open(png); has_a = im0.mode in ("RGBA", "LA") and im0.getextrema()[-1][0] < 255
        for q in (92, 85, 75, 65, 55):
            buf = io.BytesIO(); (im0 if has_a else im0.convert("RGB")).save(buf, "WEBP", quality=q); raw = buf.getvalue(); kind = "webp"
            if len(raw) < 690_000: break
    (out / f"{k}.b64").write_text(f"{kind}:" + base64.b64encode(raw).decode())
    (out / f"{k}.json").write_text(json.dumps({"minutes": round(mins, 1), "mode": mode, "w": Image.open(png).width, "h": Image.open(png).height, "seed": seed, "kind": kind}))
subprocess.run(["git", "add", str(out)])
subprocess.run(["git", "commit", "-q", "-m", f"[skip ci] forge: {jid} #{k} ({mins:.1f} min)"])
for i in range(6):
    if subprocess.run(["git", "pull", "-q", "--rebase", "origin", "main"]).returncode == 0 and subprocess.run(["git", "push", "-q", "origin", "HEAD:main"]).returncode == 0: break
    time.sleep(5 + i * 5)
