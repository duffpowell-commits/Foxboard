#!/usr/bin/env python3
"""390x844 screenshots of Foxboard's key screens, Chromium + WebKit, with a mocked Claude (db, GitHub, sample).
  python3 tools/claude/shots.py [OUTDIR]   -> OUTDIR/<engine>_<screen>.png  (Claude can Read the PNGs to look)"""
import asyncio, os, pathlib, sys
from playwright.async_api import async_playwright
ROOT = pathlib.Path(__file__).resolve().parents[2]; APP = os.environ.get('APP_URL') or (ROOT / 'index.html').as_uri()
OUT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else '/tmp/foxboard-shots'); OUT.mkdir(parents=True, exist_ok=True)
MOCK = r"""(()=>{ const store=new Map(), subs=[];
const snap=p=>({exists:store.has(p),id:p.split('/').pop(),data:()=>JSON.parse(JSON.stringify(store.get(p)))});
const docs=c=>[...store.keys()].filter(p=>p.startsWith(c+'/')&&p.split('/').length===c.split('/').length+1).map(snap);
const doc=p=>({set:async v=>{store.set(p,v);subs.forEach(f=>f());},update:async v=>{store.set(p,{...(store.get(p)||{}),...v});subs.forEach(f=>f());},delete:async()=>{store.delete(p);},get:async()=>snap(p),onSnapshot:fn=>{const s=()=>fn(snap(p));subs.push(s);setTimeout(s,0);}});
const q=c=>({where:()=>q(c),orderBy:()=>q(c),limit:()=>q(c),get:async()=>({docs:docs(c)}),onSnapshot:fn=>{const s=()=>fn({docs:docs(c)});subs.push(s);setTimeout(s,0);},add:async v=>doc(c+'/'+Math.random().toString(36).slice(2)).set(v)});
store.set('fromclaude/d1',{title:'Knight, cleaner outline',note:'Thinner outline, 2 fewer colors',at:Date.now(),chunks:1});
const sample=async()=>({text:'ok'}); sample.json=async()=>({}); sample.limits=async()=>({});
window.claude={use:async n=>n==='db'?{doc,collection:q}:n==='user'?{isOwner:()=>true,id:async()=>'u_me',can:async()=>true,profiles:async()=>({})}:n==='mcp'?{listTools:async()=>({}),callTool:async()=>({content:[]})}:n==='sample'?sample:null};})();"""
SETUP = """Foxboard.newDoc({w:64,h:64,pixel:true,name:'Knight'}); const c=document.createElement('canvas'); c.width=c.height=64; const g=c.getContext('2d');
g.fillStyle='#8a97ab'; g.fillRect(22,14,20,30); g.fillStyle='#c2602f'; g.fillRect(20,40,24,14); g.fillStyle='#f0a040'; g.fillRect(28,20,8,4);
__fb.sel=Foxboard.add('image',{src:c.toDataURL(),x:0,y:0,w:64,h:64});"""
SCREENS = [('canvas', ''), ('menu', "document.querySelector('#bMenu').click()"), ('forge', "__fb.openAI('forge')"),
           ('image_panel', "__fb.openProps()"), ('send_to_claude', "openClaudeLink ? 0 : 0"), ('bible', "__fb.openBible()"), ('library', "__fb.openLibrary()")]
async def main():
    async with async_playwright() as p:
        for eng in ('chromium', 'webkit'):
            try: b = await getattr(p, eng).launch()
            except Exception as e: print('skip', eng, str(e)[:80]); continue
            for mocked in (True, False):
                pg = await b.new_page(viewport={'width': 390, 'height': 844}, device_scale_factor=1, has_touch=True)
                errs = []; pg.on('pageerror', lambda e: errs.append(str(e)) if 'access control' not in str(e) else None)
                if mocked: await pg.add_init_script(MOCK)
                await pg.goto(APP); await pg.wait_for_timeout(900); await pg.evaluate(SETUP); await pg.wait_for_timeout(300)
                for name, js in SCREENS if mocked else SCREENS[:4]:
                    try:
                        await pg.evaluate("__fb.t.closeSheet()")
                        if name == 'send_to_claude': await pg.evaluate("document.querySelector('#bMenu').click()"); await pg.wait_for_timeout(200); await pg.click('#shBody button:has-text("Send to Claude")')
                        elif js: await pg.evaluate(js)
                        await pg.wait_for_timeout(350)
                        await pg.screenshot(path=str(OUT / f"{eng}_{'' if mocked else 'noclaude_'}{name}.png"))
                    except Exception as e: print('!', eng, name, str(e)[:100])
                if errs: print('page errors', eng, errs[:3])
                await pg.close()
            await b.close()
    print(len(list(OUT.glob('*.png'))), 'screenshots in', OUT)
asyncio.run(main())
