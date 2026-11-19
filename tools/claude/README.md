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
Then `git add forge/jobs && git commit && git push`. The workflow renders it in about 5–15 minutes on free runners, and results land in `forge/results/<id>/`. Pass `jid` to choose the id. Only `<id>.json` triggers a render, and the input files are pushed in the same commit.

## 4. The shared library (Duff's phone sees it)
Use the artifact db tools on artifact `408d3d4e-8800-4a0e-9cdc-1251d2b400a7`. `library/<id>` holds each piece's meta and `libchunks/<id>_<n>` holds its body. `fbx.py push-doc` / `pull` do the packing. Never overwrite or delete what Duff made. Push new items.
