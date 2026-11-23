"""Deliver a finished Forge take straight into a game repo's art inbox (job field "game").

Runs on the render runner after render_one.py. Writes <inbox>/<YYYY-MM-DD>-foxboard/<job>-<k>.png on the game
repo's main through the GitHub contents API, using the GAME_PUSH_TOKEN secret (a fine-grained token with
Contents: read and write on the game repos). Never fails the take: a missing token, an unknown game or an API
error is written to forge/results/<id>/<k>.sent.json and the job carries on.
FORGE_DRY=1 prints what it would send instead of calling GitHub (tests).
"""
import base64, datetime, json, os, pathlib, re, sys, time, urllib.error, urllib.request

# Only these games can be targeted from a (public) job file. inbox dirs are paths-ignored by the games' builds.
GAMES = {
    "lethemoor": ("duffpowell-commits/lethemoor", "grok_art"),
    "duffquest": ("duffpowell-commits/duffquest", "grok_art"),
}


def plan(jid, k, root="."):
    root = pathlib.Path(root)
    job = json.loads((root / f"forge/jobs/{jid}.json").read_text())
    game = job.get("game")
    if not game:
        return None
    if game not in GAMES:
        return {"error": f"unknown game {game!r}"}
    png = root / f"forge/results/{jid}/{k}.png"
    if not png.exists():
        return {"error": "take has no image (render failed)"}
    repo, inbox = GAMES[game]
    day = datetime.date.fromtimestamp(job["at"] / 1000) if job.get("at") else datetime.date.today()
    name = re.sub(r"[^a-z0-9_-]+", "_", str(job.get("name") or jid).lower()).strip("_")[:48] or "art"
    return {"repo": repo, "path": f"{inbox}/{day.isoformat()}-foxboard/{name}-{k}.png", "png": str(png), "game": game}


def put(repo, path, data, token, message):
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    body = json.dumps({"message": message, "content": base64.b64encode(data).decode(), "branch": "main"}).encode()
    for i in range(5):
        req = urllib.request.Request(url, data=body, method="PUT", headers={
            "Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json", "User-Agent": "foxboard-forge"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read()).get("commit", {}).get("sha", "")
        except urllib.error.HTTPError as e:
            if e.code == 422:  # file already there (re-run): leave it
                return "exists"
            if e.code in (409, 500, 502, 503) and i < 4:  # main moved under us / GitHub hiccup
                time.sleep(3 + i * 4); continue
            raise RuntimeError(f"GitHub {e.code}: {e.read()[:300].decode(errors='replace')}")
    raise RuntimeError("gave up after retries")


def main():
    jid, k = sys.argv[1], int(sys.argv[2])
    p = plan(jid, k)
    if p is None:
        return 0
    out = pathlib.Path(f"forge/results/{jid}/{k}.sent.json")
    if "error" in p:
        res = {"ok": False, "error": p["error"]}
    elif os.environ.get("FORGE_DRY"):
        print(json.dumps(p)); return 0
    elif not os.environ.get("GAME_PUSH_TOKEN"):
        res = {"ok": False, "error": "GAME_PUSH_TOKEN secret not set on the Foxboard repo", "game": p["game"]}
    else:
        try:
            sha = put(p["repo"], p["path"], pathlib.Path(p["png"]).read_bytes(), os.environ["GAME_PUSH_TOKEN"],
                      f"Foxboard Forge: {jid} take {k} (auto-sent)")
            res = {"ok": True, "repo": p["repo"], "path": p["path"], "commit": sha, "game": p["game"]}
        except Exception as e:
            res = {"ok": False, "error": str(e)[:400], "game": p["game"]}
    print("send_game:", json.dumps(res))
    out.write_text(json.dumps(res) + "\n")
    if os.environ.get("FORGE_NO_GIT"):
        return 0
    import subprocess
    subprocess.run(["git", "add", str(out)])
    subprocess.run(["git", "commit", "-q", "-m", f"[skip ci] forge: {jid} #{k} sent to {p.get('game', '?')}"])
    for i in range(6):
        if subprocess.run(["git", "pull", "-q", "--rebase", "origin", "main"]).returncode == 0 and \
                subprocess.run(["git", "push", "-q", "origin", "HEAD:main"]).returncode == 0:
            break
        time.sleep(5 + i * 5)
    return 0


if __name__ == "__main__":
    sys.exit(main())
