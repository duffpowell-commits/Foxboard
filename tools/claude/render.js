// Render a Foxboard doc with Foxboard's own renderer: node render.js doc.json out [scale] -> out_<page>.png
const fs = require('fs'), path = require('path');
let pw; try { pw = require('playwright'); } catch (e) { pw = require(path.join(require('child_process').execSync('npm root -g').toString().trim(), 'playwright')); }
const { chromium } = pw;
(async () => {
  const [docPath, outBase, scaleArg] = process.argv.slice(2);
  if (!docPath || !outBase) { console.error('usage: node render.js doc.json out [scale]'); process.exit(2); }
  const doc = JSON.parse(fs.readFileSync(docPath, 'utf8')), scale = +scaleArg || 1;
  const browser = await chromium.launch(); const page = await browser.newPage();
  await page.goto('file://' + path.resolve(__dirname, '../../index.html'));
  await page.waitForFunction(() => window.__fb);
  const pngs = await page.evaluate(async ({ doc, scale }) => {
    window.__fb.doc = doc;
    const srcs = [...new Set(doc.pages.flatMap(p => p.objects.filter(o => o.type === 'image').map(o => o.src)))];
    await Promise.all(srcs.map(s => new Promise(r => { const i = new Image(); i.onload = i.onerror = r; i.src = s; })));
    try { await document.fonts.ready; } catch (e) {}
    await new Promise(r => setTimeout(r, 300));
    return doc.pages.map((_, i) => window.__fb.renderToCanvas(scale, false, i).toDataURL('image/png'));
  }, { doc, scale });
  pngs.forEach((u, i) => fs.writeFileSync(`${outBase}_${i}.png`, Buffer.from(u.split(',')[1], 'base64')));
  console.log(pngs.map((_, i) => `${outBase}_${i}.png`).join('\n'));
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
