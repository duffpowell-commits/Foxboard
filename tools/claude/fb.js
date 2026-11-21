// Drive every Foxboard feature headlessly through the app's own code (window.Foxboard).
//   node tools/claude/fb.js <script.js> [--doc in.json] [--out doc.json] [--png prefix] [--scale n] [--files dir]
// script.js is the body of an async function with: F (= window.Foxboard), save(blob|dataURL, name), log(...)
//   e.g.  const t = F.add('text',{text:'Hi',size:80}); F.set(t,{curve:40,shadow:{c:'#000',a:.6,blur:12,x:4,y:4}});
//         await save(await F.exportFile('pdf'), 'card.pdf');
// Forge from Claude: const r = F.forgeFiles({mode:'edit', id, mask:{rects:[[x,y,w,h]]}, prompt:'...'}); await saveForge(r);
//   Also: mode:'new', refCanvas/refSrc, refStrength (style-board workaround); mode:'sketch' + initCanvas; tile, seed, strength, w, h.
//   Jobs must land on Foxboard main to render. Prefer tools/claude/art_loop.py queue.
//   -> writes r.files into the repo (forge/jobs/...); commit + push them with git and the runners pick them up.
// Prints the script's return value as JSON. --out writes the doc (with images) for fbx.py push-doc.
const fs = require('fs'), path = require('path');
let pw; try { pw = require('playwright'); } catch (e) { pw = require(path.join(require('child_process').execSync('npm root -g').toString().trim(), 'playwright')); }
const args = process.argv.slice(2), opt = {}; const pos = [];
for (let i = 0; i < args.length; i++) { if (args[i].startsWith('--')) opt[args[i].slice(2)] = args[++i]; else pos.push(args[i]); }
if (!pos[0]) { console.error('usage: node fb.js script.js [--doc in.json] [--out doc.json] [--png prefix] [--scale n] [--files dir]'); process.exit(2); }
const REPO = path.resolve(__dirname, '../..');
(async () => {
  const body = fs.readFileSync(pos[0], 'utf8'), filesDir = path.resolve(opt.files || '.');
  const browser = await pw.chromium.launch(); const page = await browser.newPage({ viewport: { width: 390, height: 820 } });
  const errors = []; page.on('pageerror', e => errors.push(String(e)));
  await page.goto('file://' + path.join(REPO, 'index.html'));
  await page.waitForFunction(() => window.Foxboard && window.__fb);
  await page.exposeFunction('__save', (name, b64) => { const p = path.join(filesDir, name); fs.mkdirSync(path.dirname(p), { recursive: true }); fs.writeFileSync(p, Buffer.from(b64, 'base64')); return p; });
  await page.exposeFunction('__saveForge', files => { const out = []; for (const [rel, content] of Object.entries(files)) { if (!/^forge\/jobs\/[A-Za-z0-9_.-]+$/.test(rel)) throw new Error('bad path ' + rel); const p = path.join(REPO, rel); fs.writeFileSync(p, content); out.push(rel); } return out; });
  if (opt.doc) { const d = JSON.parse(fs.readFileSync(opt.doc, 'utf8')); await page.evaluate(async d => { Foxboard.load(d.doc || d); const srcs = [...new Set(Foxboard.doc().pages.flatMap(p => p.objects.filter(o => o.type === 'image').map(o => o.src)))]; await Promise.all(srcs.map(s => new Promise(r => { const i = new Image(); i.onload = i.onerror = r; i.src = s; }))); }, d); }
  const result = await page.evaluate(async body => {
    const F = window.Foxboard, logs = [];
    const log = (...a) => logs.push(a.map(x => typeof x === 'string' ? x : JSON.stringify(x)).join(' '));
    const toB64 = async x => { if (typeof x === 'string') return x.split(',')[1]; const b = new Uint8Array(await x.arrayBuffer()); let s = ''; for (let i = 0; i < b.length; i += 32768) s += String.fromCharCode.apply(null, b.subarray(i, i + 32768)); return btoa(s); };
    const save = async (x, name) => window.__save(name, await toB64(x));
    const saveForge = async r => window.__saveForge(r.files);
    const wait = ms => new Promise(r => setTimeout(r, ms));
    const loaded = async () => { const srcs = [...new Set(F.doc().pages.flatMap(p => p.objects.filter(o => o.type === 'image').map(o => o.src)))]; await Promise.all(srcs.map(s => new Promise(r => { const i = new Image(); i.onload = i.onerror = r; i.src = s; }))); try { await document.fonts.ready; } catch (e) {} await wait(150); };
    const fn = new Function('F', 'save', 'saveForge', 'log', 'wait', 'loaded', `return (async()=>{ ${body} })();`);
    let ret; try { ret = await fn(F, save, saveForge, log, wait, loaded); } catch (e) { return { error: String(e && e.message || e), logs }; }
    await loaded();
    return { ret, logs };
  }, body);
  if (opt.out) { const d = await page.evaluate(() => Foxboard.doc()); fs.writeFileSync(opt.out, JSON.stringify(d)); }
  if (opt.png) {
    const urls = await page.evaluate(sc => Foxboard.doc().pages.map((_, i) => Foxboard.render(sc, i)), +opt.scale || 1);
    urls.forEach((u, i) => fs.writeFileSync(`${opt.png}_${i}.png`, Buffer.from(u.split(',')[1], 'base64')));
    result.pngs = urls.map((_, i) => `${opt.png}_${i}.png`);
  }
  if (errors.length) result.pageErrors = errors;
  console.log(JSON.stringify(result, null, 1));
  await browser.close();
  process.exit(result.error ? 1 : 0);
})().catch(e => { console.error(e); process.exit(1); });
