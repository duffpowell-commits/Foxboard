"""Forge auto-send to game: job field "game" -> runner drops each take in the game's inbox; Lethemoor uses the direct path."""
import json, os, subprocess, sys, tempfile
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
fails = []
def check(name, ok, info=""):
    print(("PASS " if ok else "FAIL ") + name, info if not ok else ""); ok or fails.append(name)

# --- runner side (forge/send_game.py), no network
sys.path.insert(0, str(ROOT / "forge")); import send_game
with tempfile.TemporaryDirectory() as t:
    t = Path(t); (t / "forge/jobs").mkdir(parents=True); (t / "forge/results/j1").mkdir(parents=True)
    (t / "forge/jobs/j1.json").write_text(json.dumps({"prompt": "x", "game": "lethemoor", "name": "Lantern Bearer!", "at": 1795392000000}))
    (t / "forge/jobs/j2.json").write_text(json.dumps({"prompt": "x"}))
    (t / "forge/jobs/j3.json").write_text(json.dumps({"prompt": "x", "game": "../../evil"}))
    (t / "forge/results/j1/0.png").write_bytes(b"\x89PNG")
    p = send_game.plan("j1", 0, t)
    check("plan targets lethemoor inbox", p and p["repo"] == "duffpowell-commits/lethemoor" and p["path"].startswith("grok_art/") and p["path"].endswith("-foxboard/lantern_bearer-0.png"), p)
    check("no game -> nothing to send", send_game.plan("j2", 0, t) is None)
    check("unknown game refused", "error" in send_game.plan("j3", 0, t))
    check("failed take not sent", "error" in send_game.plan("j1", 1, t))
    env = {**os.environ, "FORGE_NO_GIT": "1"}; env.pop("GAME_PUSH_TOKEN", None); env.pop("FORGE_DRY", None)
    r = subprocess.run([sys.executable, str(ROOT / "forge/send_game.py"), "j1", "0"], cwd=t, env=env, capture_output=True, text=True)
    sent = t / "forge/results/j1/0.sent.json"
    check("missing token: take still succeeds, reason recorded", r.returncode == 0 and sent.exists() and "GAME_PUSH_TOKEN" in sent.read_text(), r.stderr[-300:])
wf = (ROOT / ".github/workflows/forge.yml").read_text()
check("workflow runs send_game after render", "forge/send_game.py" in wf and "secrets.GAME_PUSH_TOKEN" in wf and wf.index("render_one.py") < wf.index("send_game.py"))

# --- app side
app = os.environ.get("APP_URL") or (ROOT / "index.html").as_uri()
with sync_playwright() as pw:
    b = getattr(pw, os.environ.get('BROWSER', 'chromium')).launch()
    pg = b.new_page(viewport={"width": 390, "height": 820}, has_touch=True)
    pg.goto(app); pg.wait_for_function("window.Foxboard")
    r = pg.evaluate("""() => { const out = {};
      const f = Foxboard.forgeFiles({prompt:'a crow', game:'lethemoor', name:'crow', n:1});
      out.job = JSON.parse(f.files[`forge/jobs/${f.jid}.json`]);
      try { Foxboard.forgeFiles({prompt:'a crow', game:'nope'}); out.bad = 'accepted'; } catch(e) { out.bad = String(e.message); }
      out.plain = JSON.parse(Object.entries(Foxboard.forgeFiles({prompt:'a crow'}).files)[0][1]).game ?? null;
      out.doc = Foxboard.help().forge; out.direct = window.__fb && __fb.t && __fb.t.bible ? null : null;
      return out; }""")
    check("forgeFiles carries game + name", r["job"].get("game") == "lethemoor" and r["job"].get("name") == "crow", r["job"])
    check("unknown game rejected in app", r["bad"] != "accepted", r["bad"])
    check("no game by default", r["plain"] is None)
    check("API_DOC documents game", "game:" in r["doc"])
    html = (ROOT / "index.html").read_text()
    check("Lethemoor direct path on by default", "inbox:'grok_art',key:'#00FF00',decoder:true,direct:true," in html)
    check("Forge screen has auto-send toggle", "📦 Auto-send takes to the game" in html)
    b.close()
print("ALL PASS" if not fails else f"{len(fails)} FAILED"); sys.exit(1 if fails else 0)
