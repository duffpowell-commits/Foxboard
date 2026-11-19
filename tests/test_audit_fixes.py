"""Regression tests for the Nov 19 audit: bible edits survive a live snapshot, a failed template read never
overwrites the cloud list, direct send falls back to the outbox without the GitHub connector, failed uploads
leave no orphan chunks, Forge never double-counts a take, a live note never wipes a draft, palette long-press
removes a color by touch, a pinch never leaves a magic-eraser mark, and template delete needs a second tap."""
import os, asyncio, pathlib
from playwright.async_api import async_playwright
APP = os.environ.get('APP_URL') or (pathlib.Path(__file__).resolve().parent.parent / 'index.html').as_uri()

# In-memory stand-in for the artifact db / user / artifact / mcp capabilities.
MOCK = r"""
(()=>{
const store=new Map(), subs=[]; window.__db=store; window.__published=[]; window.__failSet=null; let seq=0;
const snapDoc=p=>({exists:store.has(p),id:p.split('/').pop(),data:()=>JSON.parse(JSON.stringify(store.get(p)))});
const inColl=(c,p)=>p.startsWith(c+'/')&&p.split('/').length===c.split('/').length+1;
const qdocs=q=>{ let ps=[...store.keys()].filter(p=>inColl(q.c,p)); for(const [f,v] of q.w) ps=ps.filter(p=>store.get(p)[f]===v);
  let ds=ps.map(snapDoc); if(q.o) ds.sort((a,b)=>(a.data()[q.o]>b.data()[q.o]?1:-1)*(q.dir==='desc'?-1:1)); return ds.slice(0,q.l||1e9); };
const fire=()=>setTimeout(()=>subs.forEach(s=>s()),0);
const write=(p,v)=>{ if(window.__failSet&&window.__failSet(p)) return Promise.reject({code:'quota_exceeded'}); if(v===undefined) store.delete(p); else store.set(p,JSON.parse(JSON.stringify(v))); fire(); return Promise.resolve(); };
const doc=p=>({ set:v=>write(p,v), update:v=>write(p,{...(store.get(p)||{}),...v}), delete:()=>write(p,undefined),
  get:async()=>snapDoc(p), onSnapshot:(fn)=>{ const s=()=>fn(snapDoc(p)); subs.push(s); setTimeout(s,0); return ()=>{}; } });
const query=q=>({ where:(f,_,v)=>query({...q,w:[...q.w,[f,v]]}), orderBy:(o,dir)=>query({...q,o,dir}), limit:l=>query({...q,l}),
  get:async()=>({docs:qdocs(q)}), onSnapshot:fn=>{ const s=()=>fn({docs:qdocs(q)}); subs.push(s); setTimeout(s,0); return ()=>{}; },
  add:v=>write(q.c+'/n'+(++seq),v), doc:id=>doc(q.c+'/'+id) });
const db={doc, collection:c=>query({c,w:[]})};
const user={isOwner:()=>true, id:async()=>'u_me', can:async()=>true, profiles:async ids=>Object.fromEntries(ids.map(i=>[i,{name:'Tester'}]))};
const artifact={publish:async f=>{ window.__published.push(f); }};
window.__mcp={ calls:0, listTools:async()=>({}), callTool:async(srv,tool,args)=>{ window.__mcp.calls++; await new Promise(r=>setTimeout(r,60));
  if(/\/\d+\.b64$/.test(args.path)) return {content:[{type:'text',text:'png:'+'A'.repeat(300)}]}; throw {code:'tool_error',message:'404'}; } };
window.__useMcp=true;
window.claude={use:async n=> n==='db'?db : n==='user'?user : n==='artifact'?artifact : n==='mcp'?(window.__useMcp?window.__mcp:null) : null};
})();
"""

results = []
def check(name, ok, extra=''):
    results.append(ok); print(('PASS ' if ok else 'FAIL ') + name + (('  ' + str(extra)) if extra else ''))

async def page(p, mcp=True, local_templates=None):
    b = await getattr(p, os.environ.get('BROWSER', 'chromium')).launch()
    pg = await b.new_page(viewport={'width': 390, 'height': 820}, has_touch=True)
    errs = []; pg.on('pageerror', lambda e: errs.append(str(e)) if 'access control checks' not in str(e) else None)  # WebKit flags the file:// template fetch
    init = MOCK + ('' if mcp else 'window.__useMcp=false;')
    if local_templates is not None:
        init += "try{localStorage.setItem('foxboard.templates',%r);}catch(e){}" % local_templates
    await pg.add_init_script(init)
    await pg.goto(APP); await pg.wait_for_timeout(900)
    return b, pg, errs

async def main():
    async with async_playwright() as p:
        b, pg, errs = await page(p)
        ev = pg.evaluate

        # 1) bible edits survive a snapshot that lands while the sheet is open
        await ev("__fb.openBible(__fb.t.bible.games[0].id)"); await pg.wait_for_timeout(150)
        await pg.locator('#shBody textarea').first.fill('MY NEW SPRITE RULES')
        await ev("""(async()=>{ const b=JSON.parse(JSON.stringify(__fb.t.bible)); b.characters=[...b.characters,{id:'zz',name:'Remote',game:b.games[0].id,look:'x'}];
                     await __fb.t.dbCap.doc('bible/main').set({games:b.games,characters:b.characters,at:1}); })()""")
        await pg.wait_for_timeout(200)
        await pg.click('#shBody button:has-text("Save bible")'); await pg.wait_for_timeout(200)
        saved = await ev("(__db.get('bible/main')||{games:[{}]}).games[0].sprite")
        check('bible: typed sprite text survives a live update + Save', saved == 'MY NEW SPRITE RULES', saved)

        # 7) palette long-press removes a color (touch, no contextmenu)
        await ev("__fb.openBible(__fb.t.bible.games[0].id)"); await pg.wait_for_timeout(150)
        n0 = await ev("__fb.t.gameById(__fb.t.bibleGid||__fb.t.bible.games[0].id).palette.length")
        sw = pg.locator('#shBody .swatches i').first
        bb = await sw.bounding_box()
        await sw.dispatch_event('pointerdown', {'pointerId': 7, 'clientX': bb['x'] + 5, 'clientY': bb['y'] + 5, 'pointerType': 'touch'})
        await pg.wait_for_timeout(750)
        await sw.dispatch_event('pointerup', {'pointerId': 7, 'pointerType': 'touch'}) if await sw.count() else None
        n1 = await ev("__fb.t.gameById(__fb.t.bible.games[0].id).palette.length")
        check('bible: long-press removes a palette color', n1 == n0 - 1, (n0, n1))
        check('palette swatches are at least 36px', bb['width'] >= 36, bb['width'])
        await ev("__fb.t.closeSheet()")

        # 3) direct send with no GitHub connector falls back to the outbox
        b2, pg2, errs2 = await page(p, mcp=False)
        await pg2.evaluate("__fb.t.bible.games.forEach(g=>{ g.direct=true; g.decoder=true; }); __fb.openSendToGame()"); await pg2.wait_for_timeout(200)
        await pg2.click('#shBody button:has-text("Send")'); await pg2.wait_for_timeout(800)
        out = await pg2.inner_text('#shBody .out')
        q = await pg2.evaluate("[...__db.values()].filter(v=>v.status==='queued').length")
        check('direct send without the connector queues to the outbox', q == 1, out[:90])
        check('no page errors (no-connector page)', not errs2, errs2)
        await b2.close()

        # 4) a failed upload leaves no orphan chunks
        r = await ev("""(async()=>{ const g=__fb.t.bible.games[0]; const big=new Blob([new Uint8Array(400000).map((_,i)=>i*7)],{type:'image/png'});
            window.__failSet=p=>p.startsWith('outboxchunks/')&&p.endsWith('_1');
            let err=null; try{ await __fb.t.queueOutbox(g,'x','png',big,'grok_art/2026-01-01-foxboard','x.png'); }catch(e){ err=e.code; }
            window.__failSet=null;
            return {err, chunks:[...__db.keys()].filter(k=>k.startsWith('outboxchunks/')).length,
                    stuck:[...__db.entries()].filter(([k,v])=>k.startsWith('outbox/')&&v.status!=='queued'&&v.status!=='delivered').length,
                    queued:[...__db.entries()].filter(([k,v])=>k.startsWith('outbox/')&&v.name==='x'&&v.status==='queued').length}; })()""")
        check('outbox: failed upload leaves no chunks and nothing queued', r['err'] == 'quota_exceeded' and r['chunks'] == 0 and r['queued'] == 0, r)
        r = await ev("""(async()=>{ const id=await __fb.t.queueOutbox(__fb.t.bible.games[0],'ok','png',new Blob([new Uint8Array(10)]),'grok_art/2026-01-01-foxboard','ok.png');
            return __db.get('outbox/'+id).status; })()""")
        check('outbox: a good upload ends up queued', r == 'queued', r)

        # 5) Forge: two checks at once never double-count a take
        r = await ev("""(async()=>{ const j={id:'dup',n:2,w:512,h:512,at:Date.now(),got:[],state:'rendering'};
            await Promise.all([__fb.forgeCheck(j),__fb.forgeCheck(j)]); return j.got; })()""")
        check('forge: concurrent checks give each take once', sorted(r) == [0, 1] and len(r) == 2, r)

        # 6) a live note never wipes a note being typed
        await ev("""__db.set('library/it1',{name:'Art',w:8,h:8,frames:1,by:'u_other',at:5,thumb:'',chunks:0})""")
        await ev("__fb.t.dbCap.doc('library/it1').set(__db.get('library/it1'))"); await pg.wait_for_timeout(200)
        await ev("__fb.t.openLibItem('it1')"); await pg.wait_for_timeout(150)
        ta = pg.locator('#shBody textarea'); await ta.fill('half-typed note')
        await ev("__fb.t.dbCap.collection('libnotes').add({item:'it1',text:'someone else',by:'u_other',at:Date.now()})"); await pg.wait_for_timeout(300)
        val = await pg.locator('#shBody textarea').input_value()
        shown = await pg.inner_text('#shBody')
        check('library: live note keeps the draft', val == 'half-typed note', val)
        check('library: the new note shows up', 'someone else' in shown)
        await ev("__fb.t.closeSheet()")

        # 9) template delete needs a second tap
        await ev("""__fb.t.myTemplates=[{id:'t1',name:'Keep me',w:8,h:8,doc:JSON.parse(JSON.stringify({...__fb.doc,cur:0}))}]; __fb.t.openNew()""")
        await pg.wait_for_timeout(200)
        d = pg.locator('#shBody button[aria-label="Delete template"], #shBody .preset button.danger').first
        await d.click(); await pg.wait_for_timeout(150)
        one = await ev("__fb.t.myTemplates.length")
        check('templates: one tap does not delete', one == 1, one)
        await ev("__fb.t.closeSheet()")
        check('no page errors', not errs, errs)
        await b.close()

        # 2) a failed cloud read never publishes over the cloud list
        b3, pg3, errs3 = await page(p, local_templates='[{"id":"a","name":"Local only","doc":{"w":8,"h":8,"pages":[]}}]')
        r = await pg3.evaluate("(async()=>{ await new Promise(r=>setTimeout(r,300)); const w=await __fb.t.persistTemplates(); return {w, published:__published.length}; })()")
        check('templates: unreadable cloud list is never overwritten', r['published'] == 0, r)
        await b3.close()

        # 8) a pinch in the magic eraser leaves no mask mark
        b4, pg4, errs4 = await page(p)
        await pg4.evaluate("""(async()=>{ const c=document.createElement('canvas'); c.width=c.height=64; const g=c.getContext('2d'); g.fillStyle='#456'; g.fillRect(0,0,64,64);
            __fb.doc={w:64,h:64,bg:'#000000',pixel:false,fps:8,cur:0,pages:[{id:'p1',objects:[{id:'im',type:'image',x:0,y:0,w:64,h:64,rot:0,opacity:1,src:c.toDataURL(),natW:64,natH:64,hidden:false,locked:false}]}]};
            await new Promise(r=>setTimeout(r,250)); __fb.sel='im'; __fb.fit(); })()""")
        await pg4.wait_for_timeout(300); await pg4.evaluate("__fb.openProps()"); await pg4.wait_for_timeout(200)
        await pg4.click('#shBody button:has-text("Magic eraser")'); await pg4.wait_for_timeout(250)
        st = await pg4.locator('#stage').bounding_box(); v = await pg4.evaluate("__fb.view")
        x, y = st['x'] + v['x'] + 32 * v['z'], st['y'] + v['y'] + 32 * v['z']
        for pid, dx in ((1, 0), (2, 60)):
            await pg4.locator('#cv').dispatch_event('pointerdown', {'pointerId': pid, 'clientX': x + dx, 'clientY': y, 'pointerType': 'touch', 'isPrimary': pid == 1})
        for pid in (1, 2):
            await pg4.locator('#cv').dispatch_event('pointerup', {'pointerId': pid, 'clientX': x, 'clientY': y, 'pointerType': 'touch'})
        painted = await pg4.evaluate("(()=>{ const m=__fb.t.magic&&__fb.t.magic.mask; if(!m) return -1; const d=m.getContext('2d').getImageData(0,0,m.width,m.height).data; let n=0; for(let i=3;i<d.length;i+=4) if(d[i]) n++; return n; })()")
        check('magic eraser: a pinch leaves no stray mask mark', painted == 0, painted)
        await b4.close()

    print(f'\n{sum(results)}/{len(results)} passed')
    raise SystemExit(0 if all(results) else 1)

asyncio.run(main())
