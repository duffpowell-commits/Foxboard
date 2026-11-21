# Claude's access to every Foxboard feature

Everything Duff can do by touch, Claude can do from a cloud session. This is how.

## 1. The command API (`window.Foxboard`)
The app exposes one scriptable object. `Foxboard.help()` returns every command with its arguments:
- layers: `add`, `element`, `set`, `get`, `list`, `remove`, `move`, `order`
- selection/layout: `select`, `selected`, `group`, `ungroup`, `align`, `distribute`
- images: `crop`, `mask`, `removeBg`, `magicErase` (rects/circles/tap), `expand` (local fill), `adjust`, `snapPalette`
- look: in `set`: `shadow`, `grad`, `blend`, `curve`, `opacity`, `stroke`, fonts and so on
- canvas: `newDoc`, `load`, `doc`, `resizeCanvas`, `addPage`, `goPage`, `delPage`, `setFps`
- output: `render`, `renderCanvas`, `exportFile('png'|'jpg'|'gif'|'sheet'|'pdf'|'video')`
- AI: `forge` (in-app, through the GitHub connector) and `forgeFiles` (builds the job files so Claude can commit them)
- `undo`, `redo`

## 2. Run it headless: `tools/claude/fb.js`
```
node tools/claude/fb.js script.js [--doc in.json] [--out doc.json] [--png prefix] [--scale n] [--files dir]
```
`script.js` is the body of an async function. It has `F` (= Foxboard), `save(blob|dataURL, name)`, `saveForge(r)`, `loaded()`, `wait(ms)` and `log()`. Its return value comes back as JSON.
- Edit one of Duff's pieces: pull it with `fbx.py pull` and pass it as `--doc`. Write the result with `--out`, then push it back with `fbx.py push-doc`. See the foxboard-link skill for the library steps.
- Always look at `--png` previews before handing anything over.

## 3. Forge from Claude
```js
const r = F.forgeFiles({mode:'edit', id, mask:{rects:[[x,y,w,h]]}, prompt:'...'});   // or mode 'new' | 'expand' | 'upscale'
await saveForge(r);   // writes forge/jobs/<id>.json (+ .init.b64 / .mask.b64) into the repo
```
Then commit those job files and push them to **Foxboard `main`** (or use `art_loop.py queue`, which does that). The workflow only runs on a push to `main` under `forge/jobs/**` while the repo is public. Results land in `forge/results/<id>/` in about 5–15 minutes. Pass `jid` to choose the id. Only `<id>.json` triggers a render, and the input files must be in the same commit. Code changes still go through a pull request.

## 4. The shared library (Duff's phone sees it)
Use the artifact db tools on artifact `408d3d4e-8800-4a0e-9cdc-1251d2b400a7`. `library/<id>` holds each piece's meta and `libchunks/<id>_<n>` holds its body. `fbx.py push-doc` / `pull` do the packing. Never overwrite or delete what Duff made. Push new items.

## 5. The art loop (`art_loop.py`)
Render, judge, reroll, deliver, without Duff babysitting it (steps in the art-loop skill).
```
python3 tools/claude/art_loop.py queue  --id lm-sky-c-20261119 --prompt-file p.txt --n 2 --w 512 --h 512 [--key '#00FF00']
       [--mode new|sketch|edit --init a.png --mask m.png --ref style.png --ref-strength 0.55 --strength 0.7 --tile --seed N]
python3 tools/claude/art_loop.py status lm-sky-c-20261119
python3 tools/claude/art_loop.py score  lm-sky-c-20261119 --kind sprite|texture|scene|hud [--aspect 0.37]
python3 tools/claude/art_loop.py cut    lm-sky-c-20261119/1 pick.png --height 640
```
Sizes must be 256-1024 and a multiple of 64. `queue` publishes a job-only commit to Foxboard `main`
(that is what `forge.yml` renders). Use `--no-publish` to write the files without pushing.
`--ref` is a style-board workaround, not IP-Adapter. `--init` with `--mode new` switches to sketch and warns.
`score` / `cut` are the cleanup and QA tools to use before a handoff.
`score` flags what kept going wrong by eye: key punching holes through the subject, floor shadow,
watermarks/stray marks, cropped head or sides, floating feet, off-palette, baked glow, seams on
textures. It writes `forge/out/<id>_sheet.png`. `cut` turns the pick into a game-ready PNG: key to transparent, crop, resize, and despill (green/magenta cast pulled out of the 3 px edge band only, so moss inside stays green). It's a pre-filter: still look at the sheet
(it can't see faces, and the faceless rule is the one that matters most). Test: `tests/test_art_loop.py`.

## 6. Duff → Claude and back (Send to Claude, drafts, problem log)
- **Inbox:** `ArtifactData list` collection `toclaude` (one marker doc per sender's user id), then `query` `toclaude/<uid>/items` (newest first, `status == "sent"`) and `list` `toclaude/<uid>/chunks`, both with the same `out_dir`; run `python3 tools/claude/fbx.py inbox <id> <db_dir> OUTDIR` → `doc.json`, `snapshot.png` (Read it), `info.json` (note, layers, selection, game). Reply by updating the row: `{status:"seen", reply:"..."}`.
- **Draft back:** edit `doc.json` with `fb.js`, render a preview, `fbx.py push-draft doc.json preview.png OUTDIR --title "..." --note "..."`, then send each `writes.json` batch. Duff gets an Open banner; it loads as plain data and undo returns his version.
- **Problems:** `ArtifactData list` collection `diag` for user ids, then `query` `diag/<uid>/log` — each row has kind (`forge`, `send`, `share`, `ai`, `crash`, `promise`…), msg, code, stack, ua, ver, where (`claude` or `site`).

## 7. Checks and waits
- `tools/claude/check.sh` — every test in Chromium, then WebKit (iPhone), then screenshots of the key screens in `/tmp/foxboard-shots` (Read them). `--quick` = Chromium only.
- `python3 tools/claude/shots.py DIR` — just the screenshots.
- `python3 tools/claude/forge_wait.py <job>...` with Bash run_in_background — you get woken when the takes land.
