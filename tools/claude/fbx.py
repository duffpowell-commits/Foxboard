#!/usr/bin/env python3
"""Foxboard shared-library packer for Claude sessions (transport = the ArtifactData tool on the Foxboard artifact).

  fbx.py push-image art.png "Game – Piece" OUTDIR [--title T] [--sub S] [--font CSS] [--color HEX] [--pixel] [--cut-key HEX] [--max PX]
  fbx.py push-doc doc.json preview.png OUTDIR
  fbx.py pull <id> <db_dir> doc.json
  fbx.py push-draft doc.json preview.png OUTDIR --title T [--note N]   (Claude -> Duff: shows an "open it?" banner)
  fbx.py inbox <id> <db_dir> OUTDIR                                     (Duff -> Claude: unpacks a Send to Claude item)

push-* writes one JSON file per db document into OUTDIR plus OUTDIR/writes.json:
  {"id": ..., "batches": [[{op, collection, doc_id, file_path}, ...], ...]}
Send each batch as one ArtifactData `batch` call on the Foxboard URL, in order. The library meta write is
last in the last batch, so the item only appears in the app once every chunk is there.
pull reads files saved by ArtifactData reads with out_dir=<db_dir> (library/<id>.json, libchunks/<id>_<n>.json).
Format mirrors shareCanvas()/openLibCanvas() in index.html: chunks of 180000 chars, meta {name,w,h,frames,pixel,by,at,thumb,chunks}.
"""
import argparse, base64, io, json, pathlib, random, string, sys, time
from PIL import Image

CHUNK = 180000          # same as index.html
BATCH_BYTES = 900_000   # ArtifactData batch body limit is 1 MiB
FONTS = {"pixel": '"Press Start 2P", monospace', "comic": "Bangers, Impact, sans-serif", "fantasy": "Cinzel, Georgia, serif",
         "gothic": '"Pirata One", serif', "horror": "Creepster, fantasy", "marker": '"Permanent Marker", cursive'}


def uid(n=7): return "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(n))


def data_url(im):
    """PNG when the image has transparency, else JPEG (much smaller; the db holds base64)."""
    im = im.convert("RGBA") if im.mode not in ("RGB", "RGBA") else im
    buf = io.BytesIO()
    if im.mode == "RGBA" and im.getextrema()[3][0] < 255:
        im.save(buf, "PNG", optimize=True); kind = "png"
    else:
        im.convert("RGB").save(buf, "JPEG", quality=90); kind = "jpeg"
    return f"data:image/{kind};base64," + base64.b64encode(buf.getvalue()).decode()


def thumb_url(im):
    im = im.convert("RGBA"); im.thumbnail((128, 128), Image.NEAREST if max(im.size) <= 128 else Image.LANCZOS)
    c = Image.new("RGBA", (128, 128), (59, 54, 80, 255)); c.alpha_composite(im, ((128 - im.width) // 2, (128 - im.height) // 2))
    buf = io.BytesIO(); c.save(buf, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def cut_key(im, key):
    kc = tuple(int(key[i:i + 2], 16) for i in (1, 3, 5)); im = im.convert("RGBA"); px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            if px[x, y][:3] == kc: px[x, y] = (0, 0, 0, 0)
    return im


def write_out(doc, preview, out, kind="library", title=None, note=None):
    out = pathlib.Path(out).resolve(); out.mkdir(parents=True, exist_ok=True)
    iid = uid() + uid()
    meta_coll, chunk_coll = ("library", "libchunks") if kind == "library" else ("fromclaude", "fromclaudechunks")
    body = json.dumps({**doc, "cur": 0}, separators=(",", ":"))
    parts = [body[i:i + CHUNK] for i in range(0, len(body), CHUNK)]
    writes = []
    for n, p in enumerate(parts):
        f = out / f"{chunk_coll}_{iid}_{n}.json"; f.write_text(json.dumps({"item": iid, "n": n, "data": p}))
        writes.append({"op": "set", "collection": chunk_coll, "doc_id": f"{iid}_{n}", "file_path": str(f)})
    meta = {"name": doc.get("name") or "Untitled", "w": doc["w"], "h": doc["h"], "frames": len(doc["pages"]), "pixel": bool(doc.get("pixel")),
            "by": "", "at": int(time.time() * 1000), "thumb": thumb_url(preview), "chunks": len(parts)}
    if kind != "library": meta.update({"title": (title or doc.get("name") or "Untitled")[:80], "note": (note or "")[:300]})
    f = out / f"{meta_coll}_{iid}.json"; f.write_text(json.dumps(meta))
    writes.append({"op": "set", "collection": meta_coll, "doc_id": iid, "file_path": str(f)})
    batches, cur, size = [], [], 0
    for w in writes:
        s = pathlib.Path(w["file_path"]).stat().st_size + 300
        if cur and (size + s > BATCH_BYTES or len(cur) >= 50): batches.append(cur); cur, size = [], 0
        cur.append(w); size += s
    batches.append(cur)
    (out / "writes.json").write_text(json.dumps({"id": iid, "batches": batches}, indent=1))
    print(json.dumps({"id": iid, "chunks": len(parts), "batches": len(batches), "writes": str(out / "writes.json")}))


def push_image(a):
    im = Image.open(a.image); im.load()
    if a.cut_key: im = cut_key(im, a.cut_key)
    if max(im.size) > a.max:
        k = a.max / max(im.size); im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
    w, h = im.size
    objs = [{"id": uid(), "type": "image", "name": a.name, "x": 0, "y": 0, "w": w, "h": h, "rot": 0, "opacity": 1,
             "src": data_url(im), "natW": w, "natH": h, "fill": "", "stroke": "#1a0d05", "strokeW": 0, "radius": 0, "hidden": False, "locked": False}]
    def text(t, size, cy):
        font = FONTS.get(a.font, a.font) if a.font else (FONTS["pixel"] if a.pixel else FONTS["comic"])
        tw, th = max(1, round(len(t) * size * 0.6)), round(size * 1.2)
        return {"id": uid(), "type": "text", "text": t, "font": font, "size": size, "bold": False, "italic": False, "align": "center",
                "fill": a.color, "stroke": "#1a0d05", "strokeW": 0 if a.pixel else max(1, round(size / 10)),
                "x": (w - tw) / 2, "y": cy - th / 2, "w": tw, "h": th, "rot": 0, "opacity": 1, "radius": 0, "hidden": False, "locked": False}
    if a.title: objs.append(text(a.title, max(8, round(min(w, h) / 9)), h * 0.1))
    if a.sub: objs.append(text(a.sub, max(8, round(min(w, h) / 18)), h * 0.9))
    doc = {"name": a.name, "w": w, "h": h, "bg": "transparent" if a.pixel or im.mode == "RGBA" else "#ffffff", "pixel": a.pixel, "grid": a.pixel,
           "onion": False, "fps": 8, "cur": 0, "pages": [{"id": uid(), "objects": objs}]}
    write_out(doc, im, a.out)


def push_doc(a):
    doc = json.loads(pathlib.Path(a.doc).read_text())
    assert doc.get("w", 0) > 0 and doc.get("h", 0) > 0 and doc.get("pages"), "doc needs w, h and pages"
    write_out(doc, Image.open(a.preview), a.out)


def push_draft(a):
    doc = json.loads(pathlib.Path(a.doc).read_text())
    assert doc.get("w", 0) > 0 and doc.get("h", 0) > 0 and doc.get("pages"), "doc needs w, h and pages"
    write_out(doc, Image.open(a.preview), a.out, kind="draft", title=a.title, note=a.note)


def inbox(a):
    """Unpack a Send to Claude item read with ArtifactData out_dir=<db_dir> (toclaude/<id>.json + toclaudechunks/<id>_<n>.json)."""
    db = pathlib.Path(a.db_dir); out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    meta = read_db(db / "toclaude" / f"{a.id}.json")
    parts = sorted((c for c in (read_db(f) for f in (db / "toclaudechunks").glob("*.json")) if c.get("item") == a.id), key=lambda c: c["n"])
    if len(parts) != meta.get("chunks"): sys.exit(f"have {len(parts)} chunks, meta says {meta.get('chunks')}: read every toclaudechunks row for {a.id}")
    doc = json.loads("".join(c["data"] for c in parts)); (out / "doc.json").write_text(json.dumps(doc))
    png = str(meta.get("png", "")); ext = "jpg" if png.startswith("data:image/jpeg") else "png"
    if "," in png: (out / f"snapshot.{ext}").write_bytes(base64.b64decode(png.split(",", 1)[1]))
    info = {k: meta.get(k) for k in ("note", "name", "w", "h", "pixel", "frames", "cur", "sel", "game", "status", "at", "ver")}
    info["layers"] = json.loads(meta.get("layers") or "[]"); info["doc"] = str(out / "doc.json"); info["snapshot"] = str(out / f"snapshot.{ext}")
    (out / "info.json").write_text(json.dumps(info, indent=1)); print(json.dumps({k: info[k] for k in ("note", "name", "w", "h", "frames", "doc", "snapshot")}))


def read_db(p):
    j = json.loads(pathlib.Path(p).read_text())
    return j["data"] if isinstance(j, dict) and isinstance(j.get("data"), dict) else j


def pull(a):
    db = pathlib.Path(a.db_dir)
    meta = read_db(db / "library" / f"{a.id}.json")
    parts = []
    for f in (db / "libchunks").glob("*.json"):
        c = read_db(f)
        if c.get("item") == a.id: parts.append(c)
    parts.sort(key=lambda c: c["n"])
    if len(parts) != meta.get("chunks"): sys.exit(f"have {len(parts)} chunks, meta says {meta.get('chunks')}: read every libchunks row for {a.id}")
    doc = json.loads("".join(c["data"] for c in parts))
    pathlib.Path(a.doc).write_text(json.dumps(doc))
    print(json.dumps({"name": meta.get("name"), "w": doc["w"], "h": doc["h"], "frames": len(doc["pages"]), "doc": str(a.doc)}))


ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest="cmd", required=True)
p = sp.add_parser("push-image"); p.add_argument("image"); p.add_argument("name"); p.add_argument("out")
p.add_argument("--title"); p.add_argument("--sub"); p.add_argument("--font"); p.add_argument("--color", default="#ffffff")
p.add_argument("--pixel", action="store_true"); p.add_argument("--cut-key"); p.add_argument("--max", type=int, default=1024)
p.set_defaults(fn=push_image)
p = sp.add_parser("push-doc"); p.add_argument("doc"); p.add_argument("preview"); p.add_argument("out"); p.set_defaults(fn=push_doc)
p = sp.add_parser("pull"); p.add_argument("id"); p.add_argument("db_dir"); p.add_argument("doc"); p.set_defaults(fn=pull)
p = sp.add_parser("push-draft"); p.add_argument("doc"); p.add_argument("preview"); p.add_argument("out"); p.add_argument("--title"); p.add_argument("--note"); p.set_defaults(fn=push_draft)
p = sp.add_parser("inbox"); p.add_argument("id"); p.add_argument("db_dir"); p.add_argument("out"); p.set_defaults(fn=inbox)
a = ap.parse_args(); a.fn(a)
