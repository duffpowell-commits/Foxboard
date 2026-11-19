"""Write done.json for every job whose versions all landed (or failed)."""
import json, pathlib
for jf in sorted(pathlib.Path("forge/jobs").glob("*.json")):
    jid = jf.stem; res = pathlib.Path("forge/results") / jid
    if (res / "done.json").exists(): continue
    try: n = max(1, min(4, int(json.loads(jf.read_text()).get("n", 1))))
    except Exception: continue
    ok = [k for k in range(n) if (res / f"{k}.b64").exists()]
    bad = [k for k in range(n) if (res / f"{k}.error.txt").exists()]
    if len(ok) + len(bad) == n:
        res.mkdir(parents=True, exist_ok=True)
        (res / "done.json").write_text(json.dumps({"ok": ok, "failed": bad}))
        print("done", jid, ok, bad)
