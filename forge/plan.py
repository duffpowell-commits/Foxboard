"""List job/version pairs still to render -> GitHub Actions matrix."""
import json, os, pathlib, re
items = []
for jf in sorted(pathlib.Path("forge/jobs").glob("*.json")):
    try: job = json.loads(jf.read_text())
    except Exception: continue
    jid = jf.stem
    if not re.fullmatch(r"[A-Za-z0-9_-]{4,64}", jid): continue
    res = pathlib.Path("forge/results") / jid
    if (res / "done.json").exists(): continue
    n = max(1, min(4, int(job.get("n", 1))))
    for k in range(n):
        # a committed error.txt is a finished failed take (finish.py counts it); do not retry it forever
        if not (res / f"{k}.png").exists() and not (res / f"{k}.error.txt").exists(): items.append({"job": jid, "k": k})
items = items[:16]
with open(os.environ["GITHUB_OUTPUT"], "a") as fh:
    fh.write(f"matrix={json.dumps(items)}\nany={'true' if items else 'false'}\n")
print(items)
