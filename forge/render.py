"""Render forge/prompts.json with stable-diffusion.cpp on CPU; commit each PNG + timing as it lands."""
import json, os, subprocess, time, pathlib
env = dict(l.strip().split("=", 1) for l in open("models.env") if "=" in l)
SD = os.environ["SD"]; os.makedirs("forge/out", exist_ok=True)
log = open("forge/out/log.txt", "a")
def say(*a):
    s = " ".join(str(x) for x in a); print(s, flush=True); log.write(s + "\n"); log.flush()
say("nproc", os.cpu_count(), "models", env)
configs = []
if "T5GGUF" in env: configs.append(("t5gguf", ["--t5xxl", env["T5GGUF"]]))
configs.append(("t5fp16_q8", ["--t5xxl", env["T5FP16"], "--type", "q8_0"]))
configs.append(("t5fp16", ["--t5xxl", env["T5FP16"]]))
good = None
for p in json.load(open("forge/prompts.json")):
    tries = [good] if good else configs
    for name, extra in tries:
        out = f"forge/out/{p['id']}.png"
        cmd = [SD, "--diffusion-model", env["DIFF"], "--vae", env["VAE"], "--clip_l", env["CLIP"], *extra,
               "-p", p["prompt"], "--cfg-scale", "1.0", "--sampling-method", "euler", "--steps", "4",
               "-W", str(p["w"]), "-H", str(p["h"]), "--seed", str(p["seed"]), "-t", str(os.cpu_count()), "-o", out]
        t0 = time.time(); r = subprocess.run(cmd, capture_output=True, text=True); dt = time.time() - t0
        tail = (r.stdout + r.stderr)[-1500:]
        if r.returncode == 0 and pathlib.Path(out).exists():
            good = (name, extra); say(f"OK {p['id']} {p['w']}x{p['h']} {dt/60:.1f} min config={name}")
            subprocess.run(["git", "add", "forge/out"]); subprocess.run(["git", "commit", "-q", "-m", f"[skip ci] forge: {p['id']} ({dt/60:.1f} min)"])
            for i in range(3):
                if subprocess.run(["git", "pull", "-q", "--rebase"]).returncode == 0 and subprocess.run(["git", "push", "-q"]).returncode == 0: break
                time.sleep(5)
            break
        say(f"FAIL {p['id']} config={name} rc={r.returncode} {dt:.0f}s\n{tail}")
subprocess.run(["git", "add", "forge/out"]); subprocess.run(["git", "commit", "-q", "-m", "[skip ci] forge: log"]); subprocess.run(["git", "push", "-q"])
