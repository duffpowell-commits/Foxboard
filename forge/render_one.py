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
cmd = [os.environ["SD"], "--diffusion-model", env["DIFF"], "--vae", env["VAE"], "--clip_l", env["CLIP"], "--t5xxl", env["T5GGUF"],
       "-p", prompt, "--cfg-scale", "1.0", "--sampling-method", "euler", "--steps", "4",
       "-W", str(W), "-H", str(H), "--seed", str(seed), "-t", str(os.cpu_count()), "-o", str(png)]
t0 = time.time(); r = subprocess.run(cmd, capture_output=True, text=True); mins = (time.time() - t0) / 60
if r.returncode != 0 or not png.exists():
    (out / f"{k}.error.txt").write_text((r.stdout + r.stderr)[-3000:])
else:
    key = job.get("key")
    if key and re.fullmatch(r"#[0-9A-Fa-f]{6}", key):
        im = keyfix(Image.open(png), key)
        im.save(png)
    raw = png.read_bytes()
    if len(raw) > 700_000:  # the GitHub connector reads files up to ~1 MB; ship a smaller copy for the app
        buf = io.BytesIO(); Image.open(png).convert("RGB").save(buf, "WEBP", quality=92); raw = buf.getvalue(); kind = "webp"
    else: kind = "png"
    (out / f"{k}.b64").write_text(f"{kind}:" + base64.b64encode(raw).decode())
    (out / f"{k}.json").write_text(json.dumps({"minutes": round(mins, 1), "w": W, "h": H, "seed": seed, "kind": kind}))
subprocess.run(["git", "add", str(out)])
subprocess.run(["git", "commit", "-q", "-m", f"[skip ci] forge: {jid} #{k} ({mins:.1f} min)"])
for i in range(6):
    if subprocess.run(["git", "pull", "-q", "--rebase", "origin", "main"]).returncode == 0 and subprocess.run(["git", "push", "-q", "origin", "HEAD:main"]).returncode == 0: break
    time.sleep(5 + i * 5)
