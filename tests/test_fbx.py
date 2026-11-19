"""tools/claude/fbx.py + render.js: push art into the shared library format and pull it back out.

Simulates the db with files laid out the way ArtifactData out_dir writes them.
Run: python tests/test_fbx.py   (needs pillow + node playwright)
"""
import json, pathlib, shutil, subprocess, sys, tempfile
from PIL import Image, ImageDraw
ROOT = pathlib.Path(__file__).resolve().parent.parent
FBX = ROOT / "tools/claude/fbx.py"; RENDER = ROOT / "tools/claude/render.js"
fails = 0
def check(name, ok, extra=""):
    global fails
    print(("PASS " if ok else "FAIL ") + name + (f"  ({extra})" if extra else "")); fails += 0 if ok else 1
def run(*a):
    r = subprocess.run([str(x) for x in a], capture_output=True, text=True)
    if r.returncode: print(r.stdout[-1500:], r.stderr[-1500:])
    return r

tmp = pathlib.Path(tempfile.mkdtemp())
try:
    # a noisy 768x768 image on an exact magenta key, so the body needs several chunks
    im = Image.effect_noise((768, 768), 90).convert("RGB")
    im.paste((255, 0, 255), (0, 0, 768, 120))
    d = ImageDraw.Draw(im); d.rectangle([300, 300, 460, 460], fill=(20, 200, 90))
    src = tmp / "art.png"; im.save(src)

    out = tmp / "push"
    r = run(sys.executable, FBX, "push-image", src, "Lethemoor – Test piece", out, "--title", "BEARER", "--cut-key", "#FF00FF")
    check("push-image runs", r.returncode == 0)
    plan = json.loads((out / "writes.json").read_text()) if (out / "writes.json").exists() else {"batches": []}
    batches = plan.get("batches", []); flat = [w for b in batches for w in b]
    metas = [w for w in flat if w["collection"] == "library"]; chunks = [w for w in flat if w["collection"] == "libchunks"]
    check("one meta write, last in the last batch", len(metas) == 1 and batches and batches[-1][-1] is not None and batches[-1][-1]["collection"] == "library")
    check("body split into several chunks", len(chunks) >= 2, f"{len(chunks)}")
    sizes = [pathlib.Path(w["file_path"]).stat().st_size for w in flat]
    check("every doc file < 256 KiB", sizes and max(sizes) < 256 * 1024, f"max {max(sizes) if sizes else 0}")
    check("every batch < 1 MiB and <= 50 writes", all(sum(pathlib.Path(w['file_path']).stat().st_size for w in b) < 1_000_000 and len(b) <= 50 for b in batches))
    check("file paths absolute", all(pathlib.Path(w["file_path"]).is_absolute() for w in flat))
    meta = json.loads(pathlib.Path(metas[0]["file_path"]).read_text()) if metas else {}
    need = {"name", "w", "h", "frames", "pixel", "by", "at", "thumb", "chunks"}
    check("meta has the app's fields", need <= set(meta), str(sorted(need - set(meta))))
    check("meta.chunks matches", meta.get("chunks") == len(chunks))
    check("thumb is a PNG data URL", str(meta.get("thumb", "")).startswith("data:image/png;base64,"))
    ids = {w["doc_id"] for w in metas}; iid = next(iter(ids), "")
    check("chunk ids are <id>_<n>", sorted(w["doc_id"] for w in chunks) == sorted(f"{iid}_{n}" for n in range(len(chunks))))

    # simulate the db, the way ArtifactData out_dir saves reads: <out_dir>/<collection>/<doc_id>.json
    db = tmp / "db"
    for w in flat:
        p = db / w["collection"] / (w["doc_id"] + ".json"); p.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(w["file_path"], p)
    docf = tmp / "doc.json"
    r = run(sys.executable, FBX, "pull", iid, db, docf)
    check("pull runs", r.returncode == 0)
    doc = json.loads(docf.read_text()) if docf.exists() else {}
    check("pulled doc is 768x768 with 1 page", doc.get("w") == 768 and doc.get("h") == 768 and len(doc.get("pages", [])) == 1)
    objs = doc.get("pages", [{}])[0].get("objects", [])
    check("image + title text objects", [o.get("type") for o in objs] == ["image", "text"], str([o.get("type") for o in objs]))

    r = run("node", RENDER, docf, tmp / "out", 1)
    png = tmp / "out_0.png"
    check("render.js renders page 0", r.returncode == 0 and png.exists())
    if png.exists():
        got = Image.open(png).convert("RGBA"); px = got.load()
        check("key colour cut to transparent", px[10, 10][3] == 0, str(px[10, 10]))
        g = px[380, 440]
        check("subject pixels survive", g[3] == 255 and g[1] > 150 and g[0] < 80, str(g))
        title = sum(1 for x in range(200, 568) for y in range(0, 140) if px[x, y][3] == 255)
        check("title text drawn by the app", title > 500, str(title))

    # pull also accepts ArtifactData-style wrapped files ({"data": {...}, "version": n})
    for f in db.rglob("*.json"):
        f.write_text(json.dumps({"id": f.stem, "version": 1, "data": json.loads(f.read_text())}))
    r = run(sys.executable, FBX, "pull", iid, db, tmp / "doc2.json")
    check("pull handles wrapped read files", r.returncode == 0 and json.loads((tmp / "doc2.json").read_text()) == doc)

    # push-doc: a 2-frame doc
    two = {"name": "Two frames", "w": 32, "h": 32, "bg": "transparent", "pixel": True, "grid": True, "onion": False, "fps": 8, "cur": 0,
           "pages": [{"id": "a", "objects": []}, {"id": "b", "objects": []}]}
    (tmp / "two.json").write_text(json.dumps(two)); Image.new("RGBA", (32, 32)).save(tmp / "prev.png")
    r = run(sys.executable, FBX, "push-doc", tmp / "two.json", tmp / "prev.png", tmp / "push2")
    m2 = [w for b in json.loads((tmp / "push2/writes.json").read_text())["batches"] for w in b if w["collection"] == "library"] if r.returncode == 0 else []
    check("push-doc: frames=2, pixel", bool(m2) and json.loads(pathlib.Path(m2[0]["file_path"]).read_text())["frames"] == 2)
finally:
    shutil.rmtree(tmp, ignore_errors=True)
print("ALL PASS" if not fails else f"{fails} FAILED"); sys.exit(1 if fails else 0)
