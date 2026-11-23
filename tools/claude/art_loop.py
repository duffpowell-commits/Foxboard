#!/usr/bin/env python3
"""Art loop helper: queue Forge jobs, check them, score the takes, build a contact sheet.

Used by the art-loop skill (render -> judge -> reroll -> deliver). Run from a Foxboard clone.

  python3 tools/claude/art_loop.py queue  --id lm-x-20261119 --prompt-file p.txt [--n 2 --w 512 --h 512 --seed N --key '#00FF00']
       [--mode new|sketch|edit --init a.png --mask m.png --ref style.png --ref-strength 0.55 --strength 0.7 --tile --send-to lethemoor]
       Sizes must be 256-1024 and a multiple of 64. Job files are committed and published to Foxboard main (job-only).
       Pass --no-publish to write the files without git (tests / a dry run).
  python3 tools/claude/art_loop.py status lm-x-20261119 [more ids]
  python3 tools/claude/art_loop.py score  lm-x-20261119 --game lethemoor --kind sprite|texture|scene|hud [--aspect 0.37]
  python3 tools/claude/art_loop.py cut    lm-x-20261119/1 out.png [--height 640] [--key '#00FF00']

score prints JSON (one entry per take, plus "best") and writes forge/out/<id>_sheet.png.
The numbers are a pre-filter only; Claude still looks at the sheet before picking.
"""
import argparse, json, os, re, subprocess, sys, time, random
from PIL import Image, ImageDraw

def repo_root():
    return os.path.abspath(os.environ.get("FOXBOARD_ROOT") or os.path.join(os.path.dirname(__file__), "..", ".."))


ROOT = repo_root()


def dirs():
    root = repo_root()
    return root, *(os.path.join(root, "forge", d) for d in ("jobs", "results", "out"))


JOBS, RESULTS, OUT = dirs()[1:]
ID_RE = re.compile(r"^[A-Za-z0-9_-]{4,64}$")

# Per-game locks. Palette + key colour mirror DEFAULT_BIBLE in index.html; keep them in step.
GAMES = {
    "lethemoor": {
        "key": "#00FF00",
        "palette": ['#05070c', '#0b111b', '#141d2b', '#202d40', '#33445a', '#4d6078', '#2a170a', '#5a3414', '#8f561f',
                    '#c98a2e', '#f2c25a', '#ffe9a8', '#4a0710', '#8a1020', '#c81e2e', '#6f6656', '#a99c84', '#d9cdb4'],
    },
}


def sh(*cmd, check=True, cwd=None):
    r = subprocess.run(cmd, cwd=cwd or repo_root(), capture_output=True, text=True)
    if check and r.returncode:
        sys.exit(f"failed: {' '.join(cmd)}\n{r.stdout}{r.stderr}")
    return r.stdout.strip()


def hexrgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


# ---------- queue ----------

def encode_image(src):
    """Read a png/jpg (or an existing png:/jpg: b64 text file) and return 'png:' + base64."""
    import base64, io
    head = open(src, "rb").read(8)
    # already a Forge b64 text file
    if head.lstrip()[:4] in (b"png:", b"jpg:") or head.lstrip().startswith(b"jpeg:"):
        return open(src, "r").read().strip()
    im = Image.open(src).convert("RGBA")
    buf = io.BytesIO(); im.save(buf, "PNG")
    return "png:" + base64.b64encode(buf.getvalue()).decode()


def check_size(name, v):
    if v < 256 or v > 1024:
        sys.exit(f"{name} must be between 256 and 1024 inclusive (got {v})")
    if v % 64:
        rec = max(256, min(1024, round(v / 64) * 64))
        sys.exit(f"{name} must be a multiple of 64 (got {v}). Closest valid size: {rec}")


def check_strength(name, v, lo, hi):
    try:
        f = float(v)
    except (TypeError, ValueError):
        sys.exit(f"{name} must be a number between {lo} and {hi} (got {v!r})")
    if not (lo <= f <= hi):
        sys.exit(f"{name} must be between {lo} and {hi} (got {v})")
    return f


def write_job_files(a):
    """Build the job JSON and any init/mask/ref b64 files. Returns (job, written paths)."""
    root, jobs, results, _out = dirs()
    if not ID_RE.match(a.id):
        sys.exit("bad id: 4-64 chars of A-Z a-z 0-9 _ -")
    prompt = open(a.prompt_file).read().strip()
    if len(prompt) > 1500:
        sys.exit(f"prompt is {len(prompt)} chars, max 1500")
    if a.n < 1 or a.n > 4:
        sys.exit(f"n must be between 1 and 4 (got {a.n})")
    check_size("w", a.w)
    check_size("h", a.h)
    if os.path.exists(os.path.join(jobs, a.id + ".json")) or os.path.isdir(os.path.join(results, a.id)):
        sys.exit(f"{a.id} already used: pick a new id (e.g. add -b, -c)")
    mode = (a.mode or "new").strip().lower()
    if mode not in ("new", "sketch", "edit", "expand", "upscale"):
        sys.exit("mode must be new, sketch, edit, expand or upscale")
    key = None if a.key in (None, "", "null", "none") else a.key
    job = {"prompt": prompt, "n": a.n, "w": a.w, "h": a.h, "mode": mode,
           "seed": a.seed if a.seed is not None else random.randint(1, 2**31 - 1),
           "key": key, "at": int(time.time() * 1000)}
    warnings = []
    if a.init and mode == "new" and not a.ref:
        # Why: render_one used to ignore init on mode new. Don't write a lying job.
        job["mode"] = "sketch"
        mode = "sketch"
        warnings.append("init was set on mode new; switched to sketch so the picture is actually used")
    if a.tile:
        if mode in ("edit",) and getattr(a, "engine", None) != "flux":
            warnings.append("tile only affects the FLUX path (new/sketch/flux edit), not klein edits")
        job["tile"] = True
    if getattr(a, "send_to", None):
        job["game"] = a.send_to  # forge/send_game.py drops each finished take into that game's grok_art inbox
        job["name"] = a.id
    if a.strength is not None:
        job["strength"] = check_strength("strength", a.strength, 0.3, 0.95)
    if a.init and a.ref:
        sys.exit("cannot set both --init (start from this picture) and --ref (style board). FLUX.1-schnell has no separate style-reference encoder.")
    if a.ref and mode != "new":
        sys.exit("--ref is only valid with --mode new")
    os.makedirs(jobs, exist_ok=True)
    written = []

    def add_b64(flag, field, ext):
        src = getattr(a, flag)
        if not src:
            return
        if not os.path.exists(src):
            sys.exit(f"--{flag} file not found: {src}")
        rel = f"forge/jobs/{a.id}.{ext}.b64"
        path = os.path.join(jobs, f"{a.id}.{ext}.b64")
        with open(path, "w") as f:
            f.write(encode_image(src))
        job[field] = rel
        written.append(rel)

    add_b64("init", "init", "init")
    add_b64("mask", "mask", "mask")
    add_b64("ref", "ref", "ref")
    if a.ref:
        rs = 0.55 if a.ref_strength is None else check_strength("ref-strength", a.ref_strength, 0.15, 0.85)
        job["ref_strength"] = rs
        job["workaround"] = "style_board"
    # Required pairs
    if mode in ("sketch", "upscale") and "init" not in job:
        sys.exit(f"--mode {mode} needs --init")
    if mode in ("edit", "expand"):
        if "init" not in job or "mask" not in job:
            sys.exit(f"--mode {mode} needs both --init and --mask (mask: white = change, black = keep). w/h and tile do not apply to klein edits; those use --side (default 512).")
    rel_json = f"forge/jobs/{a.id}.json"
    with open(os.path.join(jobs, a.id + ".json"), "w") as f:
        json.dump(job, f, indent=1)
        f.write("\n")
    written.append(rel_json)
    return job, written, warnings


def publish_jobs_to_main(written, message):
    """Commit only forge/jobs/** onto origin/main and push, even from a feature branch.

    Why: forge.yml renders only on a push to main under forge/jobs/**. Code still
    goes through PRs. This builds a commit whose parent is origin/main and whose
    tree is origin/main plus the new job files, then pushes that SHA to main so
    a feature branch cannot sneak through.
    """
    root = repo_root()
    sh("git", "fetch", "-q", "origin", "main", cwd=root)
    # Stage only the job files in a temporary index based on origin/main.
    import tempfile
    index = tempfile.mktemp(prefix="forge-idx-")
    env = os.environ.copy()
    env["GIT_INDEX_FILE"] = index
    env["GIT_WORK_TREE"] = root
    def g(*args, check=True):
        r = subprocess.run(["git", *args], cwd=root, env=env, capture_output=True, text=True)
        if check and r.returncode:
            sys.exit(f"failed: git {' '.join(args)}\n{r.stdout}{r.stderr}")
        return r
    g("read-tree", "origin/main")
    for rel in written:
        g("add", "-f", "--", rel)
    tree = g("write-tree").stdout.strip()
    parent = sh("git", "rev-parse", "origin/main", cwd=root)
    commit = subprocess.run(
        ["git", "commit-tree", tree, "-p", parent, "-m", message],
        cwd=root, capture_output=True, text=True, env=env,
    )
    if commit.returncode:
        sys.exit(f"failed: commit-tree\n{commit.stdout}{commit.stderr}")
    sha = commit.stdout.strip()
    os.remove(index)
    for _ in range(3):
        r = subprocess.run(["git", "push", "-q", "origin", f"{sha}:main"], cwd=root)
        if r.returncode == 0:
            return sha
        sh("git", "fetch", "-q", "origin", "main", cwd=root)
        # rebase the job commit onto the new main if someone else pushed
        parent = sh("git", "rev-parse", "origin/main", cwd=root)
        # rebuild is safer than rebase for a jobs-only tree; retry from new main
        env["GIT_INDEX_FILE"] = index = tempfile.mktemp(prefix="forge-idx-")
        env["GIT_WORK_TREE"] = root
        g("read-tree", "origin/main")
        for rel in written:
            g("add", "-f", "--", rel)
        tree = g("write-tree").stdout.strip()
        commit = subprocess.run(
            ["git", "commit-tree", tree, "-p", parent, "-m", message],
            cwd=root, capture_output=True, text=True, env=env,
        )
        sha = commit.stdout.strip()
        os.remove(index)
    sys.exit("push to origin main failed 3 times")


def cmd_queue(a):
    job, written, warnings = write_job_files(a)
    for w in warnings:
        print("warning: " + w, file=sys.stderr)
    sha = None
    if not a.no_publish:
        msg = f"Forge: {a.id}" + (f"\n\n{a.trailer}" if a.trailer else "")
        sha = publish_jobs_to_main(written, msg)
        # also add the files on the current branch so the working tree stays consistent
        root = repo_root()
        subprocess.run(["git", "update-index", "--add", "--", *written], cwd=root, capture_output=True)
    mins = {512: 5, 576: 8, 640: 9, 704: 12, 768: 15, 1024: 27}.get(max(a.w, a.h), 15)
    print(json.dumps({"queued": a.id, "seed": job["seed"], "mode": job.get("mode", "new"),
                      "files": written, "warnings": warnings, "published": sha,
                      "on_main": bool(sha),
                      "check_after_min": mins + 3}))


# ---------- status ----------
def cmd_status(a):
    sh("git", "pull", "--rebase", "-q", check=False)
    out = {}
    for i in a.ids:
        d = os.path.join(RESULTS, i)
        done = os.path.join(d, "done.json")
        if os.path.exists(done):
            out[i] = {"state": "done", **json.load(open(done))}
        elif os.path.exists(os.path.join(JOBS, i + ".json")):
            pngs = sorted(f for f in os.listdir(d) if f.endswith(".png")) if os.path.isdir(d) else []
            out[i] = {"state": "rendering", "partial": pngs}
        else:
            out[i] = {"state": "unknown id"}
    print(json.dumps(out, indent=1))


# ---------- score ----------
def subject_mask(im, key):
    """True where the pixel is subject (not key background)."""
    px = im.load(); w, h = im.size; kc = hexrgb(key)
    return [[sum((px[x, y][c] - kc[c]) ** 2 for c in range(3)) > 40 * 40 for x in range(w)] for y in range(h)]


def score_one(path, game, kind, aspect, jobkey=None):
    im = Image.open(path).convert("RGB")
    w, h = im.size
    small = im.resize((max(1, w // 4), max(1, h // 4)), Image.NEAREST)
    sw, sh_ = small.size; px = small.load()
    pal = [hexrgb(c) for c in GAMES[game]["palette"]]
    key = (jobkey or GAMES[game]["key"]) if kind in ("sprite", "hud") else None
    mask = subject_mask(small, key) if key else [[True] * sw for _ in range(sh_)]
    pts = [(x, y) for y in range(sh_) for x in range(sw) if mask[y][x]]
    flags, s = [], {}
    if not pts:
        return {"file": os.path.basename(path), "score": 0, "flags": ["empty: no subject"]}
    # palette fit: mean distance to the nearest locked colour
    dist = [min(sum((px[p][c] - q[c]) ** 2 for c in range(3)) ** 0.5 for q in pal) for p in pts]
    s["palette_fit"] = round(1 - min(1, (sum(dist) / len(dist)) / 120), 2)
    if s["palette_fit"] < 0.55:
        flags.append("off-palette")
    # brightness: the lantern lights it in game, art should be lit flat and mostly dark
    lum = [0.299 * px[p][0] + 0.587 * px[p][1] + 0.114 * px[p][2] for p in pts]
    s["mean_lum"] = round(sum(lum) / len(lum))
    hot = sum(1 for v in lum if v > 235) / len(lum)
    if hot > 0.04 and kind != "hud":
        flags.append(f"baked glow ({hot:.0%} near-white)")
    if key:
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        cov = len(pts) / (sw * sh_)
        s["coverage"] = round(cov, 2)
        if cov < 0.06:
            flags.append("subject tiny")
        if y0 <= 0:
            flags.append("head/top cut off")
        if x0 <= 0 or x1 >= sw - 1:
            flags.append("side cut off")
        if kind == "sprite" and y1 < sh_ - 3 - sh_ // 6:
            flags.append("floating: feet far from bottom")
        # floor shadow: a dark band at the feet wider than the legs just above it
        def span(y):
            row = [x for x in range(sw) if mask[y][x]]
            return (row[0], row[-1]) if row else None
        hgt = y1 - y0
        legs = [span(y) for y in range(y0 + int(0.72 * hgt), y0 + int(0.85 * hgt) + 1)]
        legs = [l for l in legs if l]
        lw = max((r - l + 1) for l, r in legs) if legs else 0
        dark = 0
        for y in range(y0 + int(0.93 * hgt), y1 + 1):
            row = [x for x in range(sw) if mask[y][x] and sum(px[x, y]) / 3 < 45]
            if row:
                dark = max(dark, row[-1] - row[0] + 1)
        if kind == "sprite" and lw and dark > 1.3 * lw:
            flags.append("floor shadow (erase in Foxboard)")
        # holes: keyfix punched key colour through the subject (green-on-green clothing). Count key
        # pixels between each row's leftmost and rightmost subject pixel in the top 65% (head and torso,
        # where a real figure has no gaps; the gap between the legs is below that), vs the subject.
        holes = area = 0
        for y in range(y0, y0 + int(0.65 * (y1 - y0)) + 1):
            row = [x for x in range(sw) if mask[y][x]]
            if row:
                span = row[-1] - row[0] + 1
                holes += span - len(row); area += span
        s["holes"] = round(holes / max(1, area), 2)
        if kind == "sprite" and s["holes"] > 0.08:
            flags.append(f"key ate the subject (holes {s['holes']:.0%})")
            flags.append("unusable")  # counts double
        # stray marks: separate blobs away from the main figure (watermarks, signatures, debris)
        seen = [[False] * sw for _ in range(sh_)]; blobs = []
        for (bx, by) in pts:
            if seen[by][bx]:
                continue
            st, n = [(bx, by)], 0; seen[by][bx] = True
            while st:
                cx, cy = st.pop(); n += 1
                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if 0 <= nx < sw and 0 <= ny < sh_ and mask[ny][nx] and not seen[ny][nx]:
                        seen[ny][nx] = True; st.append((nx, ny))
            blobs.append(n)
        blobs.sort(reverse=True)
        stray = sum(b for b in blobs[1:] if b >= 6)
        if stray:
            flags.append(f"stray marks/watermark ({stray}px)")
        # key fringe: green-ish pixels left inside the subject
        kc = hexrgb(key); ki = max(range(3), key=lambda c: kc[c])
        fringe = sum(1 for p in pts if px[p][ki] > 150 and px[p][ki] > 1.6 * max(px[p][c] for c in range(3) if c != ki))
        if fringe / len(pts) > 0.01:
            flags.append("key fringe")
        if aspect:
            a2 = (x1 - x0 + 1) / (y1 - y0 + 1)
            s["aspect"] = round(a2, 2)
            if abs(a2 - aspect) / aspect > 0.35:
                flags.append(f"shape off (aspect {a2:.2f} vs {aspect:.2f})")
    if kind == "texture":
        def edge(a, b):
            return sum(sum(abs(a[i][c] - b[i][c]) for c in range(3)) for i in range(len(a))) / (3 * len(a))
        lr = edge([px[0, y] for y in range(sh_)], [px[sw - 1, y] for y in range(sh_)])
        tb = edge([px[x, 0] for x in range(sw)], [px[x, sh_ - 1] for x in range(sw)])
        s["seam"] = round(max(lr, tb))
        if s["seam"] > 25:
            flags.append(f"not seamless (edge diff {s['seam']})")
    total = s["palette_fit"] - 0.15 * len(flags)
    return {"file": os.path.basename(path), "score": round(max(0, total), 2), "flags": flags, **s}


def cmd_score(a):
    d = os.path.join(RESULTS, a.id)
    if not os.path.isdir(d):
        sys.exit(f"no results for {a.id} yet (run status)")
    pngs = sorted((f for f in os.listdir(d) if re.match(r"^\d+\.png$", f)), key=lambda f: int(f[:-4]))
    meta = {}
    for f in pngs:
        j = os.path.join(d, f[:-4] + ".json")
        meta[f] = json.load(open(j)) if os.path.exists(j) else {}
    jp = os.path.join(JOBS, a.id + ".json")
    jobkey = json.load(open(jp)).get("key") if os.path.exists(jp) else None
    res = []
    for f in pngs:
        r = score_one(os.path.join(d, f), a.game, a.kind, a.aspect, jobkey)
        r["seed"] = meta[f].get("seed")
        res.append(r)
    # contact sheet: takes side by side on mid grey, labels under each
    th = 360
    ims = [Image.open(os.path.join(d, f)).convert("RGB") for f in pngs]
    tw = [max(1, int(i.width * th / i.height)) for i in ims]
    sheet = Image.new("RGB", (sum(tw) + 12 * (len(ims) + 1), th + 70), (40, 40, 44))
    dr = ImageDraw.Draw(sheet); x = 12
    for im, wv, r in zip(ims, tw, res):
        sheet.paste(im.resize((wv, th)), (x, 12))
        dr.text((x, th + 18), f"#{r['file'][:-4]}  score {r['score']}", fill=(240, 200, 120))
        dr.text((x, th + 36), (", ".join(r["flags"]) or "clean")[:60], fill=(220, 220, 220))
        x += wv + 12
    os.makedirs(OUT, exist_ok=True)
    sp = os.path.join(OUT, f"{a.id}_sheet.png"); sheet.save(sp)
    best = max(res, key=lambda r: r["score"]) if res else None
    print(json.dumps({"id": a.id, "sheet": os.path.relpath(sp, ROOT), "takes": res,
                      "best": best and best["file"]}, indent=1))


# ---------- cut ----------
def cut_image(im, key, height=None, band=3):
    """Key colour -> transparent (soft 1-step edge), crop to the subject, optional resize,
    then despill: pull the key's colour cast out of pixels within `band` px of the cut edge.
    Only the edge band is touched, so real key-ish colours inside the subject (moss on a
    green key) survive."""
    from PIL import ImageFilter
    im = im.convert("RGBA"); kc = hexrgb(key); w, h = im.size; px = im.load()
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            d = ((r - kc[0]) ** 2 + (g - kc[1]) ** 2 + (b - kc[2]) ** 2) ** 0.5
            if d < 60:
                px[x, y] = (r, g, b, 0)
            elif d < 120:
                px[x, y] = (r, g, b, int(a * (d - 60) / 60))
    bbox = im.getchannel("A").getbbox()
    if bbox:
        im = im.crop(bbox)
    if height and im.height != height:
        im = im.resize((max(1, round(im.width * height / im.height)), height), Image.LANCZOS)
    # edge band = pixels within `band` px of transparency
    # (the image border counts as transparency: a tight crop puts the fringe right on it)
    from PIL import ImageOps
    hole = ImageOps.expand(im.getchannel("A").point(lambda v: 255 if v < 250 else 0), band, fill=255)
    near = hole.filter(ImageFilter.MaxFilter(2 * band + 1)).crop((band, band, band + im.width, band + im.height))
    on = [c for c in range(3) if kc[c] >= 128]; off = [c for c in range(3) if kc[c] < 128]
    px = im.load(); nb = near.load(); fixed = 0
    for y in range(im.height):
        for x in range(im.width):
            if not nb[x, y]:
                continue
            p = list(px[x, y])
            if p[3] == 0:
                continue
            spill = min(p[c] for c in on) - (max(p[c] for c in off) if off else 0)
            if spill > 0:
                for c in on:
                    p[c] -= spill
                px[x, y] = tuple(p); fixed += 1
    return im, fixed


def cmd_cut(a):
    src = a.src
    m = re.match(r"^([A-Za-z0-9_-]{4,64})/(\d+)$", src)  # "<job id>/<take>" shorthand
    key = a.key
    if m:
        if not key:
            jp = os.path.join(JOBS, m.group(1) + ".json")
            key = json.load(open(jp)).get("key") if os.path.exists(jp) else None
        src = os.path.join(RESULTS, m.group(1), m.group(2) + ".png")
    if not key:
        sys.exit("no key colour: pass --key")
    im, fixed = cut_image(Image.open(src), key, a.height)
    im.save(a.out, optimize=True)
    print(json.dumps({"out": a.out, "size": list(im.size), "despilled_px": fixed, "bytes": os.path.getsize(a.out)}))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    q = sub.add_parser("queue"); q.add_argument("--id", required=True); q.add_argument("--prompt-file", required=True)
    q.add_argument("--n", type=int, default=4); q.add_argument("--w", type=int, default=512); q.add_argument("--h", type=int, default=512)
    q.add_argument("--seed", type=int); q.add_argument("--key"); q.add_argument("--trailer", default="")
    q.add_argument("--mode", default="new", help="new | sketch | edit | expand | upscale")
    q.add_argument("--init", help="path to a start-from image (png/jpg). Required for sketch/edit.")
    q.add_argument("--mask", help="path to a mask image (white=change, black=keep). Required for edit.")
    q.add_argument("--ref", help="path to a style-reference image (mode new only). Style-board workaround, not IP-Adapter.")
    q.add_argument("--ref-strength", type=float, dest="ref_strength", help="how hard to follow --ref (0.15-0.85, default 0.55)")
    q.add_argument("--strength", type=float, help="img2img strength 0.3-0.95 (sketch default is 0.7 in the renderer)")
    q.add_argument("--tile", action="store_true", help="seamless (sd.cpp --circular). FLUX path only.")
    q.add_argument("--send-to", dest="send_to", choices=["lethemoor", "duffquest"], help="auto-send each finished take to this game's grok_art/ inbox")
    q.add_argument("--no-publish", action="store_true", help="write job files but do not commit or push")
    s = sub.add_parser("status"); s.add_argument("ids", nargs="+")
    c = sub.add_parser("score"); c.add_argument("id"); c.add_argument("--game", default="lethemoor", choices=sorted(GAMES))
    c.add_argument("--kind", default="sprite", choices=["sprite", "texture", "scene", "hud"]); c.add_argument("--aspect", type=float)
    k = sub.add_parser("cut"); k.add_argument("src", help="<job id>/<take> or a png path"); k.add_argument("out")
    k.add_argument("--key"); k.add_argument("--height", type=int)
    a = p.parse_args()
    {"queue": cmd_queue, "status": cmd_status, "score": cmd_score, "cut": cmd_cut}[a.cmd](a)


if __name__ == "__main__":
    main()
