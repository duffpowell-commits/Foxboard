"""Claude link (Nov 19): Send to Claude (canvas + note into db toclaude/), drafts from Claude (fromclaude/ -> banner -> open),
problem log (local + db diag/), the Claude-side packers (fbx.py push-draft / inbox), forge_wait.py and check.sh."""
import asyncio, base64, io, json, os, pathlib, subprocess, sys, tempfile, time
from playwright.async_api import async_playwright
ROOT = pathlib.Path(__file__).resolve().parent.parent
import functools, http.server, threading
# served over http, not file://: WebKit treats a file:// page as cross-origin to itself and hides every error message
_srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(type('Q', (http.server.SimpleHTTPRequestHandler,), {'log_message': lambda *a: None}), directory=str(ROOT)))
threading.Thread(target=_srv.serve_forever, daemon=True).start()
APP = os.environ.get('APP_URL') or f'http://127.0.0.1:{_srv.server_address[1]}/index.html'
res = []
def check(n, ok, x=''):
    res.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + n + (('  ' + str(x)[:300]) if x != '' else ''))
def g(r, k): return r.get(k) if isinstance(r, dict) else None

MOCK = r"""
(()=>{ const store=new Map(), subs=[]; window.__db=store; window.__failSet=null; let seq=0;
const snap=p=>({exists:store.has(p),id:p.split('/').pop(),data:()=>JSON.parse(JSON.stringify(store.get(p)))});
const inC=(c,p)=>p.startsWith(c+'/')&&p.split('/').length===c.split('/').length+1;
const qd=q=>{ let ps=[...store.keys()].filter(p=>inC(q.c,p)); for(const [f,v] of q.w) ps=ps.filter(p=>store.get(p)[f]===v); let d=ps.map(snap); if(q.o) d.sort((a,b)=>(a.data()[q.o]>b.data()[q.o]?1:-1)*(q.dir==='desc'?-1:1)); return d.slice(0,q.l||1e9); };
const fire=()=>setTimeout(()=>subs.forEach(s=>s()),0);
window.__fire=fire;
const write=(p,v)=>{ if(window.__failSet&&window.__failSet(p)) return Promise.reject({code:'quota_exceeded'}); if(v===undefined) store.delete(p); else store.set(p,JSON.parse(JSON.stringify(v))); fire(); return Promise.resolve(); };
const doc=p=>({set:v=>write(p,v),update:v=>write(p,{...(store.get(p)||{}),...v}),delete:()=>write(p,undefined),get:async()=>snap(p),onSnapshot:fn=>{const s=()=>fn(snap(p));subs.push(s);setTimeout(s,0);return()=>{};}});
const query=q=>({where:(f,_,v)=>query({...q,w:[...q.w,[f,v]]}),orderBy:(o,dir)=>query({...q,o,dir}),limit:l=>query({...q,l}),get:async()=>({docs:qd(q)}),onSnapshot:fn=>{const s=()=>fn({docs:qd(q)});subs.push(s);setTimeout(s,0);return()=>{};},add:v=>write(q.c+'/n'+(++seq),v),doc:id=>doc(q.c+'/'+id)});
window.claude={use:async n=>n==='db'?{doc,collection:c=>query({c,w:[]})}:n==='user'?{isOwner:()=>true,id:async()=>'u_me',can:async()=>true,profiles:async()=>({})}:null};
})();
"""

async def main():
    async with async_playwright() as p:
        eng = os.environ.get('BROWSER', 'chromium')
        b = await getattr(p, eng).launch()
        pg = await b.new_page(viewport={'width': 390, 'height': 844}, has_touch=True)
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)) if 'access control checks' not in str(e) and 'kaboom' not in str(e) else None)
        await pg.add_init_script(MOCK); await pg.goto(APP); await pg.wait_for_timeout(900)
        async def ev(x):
            try: return await pg.evaluate(x)
            except Exception as e: return {'error': str(e)[:160]}
        await ev("""Foxboard.newDoc({w:48,h:32,pixel:true,name:'Knight'}); Foxboard.add('rect',{x:4,y:4,w:20,h:10,fill:'#c2602f',name:'body'}); Foxboard.add('text',{text:'HI',size:8})""")
        # menu entry
        await ev("document.querySelector('#bMenu').click()"); await pg.wait_for_timeout(200)
        check('menu has 📨 Send to Claude', await pg.locator('#shBody button:has-text("Send to Claude")').count() == 1)
        # 1) send
        r = await ev("""(async()=>{ const id=await Foxboard.sendToClaude('make the knight read better'); await new Promise(r=>setTimeout(r,50));
            const m=__db.get('toclaude/u_me/items/'+id); const parts=[...__db.entries()].filter(([k,v])=>k.startsWith('toclaude/u_me/chunks/')&&v.item===id).map(([k,v])=>v).sort((a,b)=>a.n-b.n);
            const d=JSON.parse(parts.map(p=>p.data).join('')); return {status:m.status,note:m.note,png:m.png.slice(0,15),layers:JSON.parse(m.layers).length,chunks:m.chunks,got:parts.length,w:d.w,name:d.name}; })()""")
        check('send: meta + chunks land, status sent', g(r, 'status') == 'sent' and g(r, 'got') == g(r, 'chunks') and g(r, 'w') == 48 and g(r, 'name') == 'Knight', r)
        check('send: note, PNG snapshot and layer list included', g(r, 'note') == 'make the knight read better' and str(g(r, 'png')).startswith('data:image/') and g(r, 'layers') == 2, r)
        r = await ev("""(async()=>{ window.__failSet=p=>p.includes('/chunks/'); let err=null; try{ await Foxboard.sendToClaude('x'); }catch(e){ err=e.code; } window.__failSet=null;
            return {err, left:[...__db.entries()].filter(([k,v])=>(k.includes('/items/')&&v.note==='x')).length}; })()""")
        check('send: a failed upload leaves nothing behind', g(r, 'err') == 'quota_exceeded' and g(r, 'left') == 0, r)
        # sheet lists the send + a reply Claude wrote
        await ev("""(()=>{ const k=[...__db.keys()].find(k=>k.startsWith('toclaude/u_me/items/')); __db.set(k,{...__db.get(k),status:'seen',reply:'Outline it in #14101c and drop to 6 colors.'}); __fire(); })()""")
        await ev("__fb.t.closeSheet(); document.querySelector('#bMenu').click()"); await pg.wait_for_timeout(150)
        try: await pg.click('#shBody button:has-text("Send to Claude")', timeout=2000)
        except Exception: pass
        await pg.wait_for_timeout(250); body = await pg.inner_text('#shBody')
        check('sheet shows Claude\'s reply to a send', 'Outline it in #14101c' in body, body[:200])
        # 3) problem log
        r = await ev("""(async()=>{ Foxboard.report('test','boom one'); Foxboard.report('test','boom one'); const sc=document.createElement('script'); sc.textContent="setTimeout(function(){ throw new Error('kaboom'); },0)"; document.body.append(sc);
            await new Promise(r=>setTimeout(r,120)); const d=[...__db.entries()].filter(([k])=>k.startsWith('diag/u_me/log/')).map(([k,v])=>v);
            return {local:Foxboard.problems().map(x=>x.msg), db:d.map(x=>x.kind+':'+x.msg), ua:!!(d[0]&&d[0].ua)}; })()""")
        check('problem log: kept on the phone', 'boom one' in (g(r, 'local') or []) and 'kaboom' in (g(r, 'local') or []), r)
        check('problem log: reaches db diag/, deduped, with device info', (g(r, 'db') or []).count('test:boom one') == 1 and 'crash:kaboom' in (g(r, 'db') or []) and g(r, 'ua'), r)
        # 2) draft from Claude
        await ev("""(()=>{ const d={name:'Knight v2',w:48,h:32,bg:'transparent',pixel:true,fps:8,cur:0,pages:[{id:'p',objects:[]}]};
            __db.set('fromclaudechunks/dr1_0',{item:'dr1',n:0,data:JSON.stringify(d)}); __db.set('fromclaude/dr1',{title:'Cleaner knight',note:'thinner outline',at:Date.now(),chunks:1}); __fire(); })()""")
        await pg.wait_for_timeout(300)
        bar = await pg.locator('#draftbar').count()
        check('draft: banner shows when Claude sends one', bar == 1 and 'Cleaner knight' in (await pg.inner_text('#draftbar') if bar else ''))
        if bar: await pg.click('#draftbar button:has-text("Open")'); await pg.wait_for_timeout(300)
        name = await ev("__fb.doc.name")
        check('draft: Open loads it as the canvas', name == 'Knight v2', name)
        check('draft: banner goes away once opened', await pg.locator('#draftbar').count() == 0)
        await ev("__fb.undo()"); n2 = await ev("__fb.doc.name")
        check('draft: undo goes back to your canvas', n2 == 'Knight', n2)
        dl = await ev("Foxboard.drafts()")
        check('drafts() lists it as seen', isinstance(dl, list) and bool(dl) and dl[0].get('seen') is True, dl)
        check('no page errors', not errs, errs)
        await b.close()
        # no Claude (iPhone site)
        b = await getattr(p, eng).launch(); pg = await b.new_page(viewport={'width': 390, 'height': 844}, has_touch=True)
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)) if 'access control checks' not in str(e) else None)
        await pg.goto(APP); await pg.wait_for_timeout(700)
        try:
            await pg.evaluate("Foxboard.report('t','local only')"); await pg.evaluate("document.querySelector('#bMenu').click()"); await pg.wait_for_timeout(200)
            await pg.click('#shBody button:has-text("Send to Claude")', timeout=2000); await pg.wait_for_timeout(200)
            body = await pg.inner_text('#shBody')
        except Exception as e: body = str(e)[:100]
        check('no Claude: sheet explains + shows the problem log with Copy', 'inside the Claude app' in body and 'local only' in body and 'Copy log' in body, body[:160])
        check('no page errors (no Claude)', not errs, errs)
        await b.close()

asyncio.run(main())

# Claude-side packers
from PIL import Image
with tempfile.TemporaryDirectory() as td:
    td = pathlib.Path(td)
    doc = {'name': 'Draft', 'w': 32, 'h': 32, 'bg': 'transparent', 'pixel': True, 'fps': 8, 'cur': 0, 'pages': [{'id': 'p', 'objects': [{'id': 'a', 'type': 'text', 'text': 'x' * 400000}]}]}
    (td / 'd.json').write_text(json.dumps(doc)); Image.new('RGBA', (32, 32), (200, 90, 40, 255)).save(td / 'p.png')
    pr = subprocess.run([sys.executable, str(ROOT / 'tools/claude/fbx.py'), 'push-draft', str(td / 'd.json'), str(td / 'p.png'), str(td / 'out'), '--title', 'Cleaner knight', '--note', 'n'], capture_output=True, text=True)
    try:
        w = json.loads((td / 'out/writes.json').read_text()); flat = [x for bt in w['batches'] for x in bt]
        meta = json.loads(pathlib.Path(flat[-1]['file_path']).read_text())
        ok = flat[-1]['collection'] == 'fromclaude' and all(x['collection'] == 'fromclaudechunks' for x in flat[:-1]) and len(flat) - 1 == meta['chunks'] >= 3 and meta['title'] == 'Cleaner knight'
    except Exception as e: ok, meta = False, (pr.stderr or str(e))[-300:]
    check('fbx push-draft: chunks first, fromclaude meta last, title kept', ok, meta if not ok else '')
    # inbox: unpack a Send to Claude item saved by ArtifactData out_dir
    db = td / 'db'; (db / 'toclaude/u_x/items').mkdir(parents=True); (db / 'toclaude/u_x/chunks').mkdir()
    body = json.dumps({'name': 'Knight', 'w': 48, 'h': 32, 'pages': [{'id': 'p', 'objects': []}]}); buf = io.BytesIO(); Image.new('RGB', (48, 32), (1, 2, 3)).save(buf, 'PNG')
    (db / 'toclaude/u_x/items/abc.json').write_text(json.dumps({'id': 'abc', 'version': 3, 'data': {'note': 'fix it', 'name': 'Knight', 'w': 48, 'h': 32, 'chunks': 2, 'layers': '[{"id":"x"}]', 'png': 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode(), 'status': 'sent'}}))
    for n in range(2): (db / f'toclaude/u_x/chunks/abc_{n}.json').write_text(json.dumps({'data': {'item': 'abc', 'n': n, 'data': body[n * 40:(n + 1) * 40] if n == 0 else body[40:]}}))
    pr = subprocess.run([sys.executable, str(ROOT / 'tools/claude/fbx.py'), 'inbox', 'abc', str(db), str(td / 'in')], capture_output=True, text=True)
    ok = (td / 'in/doc.json').exists() and json.loads((td / 'in/doc.json').read_text())['w'] == 48 and (td / 'in/snapshot.png').read_bytes()[:4] == b'\x89PNG' and json.loads((td / 'in/info.json').read_text())['note'] == 'fix it'
    check('fbx inbox: doc + snapshot + note unpacked', ok, (pr.stdout + pr.stderr)[-300:])

# forge_wait: exits when done.json lands; flags a stuck job
with tempfile.TemporaryDirectory() as td:
    td = pathlib.Path(td); bare = td / 'r.git'; wk = td / 'w'
    sh = lambda *a, cwd=None: subprocess.run(list(a), cwd=cwd, capture_output=True, text=True)
    sh('git', 'init', '-q', '--bare', '-b', 'main', str(bare)); sh('git', 'clone', '-q', str(bare), str(wk))
    for c in (['config', 'user.email', 't@t'], ['config', 'user.name', 't']): sh('git', *c, cwd=wk)
    (wk / 'forge/jobs').mkdir(parents=True); now = int(time.time() * 1000)
    (wk / 'forge/jobs/ok1.json').write_text(json.dumps({'w': 512, 'h': 512, 'at': now - 12 * 60_000}))
    (wk / 'forge/jobs/st1.json').write_text(json.dumps({'w': 512, 'h': 512, 'at': now - 3 * 3600_000}))
    sh('git', 'add', '-A', cwd=wk); sh('git', 'commit', '-qm', 'jobs', cwd=wk); sh('git', 'push', '-q', 'origin', 'HEAD:main', cwd=wk)
    sh('git', 'clone', '-q', str(bare), str(td / 'me'))
    pw = subprocess.Popen([sys.executable, str(ROOT / 'tools/claude/forge_wait.py'), 'ok1', '--repo', str(td / 'me'), '--every', '1', '--timeout-min', '1'], stdout=subprocess.PIPE, text=True)
    time.sleep(2); (wk / 'forge/results/ok1').mkdir(parents=True); (wk / 'forge/results/ok1/0.png').write_bytes(b'x'); (wk / 'forge/results/ok1/done.json').write_text('{"ok":[0],"failed":[]}')
    sh('git', 'add', '-A', cwd=wk); sh('git', 'commit', '-qm', 'done', cwd=wk); sh('git', 'push', '-q', 'origin', 'HEAD:main', cwd=wk)
    try: out, _ = pw.communicate(timeout=30)
    except Exception: pw.kill(); out = 'timeout'
    check('forge_wait: exits 0 with the takes when done.json lands', pw.returncode == 0 and '"ok": [0]' in out and '0.png' in out, out[-200:])
    pr = subprocess.run([sys.executable, str(ROOT / 'tools/claude/forge_wait.py'), 'st1', '--repo', str(td / 'me'), '--every', '1', '--timeout-min', '1'], capture_output=True, text=True, timeout=60)
    check('forge_wait: flags a stuck job (exit 2)', pr.returncode == 2 and 'stuck' in pr.stdout, pr.stdout[-200:])

check('check.sh is executable and valid bash', os.access(ROOT / 'tools/claude/check.sh', os.X_OK) and subprocess.run(['bash', '-n', str(ROOT / 'tools/claude/check.sh')]).returncode == 0)
print(f'\n{sum(res)}/{len(res)} passed'); sys.exit(0 if res and all(res) else 1)
