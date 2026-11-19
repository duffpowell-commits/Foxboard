"""Send to game, style bible and shared library, against fake GitHub / db / user / Claude.

Run: python tests/test_pipeline.py [path/to/index.html]
Prints PASS/FAIL per check and exits non-zero on any failure.
"""
import asyncio, base64, io, json, pathlib, sys
from playwright.async_api import async_playwright
from PIL import Image

APP = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else pathlib.Path(__file__).resolve().parent.parent / 'index.html').resolve().as_uri()

MOCK = r"""
window.__calls=[]; window.__prompts=[]; window.__fail404=false;
const store=new Map(); const subs=[];
function fire(){ for(const s of subs) s(); }
function snapDoc(path){ const v=store.get(path); return {id:path.split('/').pop(),exists:!!v,data:()=>v&&JSON.parse(JSON.stringify(v)),metadata:{fromCache:false,hasPendingWrites:false}}; }
function query(col,filters=[],ord=null,lim=1000){
  const q={
    where:(f,op,v)=>query(col,[...filters,[f,op,v]],ord,lim),
    orderBy:(f,d)=>query(col,filters,[f,d||'asc'],lim),
    limit:n=>query(col,filters,ord,n),
    async get(){ return run(); },
    onSnapshot(next,err){ const f=()=>next(run()); subs.push(f); setTimeout(f,0); return ()=>{}; },
    doc:id=>docRef(col+'/'+(id||Math.random().toString(36).slice(2))),
    async add(d){ const r=docRef(col+'/'+Math.random().toString(36).slice(2)); await r.set(d); return r; }
  };
  function run(){ let docs=[...store.keys()].filter(k=>k.startsWith(col+'/')&&k.split('/').length===col.split('/').length+1).map(snapDoc);
    for(const [f,op,v] of filters) docs=docs.filter(d=>op==='=='?d.data()[f]===v:true);
    if(ord) docs.sort((a,b)=>(a.data()[ord[0]]>b.data()[ord[0]]?1:-1)*(ord[1]==='desc'?-1:1));
    docs=docs.slice(0,lim); return {docs,size:docs.length,empty:!docs.length,docChanges:()=>[],metadata:{fromCache:false,hasPendingWrites:false}}; }
  return q;
}
function docRef(path){ return {id:path.split('/').pop(),path,
  async get(){ return snapDoc(path); },
  async set(d){ if(JSON.stringify(d).length>262144) throw {code:'invalid_argument',message:'too big'}; store.set(path,JSON.parse(JSON.stringify(d))); setTimeout(fire,0); },
  async update(d){ store.set(path,{...store.get(path),...d}); setTimeout(fire,0); },
  async delete(){ store.delete(path); setTimeout(fire,0); },
  onSnapshot(next){ const f=()=>next(snapDoc(path)); subs.push(f); setTimeout(f,0); return ()=>{}; } }; }
window.__store=store;
const db={doc:docRef,collection:p=>query(p)};
const mcp={ async listTools(){ return {servers:[{server:'github',authStatus:'connected',tools:[]}],fileArgs:true}; },
  async callTool(server,tool,input){ window.__calls.push({server,tool,input}); if(window.__fail404) throw {code:'tool_error',message:'failed to create/update file: PUT https://api.github.com/... 404 Not Found []'};
    if(tool==='get_file_contents'){ if(window.__forgeReady && /\/(0|1)\.b64$/.test(input.path)) return {content:[{type:'text',text:'[Resource from github at repo://x/contents/'+input.path+'] png:'+window.__forgePNG}],payload:'png:'+window.__forgePNG}; throw {code:'tool_error',message:'404 Not Found'}; }
    return {content:[],payload:{}}; } };
const user={ isOwner:()=>true, canEdit:()=>true, async can(){ return true; }, async id(){ return 'u_duff'; }, async me(){ return {id:'u_duff'}; }, async profiles(ids){ const o={}; ids.forEach(i=>o[i]={name:i==='u_britt'?'Brittany':'Duff'}); return o; } };
const N=16; const rows=[]; for(let y=0;y<N;y++){ let r=''; for(let x=0;x<N;x++) r+=(x>3&&x<12&&y>3&&y<12)?'0':'.'; rows.push(r); }
const sample=async(input,opts={})=>{ window.__prompts.push(String(input)); const t='ok'; opts.onText&&opts.onText({text:t,delta:t}); return {text:t,truncated:false}; };
sample.json=async(input)=>{ window.__prompts.push(String(input)); return {palette:['#ff0000'],rows}; };
sample.limits=async()=>({maxPromptBytes:262144});
window.claude={use:async n=>({db,mcp,user,sample,downloads:{save:async()=>({status:'saved'})}})[n]||null};
"""

results = []
def check(name, ok, info=''):
    results.append(ok)
    print(('PASS ' if ok else 'FAIL ') + name + (('  ' + str(info)) if info and not ok else ''))

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={'width': 390, 'height': 820})
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.add_init_script(MOCK)
        await pg.goto(APP); await pg.wait_for_timeout(900)
        ev = pg.evaluate
        has = await ev("typeof window.__fb!=='undefined'")
        # 16x16 pixel doc with an amber rect on transparent
        await ev("""(()=>{ const d=__fb.doc; d.w=16; d.h=16; d.pixel=true; d.bg='transparent'; d.name='bearer test';
          d.pages=[{id:'p',objects:[{id:'r',type:'rect',x:4,y:4,w:8,h:8,rot:0,fill:'#c98a2e',stroke:'#000',strokeW:0,opacity:1}]}]; __fb.doc=d; })()""")

        # --- send to game: outbox (default) ---
        ok = await ev("typeof __fb.openSendToGame==='function'")
        check('send-to-game exists', ok)
        if ok:
            await ev("__fb.setActiveGame('lethemoor'); __fb.openSendToGame()"); await pg.wait_for_timeout(200)
            await pg.click('button:has-text("Send")'); await pg.wait_for_timeout(900)
            msg = await pg.inner_text('#shBody .out')
            ob = await ev("""(()=>{ const ks=[...window.__store.keys()].filter(k=>k.startsWith('outbox/')); return ks.map(k=>window.__store.get(k)); })()""")
            check('queued one outbox item', len(ob) == 1 and 'Queued' in msg, [msg, ob])
            if ob:
                it = ob[0]
                check('outbox item points at the lethemoor inbox', it['repo'] == 'duffpowell-commits/lethemoor' and it['dir'].startswith('grok_art/') and it['dir'].endswith('-foxboard') and it['file'].endswith('.png') and it['status'] == 'queued', it)
                b64 = await ev("""(id=>{ const ks=[...window.__store.keys()].filter(k=>k.startsWith('outboxchunks/')).sort(); return ks.map(k=>window.__store.get(k)).filter(c=>c.item===id).sort((a,b)=>a.n-b.n).map(c=>c.data).join(''); })""" + "('" + [k for k in await ev("[...window.__store.keys()]") if k.startswith('outbox/')][0].split('/')[1] + "')")
                raw = base64.b64decode(b64)
                import hashlib
                check('chunks rebuild the exact bytes (sha256)', hashlib.sha256(raw).hexdigest() == it['sha256'], (hashlib.sha256(raw).hexdigest(), it['sha256']))
                im = Image.open(io.BytesIO(raw)).convert('RGBA')
                check('flattened on the #00FF00 key', im.getpixel((0, 0)) == (0, 255, 0, 255), im.getpixel((0, 0)))
                check('art kept', im.getpixel((6, 6)) == (201, 138, 46, 255), im.getpixel((6, 6)))
            check('no connector call on the outbox path', await ev("window.__calls.length") == 0)
            # DuffQuest works through the outbox too (no decoder needed)
            await ev("__fb.setActiveGame('duffquest'); __fb.openSendToGame()"); await pg.wait_for_timeout(200)
            await pg.click('button:has-text("Send")'); await pg.wait_for_timeout(900)
            n = await ev("[...window.__store.keys()].filter(k=>k.startsWith('outbox/')).length")
            check('duffquest queues through the outbox', n == 2, n)
            await pg.click('#shClose')
            # direct mode: connector call, and a 404 falls back to the outbox
            await ev("__fb.setDirect('lethemoor',true); window.__calls=[]; __fb.setActiveGame('lethemoor'); __fb.openSendToGame()"); await pg.wait_for_timeout(200)
            await pg.click('button:has-text("Send")'); await pg.wait_for_timeout(700)
            calls = await ev("window.__calls.map(c=>({server:c.server,tool:c.tool,repo:c.input.repo,path:c.input.path,file:!!(c.input.content&&c.input.content.$file)}))")
            check('direct mode commits through github connector', len(calls) == 1 and calls[0]['tool'] == 'create_or_update_file' and calls[0]['path'].endswith('.png.b64') and calls[0]['file'], calls)
            await ev("window.__calls=[]; window.__fail404=true"); await pg.click('button:has-text("Send")'); await pg.wait_for_timeout(1000)
            msg = await pg.inner_text('#shBody .out')
            n = await ev("[...window.__store.keys()].filter(k=>k.startsWith('outbox/')).length")
            check('404 in direct mode falls back to the outbox', n == 3 and 'outbox' in msg, [n, msg])
            await ev("window.__fail404=false; __fb.setDirect('lethemoor',false)"); await pg.click('#shClose')

        # --- style bible: AI prompt carries character + palette ---
        ok = await ev("typeof __fb.openBible==='function'")
        check('style bible exists', ok)
        if ok:
            await ev("__fb.setActiveGame('duffquest'); __fb.openAI('pixel')"); await pg.wait_for_timeout(300)
            await pg.select_option('#shBody select >> nth=1', 'duff')
            await pg.click('button:has-text("Generate")'); await pg.wait_for_timeout(600)
            pr = await ev("window.__prompts.slice(-1)[0]||''")
            check('pixel prompt has the character look', 'blackout sleeve' in pr and 'fox' in pr, pr[:200])
            check('pixel prompt has the game palette', '#E0A030' in pr, pr[:200])
            check('prompt keeps the originality rule', 'ORIGINAL' in pr)
            await pg.click('#shClose')
            # snap to palette
            r = await ev("""(async()=>{ const c=document.createElement('canvas'); c.width=4; c.height=4; const g=c.getContext('2d'); g.fillStyle='#d0902a'; g.fillRect(0,0,4,4);
              const d=__fb.doc; d.pages[0].objects.push({id:'im',type:'image',x:0,y:0,w:4,h:4,rot:0,opacity:1,src:c.toDataURL('image/png'),natW:4,natH:4}); __fb.doc=d;
              await new Promise(r=>setTimeout(r,250)); const o=__fb.doc.pages[0].objects.find(o=>o.id==='im'); __fb.snapToPalette(o,['#000000','#E0A030']);
              await new Promise(r=>setTimeout(r,250)); const im=new Image(); im.src=__fb.doc.pages[0].objects.find(o=>o.id==='im').src; await im.decode();
              const k=document.createElement('canvas'); k.width=4; k.height=4; const kg=k.getContext('2d'); kg.drawImage(im,0,0); return Array.from(kg.getImageData(1,1,1,1).data); })()""")
            check('snap to palette maps to nearest palette color', r == [224, 160, 48, 255], r)

        # --- shared library ---
        ok = await ev("typeof __fb.openLibrary==='function'")
        check('shared library exists', ok)
        if ok:
            await ev("__fb.openLibrary()"); await pg.wait_for_timeout(200)
            await pg.click('button:has-text("Share this canvas")'); await pg.wait_for_timeout(800)
            keys = await ev("[...window.__store.keys()]")
            check('share writes item + chunks', any(k.startswith('library/') for k in keys) and any(k.startswith('libchunks/') for k in keys), keys)
            await ev("__fb.openLibrary()"); await pg.wait_for_timeout(300)
            txt = await pg.inner_text('#shBody')
            check('library lists it by you', 'bearer test' in txt and 'you' in txt, txt[:200])
            await pg.click('#shBody button.preset >> nth=0'); await pg.wait_for_timeout(200)
            await pg.fill('#shBody textarea', 'face reads too dark'); await pg.click('button:has-text("Add note")'); await pg.wait_for_timeout(500)
            txt = await pg.inner_text('#shBody')
            check('note shows on the item', 'face reads too dark' in txt, txt[:300])
            n0 = await ev("__fb.doc.pages[0].objects.length")
            await ev("__fb.startNew(8,8,true,'blank')"); await pg.wait_for_timeout(100)
            await ev("__fb.openLibrary()"); await pg.wait_for_timeout(200)
            await pg.click('#shBody button.preset >> nth=0'); await pg.wait_for_timeout(200)
            await pg.click('button:has-text("Open a copy")'); await pg.wait_for_timeout(600)
            st = await ev("({n:__fb.doc.pages[0].objects.length,w:__fb.doc.w,name:__fb.doc.name})")
            check('open a copy restores the canvas', st['n'] == n0 and st['w'] == 16, st)
            # big canvas splits into chunks under the 256 KiB doc limit
            r = await ev("""(async()=>{ const d=__fb.doc; const big='x'.repeat(600000); d.pages[0].objects.push({id:'bg',type:'text',text:big.slice(0,10),x:0,y:0,w:1,h:1,font:'sans-serif',size:4,fill:'#fff',stroke:'#000',strokeW:0,pad:big}); __fb.doc=d;
              const b=document.createElement('button'); await __fb.shareCanvas(b); await new Promise(r=>setTimeout(r,300));
              return [...window.__store.keys()].filter(k=>k.startsWith('libchunks/')).length; })()""")
            check('big canvas chunks under the db doc limit', r >= 4, r)

        # --- Forge ---
        ok = await ev("typeof __fb.forgeCheck==='function'")
        check('forge exists', ok)
        if ok:
            await ev("""(()=>{ const c=document.createElement('canvas'); c.width=40; c.height=40; const g=c.getContext('2d'); g.fillStyle='#ff00ff'; g.fillRect(0,0,40,40); g.fillStyle='#123456'; g.fillRect(10,10,20,20); window.__forgePNG=c.toDataURL('image/png').split(',')[1]; window.__calls=[]; })()""")
            await ev("__fb.setActiveGame('duffquest'); __fb.openAI('forge')"); await pg.wait_for_timeout(300)
            await pg.fill('#shBody textarea', 'a gothic bell tower at dawn')
            await pg.select_option('#shBody select >> nth=1', 'duff')
            await pg.click('button:has-text("Flat key background")')
            await pg.click('button:has-text("Queue it")'); await pg.wait_for_timeout(500)
            calls = await ev("window.__calls.filter(c=>c.tool==='create_or_update_file').map(c=>({repo:c.input.repo,owner:c.input.owner,path:c.input.path,branch:c.input.branch,content:c.input.content}))")
            check('forge queues one job file in Foxboard/forge/jobs', len(calls) == 1 and calls[0]['repo'] == 'Foxboard' and calls[0]['path'].startswith('forge/jobs/') and calls[0]['path'].endswith('.json') and calls[0]['branch'] == 'main', calls)
            if calls:
                job = json.loads(calls[0]['content'])
                check('job carries prompt, character look, style and key bg', 'bell tower' in job['prompt'] and 'blackout' in job['prompt'] and 'flat' in job['prompt'].lower() and job['key'] == '#FF00FF' and job['n'] == 2 and job['w'] == 768, job)
            jobs = await ev("__fb.forgeJobs.length")
            check('job listed in the app', jobs >= 1, jobs)
            await ev("window.__forgeReady=true")
            await pg.click('button:has-text("Check now")'); await pg.wait_for_timeout(800)
            got = await ev("__fb.forgeJobs[0].got")
            check('check pulls both finished versions', got == [0, 1], got)
            n0 = await ev("__fb.doc.pages[__fb.doc.cur].objects.length")
            await pg.click('#shBody img >> nth=0'); await pg.wait_for_timeout(700)
            n1 = await ev("__fb.doc.pages[__fb.doc.cur].objects.length")
            px = await ev("""(async()=>{ const o=__fb.doc.pages[__fb.doc.cur].objects.slice(-1)[0]; const im=new Image(); im.src=o.src; await im.decode(); const c=document.createElement('canvas'); c.width=im.width; c.height=im.height; const g=c.getContext('2d'); g.drawImage(im,0,0); return [o.name, Array.from(g.getImageData(20,20,1,1).data)]; })()""")
            check('tapping a result adds it as a layer', n1 == n0 + 1 and px[0].startswith('Forge') and px[1][:3] == [18, 52, 86], [n0, n1, px])

        check('no page errors', not errs, errs)
        await b.close()
    print(f"\n{sum(results)}/{len(results)} passed")
    sys.exit(0 if all(results) else 1)

if __name__=="__main__": asyncio.run(main())
