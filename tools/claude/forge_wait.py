#!/usr/bin/env python3
"""Wait for Forge jobs to finish, then exit. Run it with Bash run_in_background: the session is woken when it exits,
so Claude gets pinged the moment results land instead of polling by hand.

  python3 tools/claude/forge_wait.py <job-id> [<job-id> ...] [--timeout-min 60] [--repo .] [--every 60]

Sleeps until each job's ETA (from its size and mode), then fetches main every --every seconds. Exits 0 when every job has
done.json (prints ok/failed per job and which takes landed), 2 when one looks stuck (2x ETA, no files at all), 3 on timeout.
GitHub itself can't wake a Claude session; this is the in-session ping. Across sessions keep using send_later."""
import argparse, json, subprocess, sys, time
ap = argparse.ArgumentParser(); ap.add_argument("jobs", nargs="+"); ap.add_argument("--timeout-min", type=float, default=60)
ap.add_argument("--repo", default="."); ap.add_argument("--every", type=float, default=60); ap.add_argument("--ref", default="origin/main")
a = ap.parse_args()
SIZES = {(768, 768): 15, (512, 512): 7, (1024, 1024): 27, (576, 1024): 16, (1024, 576): 16}
def git(*args): return subprocess.run(["git", "-C", a.repo, *args], capture_output=True, text=True)
def show(path): r = git("show", f"{a.ref}:{path}"); return r.stdout if r.returncode == 0 else None
def files(jid): r = git("ls-tree", "--name-only", f"{a.ref}", f"forge/results/{jid}/"); return [l.split("/")[-1] for l in r.stdout.split()] if r.returncode == 0 else []
def eta_min(jid):
    j = json.loads(show(f"forge/jobs/{jid}.json") or "{}")
    per = SIZES.get((j.get("w"), j.get("h")), 15) * (1.4 if j.get("mode") == "sketch" else 1)
    return per + 3, j.get("at", time.time() * 1000) / 1000
start = time.time(); left = set(a.jobs)
git("fetch", "-q", "origin", "main")
etas = {jid: eta_min(jid) for jid in a.jobs}
first = min(at + m * 60 for m, at in etas.values()) - time.time()
if first > 0: print(f"sleeping {first/60:.1f} min until the first ETA", flush=True); time.sleep(min(first, a.timeout_min * 60))
while left:
    git("fetch", "-q", "origin", "main")
    for jid in sorted(left):
        d = show(f"forge/results/{jid}/done.json")
        if d:
            f = files(jid); print(json.dumps({"job": jid, "done": json.loads(d), "takes": sorted(x for x in f if x.endswith(".png"))}), flush=True); left.discard(jid); continue
        m, at = etas[jid]
        if time.time() - at > 2 * m * 60 and not files(jid): print(json.dumps({"job": jid, "stuck": True, "minutes": round((time.time() - at) / 60)}), flush=True); sys.exit(2)
    if not left: break
    if time.time() - start > a.timeout_min * 60: print(json.dumps({"timeout": sorted(left)}), flush=True); sys.exit(3)
    time.sleep(a.every)
sys.exit(0)
