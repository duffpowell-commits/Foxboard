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
ref_rel = job.get("ref") or job.get("style")
init_rel = job.get("init")
notes = []

# init on mode new used to be silently ignored (only sketch/edit/expand/upscale loaded it).
# Switch to sketch and say so; never drop the picture. ref is a different input (style board).
if init_rel and mode == "new" and not ref_rel:
    notes.append("init was set on mode new; switched to sketch so the picture is actually used")
    mode = "sketch"
    print("forge: " + notes[-1], file=sys.stderr)
def commit_take(label):
    # Why: plan.py / finish.py treat a committed error.txt as a finished (failed) take.
    # Leaving the file uncommitted made a bad job sit pending and retry on the next
    # forge/jobs push.
    if os.environ.get("FORGE_NO_GIT"):
        return
    subprocess.run(["git", "add", str(out)])
    subprocess.run(["git", "commit", "-q", "-m", f"[skip ci] forge: {jid} #{k} ({label})"])
    for i in range(6):
        if subprocess.run(["git", "pull", "-q", "--rebase", "origin", "main"]).returncode == 0 and subprocess.run(["git", "push", "-q", "origin", "HEAD:main"]).returncode == 0: break
        time.sleep(5 + i * 5)

def fail_take(code, msg):
    (out / f"{k}.error.txt").write_text(msg)
    print("forge: " + msg, file=sys.stderr)
    if os.environ.get("FORGE_DRY"):
        print(json.dumps({"error": code})); sys.exit(0)
    commit_take("error")
    sys.exit(0)

if init_rel and ref_rel:
    fail_take("init_and_ref", "a job cannot set both init (layout / start-from) and ref (style board) — FLUX.1-schnell has no separate style-reference encoder. Use ref alone for a new subject, or init + mode sketch to start from a picture.")
if ref_rel and mode not in ("new",):
    fail_take("ref_bad_mode", f"ref is only valid on mode new (got {mode!r}). sketch/edit use init, not ref.")

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
from engine import uses_klein
KLEIN = uses_klein(job)  # same rule decides which models get_models.py downloads
if KLEIN:
    # magic edit: FLUX.2 klein repaints a zoomed crop around the brushed area; only masked pixels change
    import magic_edit
    if os.environ.get("FORGE_DRY"): print(json.dumps(["magic_edit", "klein", int(job.get("side", 512))])); sys.exit(0)
    if mode == "expand" and not prompt.strip(): prompt = "Continue the scene into the empty border areas so it reads as one picture"
    t0 = time.time(); ok, log = magic_edit.run(os.environ["SD"], env, init, mask, prompt, seed, str(png), side=int(job.get("side", 512)))
    mins = (time.time() - t0) / 60
    r = subprocess.CompletedProcess([], 0 if ok else 1, log, "")
elif mode == "upscale":
    cmd = base + ["-M", "upscale", "--upscale-model", env.get("ESRGAN", ""), "--init-img", init]
elif mode in ("expand", "edit"):
    # expand, and edits with engine "flux" (New background: the mask is the whole background, and klein keeps the
    # original alpha, so the new scene came back transparent - Nov 19 real-art test)
    im = Image.open(init).convert("RGB"); ow, oh = im.size
    im.resize((W, H), Image.LANCZOS).save("init_s.png")
    Image.open(mask).convert("L").resize((W, H), Image.NEAREST).save("mask_s.png")
    if not prompt.strip(): prompt = " "  # words here get painted as text, so no default caption
    cmd = base + flux + ["-p", prompt, "--steps", "8", "-W", str(W), "-H", str(H), "--init-img", "init_s.png", "--mask", "mask_s.png", "--strength", f"{strength(0.9 if mode == 'expand' else 0.92):.2f}"]  # expand: 0.78 left glassy panels on the new edges (Nov 19); 0.9 repaints them
elif mode == "sketch":
    # sketch -> art (also "vary" a take): img2img from the whole init, no mask. Lower strength = closer to the sketch.
    Image.open(init).convert("RGB").resize((W, H), Image.LANCZOS).save("init_s.png")
    cmd = base + flux + ["-p", prompt, "--steps", "8", "-W", str(W), "-H", str(H), "--init-img", "init_s.png", "--strength", f"{strength(0.7):.2f}"]
elif ref_rel:
    # Style-board workaround (not IP-Adapter — see style_ref.py). New subject, style bleed from ref.
    from style_ref import load_b64, style_board, img2img_strength, clamp_ref_strength
    rs = clamp_ref_strength(job.get("ref_strength"))
    st = strength(img2img_strength(rs)) if job.get("strength") is not None else img2img_strength(rs)
    board = style_board(load_b64(ref_rel), W, H, seed)
    board.save("init_s.png")
    notes.append(f"style board from {ref_rel} (ref_strength={rs}, img2img strength={st:.2f}); not IP-Adapter")
    cmd = base + flux + ["-p", prompt, "--steps", "8", "-W", str(W), "-H", str(H), "--init-img", "init_s.png", "--strength", f"{st:.2f}"]
else:
    cmd = base + flux + ["-p", prompt, "--steps", "4", "-W", str(W), "-H", str(H)]
if notes:
    (out / f"{k}.note.txt").write_text("\n".join(notes) + "\n")
if os.environ.get("FORGE_DRY") and not KLEIN:  # tests: show the command, render nothing
    print(json.dumps(cmd)); sys.exit(0)
if not KLEIN:  # Nov 19: this said mode != "edit", so FLUX-engine edits never ran (NameError on r)
    # one hung render must not hold the whole queue (Nov 19: a stuck take blocked every session's jobs for 90 min):
    # cap at 3x the expected time (min 25 min); a timeout becomes a failed take, the job still finishes
    base_min = {(768, 768): 15, (512, 512): 7, (1024, 1024): 27, (576, 1024): 16, (1024, 576): 16}.get((W, H), 15) * (1.4 if mode == "sketch" or ref_rel else 1)
    cap = float(os.environ.get("FORGE_TIMEOUT_MIN") or max(25, 3 * base_min))
    t0 = time.time()
    try: r = subprocess.run(cmd, capture_output=True, text=True, timeout=cap * 60)
    except subprocess.TimeoutExpired as te:
        r = subprocess.CompletedProcess(cmd, 124, "", f"timed out after {cap:.1f} min (render cap)\n" + str(te.stderr or "")[-1000:])
        if png.exists(): png.unlink()
    mins = (time.time() - t0) / 60
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
    meta = {"minutes": round(mins, 1), "mode": mode, "w": Image.open(png).width, "h": Image.open(png).height, "seed": seed, "kind": kind}
    if ref_rel:
        meta["ref"] = True
        meta["ref_strength"] = job.get("ref_strength")
        meta["workaround"] = "style_board"
    (out / f"{k}.json").write_text(json.dumps(meta))
if os.environ.get("FORGE_NO_GIT"): sys.exit(0)  # tests: render locally, skip the commit/push loop
commit_take(f"{mins:.1f} min")
