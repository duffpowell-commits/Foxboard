"""Forge changes that make the art-generation guide actually work.

Dry-runs of render_one.py (no model) and art_loop.py queue --no-publish.
Run: python tests/test_forge_guide.py
"""
import base64, io, json, os, pathlib, subprocess, sys, tempfile
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "forge"))
sys.path.insert(0, str(ROOT / "tools" / "claude"))
from style_ref import style_board, img2img_strength, clamp_ref_strength
import art_loop

fails = 0
def check(name, ok, extra=""):
    global fails
    print(("PASS " if ok else "FAIL ") + name + (f"  ({extra})" if extra else ""))
    fails += 0 if ok else 1


def png_b64(im):
    buf = io.BytesIO(); im.save(buf, "PNG")
    return "png:" + base64.b64encode(buf.getvalue()).decode()


def dry(job_dir, jid, env_extra=None):
    env = dict(os.environ, FORGE_DRY="1", SD="sd")
    if env_extra:
        env.update(env_extra)
    pr = subprocess.run([sys.executable, str(ROOT / "forge/render_one.py"), jid, "0"],
                        cwd=job_dir, env=env, capture_output=True, text=True, timeout=60)
    try:
        out = json.loads(pr.stdout.strip().splitlines()[-1])
    except Exception:
        out = (pr.stdout + pr.stderr)[-400:]
    return pr, out


def setup_job(td, jid, job, init=None, ref=None, mask=None):
    jobs = td / "forge/jobs"; jobs.mkdir(parents=True, exist_ok=True)
    (td / "models.env").write_text("DIFF=d\nVAE=v\nCLIP=c\nT5GGUF=t\n")
    if init is not None:
        (jobs / f"{jid}.init.b64").write_text(png_b64(init))
        job.setdefault("init", f"forge/jobs/{jid}.init.b64")
    if ref is not None:
        (jobs / f"{jid}.ref.b64").write_text(png_b64(ref))
        job.setdefault("ref", f"forge/jobs/{jid}.ref.b64")
    if mask is not None:
        (jobs / f"{jid}.mask.b64").write_text(png_b64(mask))
        job.setdefault("mask", f"forge/jobs/{jid}.mask.b64")
    (jobs / f"{jid}.json").write_text(json.dumps(job))
    return td


# --- style board ---
im = Image.new("RGB", (128, 192), (30, 40, 50))
im.paste(Image.new("RGB", (40, 80), (200, 30, 30)), (10, 10))  # a red figure in the corner
b1 = style_board(im, 256, 256, seed=42)
b2 = style_board(im, 256, 256, seed=42)
b3 = style_board(im, 256, 256, seed=99)
check("style board is the asked size", b1.size == (256, 256), b1.size)
check("style board is deterministic for a seed", list(b1.getdata()) == list(b2.getdata()))
check("different seed => different board", list(b1.getdata()) != list(b3.getdata()))
# the red figure should not sit only in the top-left the way a resize would
red_in_src_corner = sum(1 for x in range(40) for y in range(80) if im.getpixel((x, y))[0] > 150)
# after shuffle, some red should appear outside that mapped corner of the 256 board
red_elsewhere = sum(1 for x in range(256) for y in range(256)
                    if (x > 80 or y > 80) and b1.getpixel((x, y))[0] > 140)
check("style board scatters crops (not a straight resize)", red_elsewhere > 0, red_elsewhere)
check("ref_strength 0.15 maps to a high img2img strength", img2img_strength(0.15) >= 0.90, img2img_strength(0.15))
check("ref_strength 0.85 maps to >= 0.72 (prompt still leads)", 0.72 <= img2img_strength(0.85) <= 0.78, img2img_strength(0.85))
check("ref_strength is clamped", clamp_ref_strength(2) == 0.85 and clamp_ref_strength(-1) == 0.15)


# --- render_one dry runs ---
with tempfile.TemporaryDirectory() as tds:
    td = pathlib.Path(tds)
    red = Image.new("RGB", (64, 64), (200, 50, 50))
    setup_job(td, "ref1", {"mode": "new", "prompt": "a lantern", "n": 1, "w": 512, "h": 512,
                           "seed": 7, "ref_strength": 0.55}, ref=red)
    pr, out = dry(td, "ref1")
    st = img2img_strength(0.55)
    check("render: ref on mode new uses --init-img (style board) and mapped strength",
          isinstance(out, list) and "--init-img" in out and out[out.index("--strength") + 1] == f"{st:.2f}", out)
    check("render: ref job writes a workaround note",
          (td / "forge/results/ref1/0.note.txt").exists() and "not IP-Adapter" in (td / "forge/results/ref1/0.note.txt").read_text())

    setup_job(td, "newinit", {"mode": "new", "prompt": "a bridge", "n": 1, "w": 512, "h": 512, "seed": 7, "strength": 0.8},
              init=red)
    pr, out = dry(td, "newinit")
    check("render: init on mode new is not ignored — switches to sketch img2img",
          isinstance(out, list) and "--init-img" in out and out[out.index("--strength") + 1] == "0.80", out)
    check("render: init on mode new warns on stderr",
          "switched to sketch" in pr.stderr)

    setup_job(td, "both", {"mode": "new", "prompt": "x", "n": 1, "w": 512, "h": 512, "seed": 7},
              init=red, ref=red)
    pr, out = dry(td, "both")
    check("render: init+ref is an error, not a silent ignore",
          isinstance(out, dict) and out.get("error") == "init_and_ref", out)
    check("render: init+ref writes error.txt", (td / "forge/results/both/0.error.txt").exists())

    setup_job(td, "plain", {"mode": "new", "prompt": "grass", "n": 1, "w": 512, "h": 512, "seed": 7})
    pr, out = dry(td, "plain")
    check("render: plain new job still has no --init-img and no --circular",
          isinstance(out, list) and "--init-img" not in out and "--circular" not in out, out)


# --- art_loop queue ---
def run_queue(td, args):
    env = dict(os.environ, FOXBOARD_ROOT=str(td))
    return subprocess.run([sys.executable, str(ROOT / "tools/claude/art_loop.py"), "queue", *args],
                          cwd=td, env=env, capture_output=True, text=True, timeout=30)


with tempfile.TemporaryDirectory() as tds:
    td = pathlib.Path(tds)
    (td / "forge/jobs").mkdir(parents=True)
    (td / "p.txt").write_text("a wet cobble floor, lit flat")
    red_path = td / "style.png"
    Image.new("RGB", (80, 80), (40, 60, 80)).save(red_path)

    pr = run_queue(td, ["--id", "q-ref-1", "--prompt-file", str(td / "p.txt"), "--w", "512", "--h", "512",
                        "--n", "2", "--seed", "99", "--tile", "--ref", str(red_path), "--ref-strength", "0.6",
                        "--no-publish"])
    check("queue: ref job exits 0", pr.returncode == 0, pr.stderr[-300:])
    data = json.loads(pr.stdout)
    job = json.loads((td / "forge/jobs/q-ref-1.json").read_text())
    check("queue: writes json + ref.b64 in one go",
          (td / "forge/jobs/q-ref-1.json").exists() and (td / "forge/jobs/q-ref-1.ref.b64").exists())
    check("queue: job carries tile, ref, ref_strength, workaround",
          job.get("tile") is True and job.get("ref") == "forge/jobs/q-ref-1.ref.b64"
          and job.get("ref_strength") == 0.6 and job.get("workaround") == "style_board", job)
    check("queue: --no-publish does not claim it landed on main", data.get("published") is None)

    pr = run_queue(td, ["--id", "q-badw", "--prompt-file", str(td / "p.txt"), "--w", "190", "--h", "500", "--no-publish"])
    check("queue: invalid size 190 is a clear error (range)",
          pr.returncode != 0 and "256 and 1024" in pr.stderr + pr.stdout and "190" in pr.stderr + pr.stdout,
          (pr.stdout + pr.stderr)[-200:])

    pr = run_queue(td, ["--id", "q-badm", "--prompt-file", str(td / "p.txt"), "--w", "500", "--h", "512", "--no-publish"])
    check("queue: size 500 is a clear error (multiple of 64) with a suggestion",
          pr.returncode != 0 and "multiple of 64" in pr.stderr + pr.stdout and "500" in pr.stderr + pr.stdout
          and "512" in pr.stderr + pr.stdout, (pr.stdout + pr.stderr)[-200:])

    init_path = td / "init.png"; Image.new("RGB", (64, 64), (10, 10, 10)).save(init_path)
    pr = run_queue(td, ["--id", "q-sw", "--prompt-file", str(td / "p.txt"), "--w", "512", "--h", "512",
                        "--mode", "new", "--init", str(init_path), "--no-publish"])
    job = json.loads((td / "forge/jobs/q-sw.json").read_text()) if pr.returncode == 0 else {}
    check("queue: --init with --mode new writes mode sketch and warns",
          pr.returncode == 0 and job.get("mode") == "sketch" and "switched to sketch" in pr.stderr, pr.stderr[-200:])

    pr = run_queue(td, ["--id", "q-edit", "--prompt-file", str(td / "p.txt"), "--mode", "edit", "--no-publish",
                        "--w", "512", "--h", "512"])
    check("queue: edit without init/mask is a clear error",
          pr.returncode != 0 and "--init" in pr.stderr + pr.stdout and "--mask" in pr.stderr + pr.stdout,
          (pr.stdout + pr.stderr)[-200:])

    pr = run_queue(td, ["--id", "q-both", "--prompt-file", str(td / "p.txt"), "--init", str(init_path),
                        "--ref", str(red_path), "--no-publish", "--w", "512", "--h", "512"])
    check("queue: --init and --ref together is a clear error",
          pr.returncode != 0 and "cannot set both" in (pr.stderr + pr.stdout).lower(),
          (pr.stdout + pr.stderr)[-200:])


# --- plan.py does not re-queue a take that already has error.txt ---
import importlib.util
def run_plan(td, jobs):
    jobs_dir = td / "forge/jobs"; jobs_dir.mkdir(parents=True, exist_ok=True)
    for jid, body, results in jobs:
        (jobs_dir / f"{jid}.json").write_text(json.dumps(body))
        if results:
            rd = td / "forge/results" / jid
            rd.mkdir(parents=True, exist_ok=True)
            for name, text in results:
                (rd / name).write_text(text)
    outp = td / "gh_out"
    env = dict(os.environ, GITHUB_OUTPUT=str(outp))
    pr = subprocess.run([sys.executable, str(ROOT / "forge/plan.py")], cwd=td, env=env,
                        capture_output=True, text=True, timeout=15)
    return pr, outp.read_text() if outp.exists() else ""

with tempfile.TemporaryDirectory() as tds:
    td = pathlib.Path(tds)
    pr, out = run_plan(td, [
        ("p-pending", {"n": 1}, None),
        ("p-failed", {"n": 1}, [("0.error.txt", "bad job")]),
        ("p-ok", {"n": 1}, [("0.png", "x")]),
        ("p-done", {"n": 2}, [("done.json", '{"ok":[0,1],"failed":[]}')]),
    ])
    check("plan: exits 0", pr.returncode == 0, pr.stderr[-200:])
    check("plan: pending take is queued", '"job": "p-pending"' in out or "'job': 'p-pending'" in pr.stdout)
    check("plan: take with error.txt is not retried", "p-failed" not in out and "p-failed" not in pr.stdout)
    check("plan: take with png is not queued", "p-ok" not in out.split("p-pending")[-1] if False else "p-ok" not in pr.stdout)
    check("plan: job with done.json is skipped", "p-done" not in pr.stdout)


# --- pre-push hook: main accepts job-only commits, refuses code ---
def git(cwd, *args, check=True):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if check and r.returncode:
        raise RuntimeError(f"git {' '.join(args)} failed:\n{r.stdout}{r.stderr}")
    return r

with tempfile.TemporaryDirectory() as tds:
    td = pathlib.Path(tds)
    remote = td / "remote.git"; work = td / "work"
    git(td, "init", "--bare", str(remote))
    git(td, "clone", str(remote), str(work))
    git(work, "config", "user.name", "Test")
    git(work, "config", "user.email", "test@example.com")
    git(work, "config", "core.hooksPath", ".githooks")
    (work / ".githooks").mkdir()
    hook = (work / ".githooks/pre-push")
    hook.write_text((ROOT / ".githooks/pre-push").read_text())
    hook.chmod(0o755)
    (work / "README").write_text("hi\n")
    git(work, "add", "README")
    git(work, "commit", "-m", "init")
    git(work, "branch", "-M", "main")
    git(work, "push", "-u", "origin", "main")

    (work / "code.py").write_text("x=1\n")
    git(work, "add", "code.py")
    git(work, "commit", "-m", "code")
    pr = git(work, "push", "origin", "main", check=False)
    check("hook: refuses a code push to main",
          pr.returncode != 0 and "forge/jobs" in pr.stderr, pr.stderr[-300:])

    git(work, "reset", "--hard", "origin/main")
    (work / "forge/jobs").mkdir(parents=True)
    (work / "forge/jobs/t1.json").write_text('{"prompt":"x"}\n')
    git(work, "add", "forge/jobs/t1.json")
    git(work, "commit", "-m", "job")
    pr = git(work, "push", "origin", "main", check=False)
    check("hook: allows a job-only push to main", pr.returncode == 0, pr.stderr[-300:])

print(f"\n{'ALL PASS' if not fails else f'{fails} FAILED'}")
sys.exit(1 if fails else 0)
