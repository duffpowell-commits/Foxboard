"""Creative features (Nov 19): sketch -> art, variations + seed lock, seamless tiles, pixelate, prompt boost,
new background, take gallery/favorites, sticker outline, before/after compare. Browser checks run the page with a
mocked Claude (GitHub connector + sample); the Forge render command is checked with render_one.py's dry run."""
import base64, io, json, os, pathlib, subprocess, sys, tempfile, asyncio
from playwright.async_api import async_playwright
ROOT = pathlib.Path(__file__).resolve().parent.parent
APP = os.environ.get('APP_URL') or (ROOT / 'index.html').as_uri()

res = []
def g(r, k):
    return r.get(k) if isinstance(r, dict) else None
def check(n, ok, x=''):
    res.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + n + (('  ' + str(x)) if x != '' else ''))

# a real PNG to stand in for a finished Forge take
try:
    from PIL import Image
    im = Image.new('RGB', (64, 64)); im.putdata([((x * 4) % 256, (y * 4) % 256, (x * y) % 256) for y in range(64) for x in range(64)])
    buf = io.BytesIO(); im.save(buf, 'PNG'); TAKE = 'png:' + base64.b64encode(buf.getvalue()).decode()
except Exception:
    TAKE = 'png:' + 'iVBORw0KGgo' + 'A' * 400

MOCK = r"""
window.__commits=[];
const take=%s;
const mcp={ listTools:async()=>({}), callTool:async(srv,tool,args)=>{
  if(tool==='create_or_update_file'){ window.__commits.push(args); return {}; }
  if(tool==='get_file_contents'){ if(/\/\d+\.b64$/.test(args.path)) return {content:[{type:'text',text:take}]}; throw {code:'tool_error',message:'404 Not Found'}; }
  throw {code:'tool_error'}; } };
const sample=async(input,opts)=>({text:'"A gothic bell tower at dawn, crows circling the spire, one warm lit window, low mist, three-quarter view"',truncated:false});
sample.json=async()=>({}); sample.limits=async()=>({});
window.claude={use:async n=> n==='mcp'?mcp : n==='sample'?sample : null};
""" % json.dumps(TAKE)

async def main():
    async with async_playwright() as p:
        b = await getattr(p, os.environ.get('BROWSER', 'chromium')).launch()
        pg = await b.new_page(viewport={'width': 390, 'height': 820}, has_touch=True)
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)) if 'access control checks' not in str(e) else None)
        await pg.add_init_script(MOCK)
        await pg.goto(APP); await pg.wait_for_timeout(900)
        async def ev(x):
            try: return await pg.evaluate(x)
            except Exception as e: return {'error': str(e)[:120]}
        async def tap(sel):
            try: await pg.click(sel, timeout=2000)
            except Exception: pass
        has = await ev("!!window.Foxboard")
        check('Foxboard API present', has)
        F = "window.Foxboard"
        await ev(F + ".newDoc({w:96,h:96,bg:'#ffffff'})")
        # a 96x96 picture: left half red, right half blue (seams at the edges when tiled)
        img = await ev("""(()=>{ const c=document.createElement('canvas'); c.width=96; c.height=96; const g=c.getContext('2d');
            const d=g.createImageData(96,96); for(let y=0;y<96;y++) for(let x=0;x<96;x++){ const i=(y*96+x)*4; d.data[i]=x*2.6; d.data[i+1]=y*2.6; d.data[i+2]=90; d.data[i+3]=255; }
            g.putImageData(d,0,0); return Foxboard.add('image',{src:c.toDataURL(),x:0,y:0,w:96,h:96}); })()""")
        await pg.wait_for_timeout(200)

        # 1) sketch -> art
        r = await ev("""(()=>{ try{ const r=Foxboard.forgeFiles({mode:'sketch',prompt:'a stone bridge',strength:0.6,n:2});
            const j=JSON.parse(r.files[Object.keys(r.files).find(k=>k.endsWith('.json'))]); return {mode:j.mode,s:j.strength,init:!!j.init,w:j.w%64,files:Object.keys(r.files).length}; }catch(e){ return {err:String(e.message||e)}; } })()""")
        check('sketch: whole-frame job with strength + init', r.get('mode') == 'sketch' and r.get('s') == 0.6 and r.get('init') and r.get('w') == 0, r)
        r = await ev(f"""(()=>{{ try{{ const r=Foxboard.forgeFiles({{mode:'sketch',id:'{img}',prompt:'x',strength:2}}); const j=JSON.parse(r.files[Object.keys(r.files).find(k=>k.endsWith('.json'))]); return j.strength; }}catch(e){{ return String(e.message||e); }} }})()""")
        check('sketch: strength is clamped (<=0.95)', r == 0.95, r)

        # 3) seamless flag + 2) seed lock
        r = await ev("""(()=>{ try{ const r=Foxboard.forgeFiles({mode:'new',prompt:'cobblestone floor',tile:true,seed:'12345'}); const j=JSON.parse(Object.values(r.files)[0]); return {tile:j.tile,seed:j.seed}; }catch(e){ return {err:String(e)}; } })()""")
        check('tile: job carries tile:true', r.get('tile') is True, r)
        check('seed lock: typed seed is used', r.get('seed') == 12345, r)

        # Forge screen: start-from chips, seamless toggle, seed field, boost
        await ev("openAI ? 0 : 0") if False else None
        await ev("__fb.openAI('forge')"); await pg.wait_for_timeout(300)
        body = await pg.inner_text('#shBody')
        check('forge screen: Start from + My sketch', 'My sketch' in body, body[:120])
        check('forge screen: Seamless tile toggle', 'Seamless tile' in body)
        check('forge screen: seed lock field', await pg.locator('#shBody input[aria-label="Seed"]').count() == 1)
        # 5) prompt boost
        bb = pg.locator('#shBody button:has-text("Boost prompt")')
        check('prompt boost button shows with Claude', await bb.count() == 1)
        if await bb.count():
            await pg.locator('#shBody textarea').first.fill('bell tower'); await bb.click(); await pg.wait_for_timeout(300)
            v = await pg.locator('#shBody textarea').first.input_value()
            check('prompt boost rewrites the idea (quotes stripped)', v.startswith('A gothic bell tower') and not v.endswith('"'), v[:60])
            await tap('#shBody button:has-text("Undo boost")'); v2 = await pg.locator('#shBody textarea').first.input_value()
            check('prompt boost can be undone', v2 == 'bell tower', v2)
        # queue a sketch through the screen
        await tap('#shBody button:has-text("My sketch")')
        fr = await pg.locator('#shBody .row:has-text("Follow sketch")').count() and await pg.locator('#shBody .row:has-text("Follow sketch")').first.is_visible()
        check('follow slider shows for sketch', fr)
        await pg.locator('#shBody textarea').first.fill('a mossy stone bridge')
        await tap('#shBody button:has-text("Queue it")'); await pg.wait_for_timeout(600)
        jobs = await ev("__commits.filter(c=>c.path.endsWith('.json')).map(c=>JSON.parse(c.content))")
        check('screen queues a sketch job with strength', bool(jobs) and jobs[-1].get('mode') == 'sketch' and 0.2 <= jobs[-1].get('strength', 0) <= 0.95, jobs[-1] if jobs else None)

        # 2) variations + 7) gallery/favorites: a finished job on this phone
        await ev("""(()=>{ const L=JSON.parse(localStorage.getItem('foxboard.forgejobs')||'[]'); })()""")
        jid = await ev("""(async()=>{ const id=await Foxboard.forge({mode:'new',prompt:'a lantern bearer',seed:500,n:2}); return id; })()""")
        await ev(f"""(async()=>{{ const t=Foxboard.takes(); }})()""")
        await ev("__fb.forgeCheck(__fb.forgeJobs[0])"); await pg.wait_for_timeout(300)
        takes = await ev("Foxboard.takes()")
        check('takes(): finished takes listed with seeds', len(takes) == 2 and (takes[0] or {}).get('seed') in (500, 501), takes)
        n0 = await ev("__commits.length")
        vid = await ev(f"""(async()=>{{ try{{ return await Foxboard.vary('{jid}',1,'subtle'); }}catch(e){{ return 'ERR '+(e.message||e); }} }})()""")
        vj = await ev("(()=>{ const c=__commits.filter(c=>c.path.endsWith('.json')).pop(); return JSON.parse(c.content); })()")
        check('vary subtle: sketch from the take, same prompt, seed kept, low strength', vj.get('mode') == 'sketch' and vj.get('strength') == 0.35 and vj.get('seed') == 501 and 'lantern' in vj.get('prompt', ''), (vid, vj))
        sent_init = await ev("__commits.slice(%d).some(c=>c.path.endsWith('.init.b64'))" % n0)
        check('vary: the take is sent as the init image', sent_init)
        fav = await ev(f"Foxboard.favorite('{jid}',0)")
        favs = await ev("Foxboard.takes().filter(t=>t.fav).length")
        check('favorite: a take can be starred', fav is True and favs == 1, favs)
        await ev("__fb.openAI('forge')"); await pg.wait_for_timeout(300)
        await tap('#shBody .tabs button:has-text("Favorites")'); await pg.wait_for_timeout(200)
        n_img = await pg.locator('#shBody img').count()
        check('gallery: Favorites view shows the starred take', n_img == 1, n_img)
        await tap('#shBody img'); await pg.wait_for_timeout(200)
        check('tapping a take shows Subtle / Strong / Reuse', all([await pg.locator(f'#shBody button:has-text("{t}")').count() for t in ['Subtle', 'Strong', 'Reuse']]))
        await ev("__fb.t.closeSheet()")

        # 3) seamless locally
        r = await ev(f"""(async()=>{{ Foxboard.makeTileable('{img}'); await new Promise(r=>setTimeout(r,150));
            const u=Foxboard.tilePreview('{img}',2); const im=new Image(); await new Promise(r=>{{ im.onload=r; im.src=u; }});
            const c=document.createElement('canvas'); c.width=im.width; c.height=im.height; const g=c.getContext('2d'); g.drawImage(im,0,0);
            const W=im.width/2, H=im.height/2; let diff=0, n=0;
            for(let y=4;y<H-4;y+=3){{ const a=g.getImageData(W-1,y,1,1).data, b=g.getImageData(W,y,1,1).data; diff+=Math.abs(a[0]-b[0]); n++; }}
            for(let x=4;x<W-4;x+=3){{ const a=g.getImageData(x,H-1,1,1).data, b=g.getImageData(x,H,1,1).data; diff+=Math.abs(a[1]-b[1]); n++; }}
            return {{avg:diff/n, w:im.width}}; }})()""")
        check('make seamless: no hard seam where tiles meet', (g(r,'avg') if g(r,'avg') is not None else 999) < 40, r)

        # 4) pixelate
        r = await ev("""(async()=>{ const c=document.createElement('canvas'); c.width=256; c.height=256; const g=c.getContext('2d');
            const gr=g.createRadialGradient(128,128,10,128,128,110); gr.addColorStop(0,'#ffe080'); gr.addColorStop(1,'#a03010'); g.fillStyle=gr; g.beginPath(); g.arc(128,128,110,0,7); g.fill();
            const id=Foxboard.add('image',{src:c.toDataURL(),x:0,y:0,w:96,h:96}); await new Promise(r=>setTimeout(r,200));
            Foxboard.pixelate(id,{size:32,n:8,outline:true}); await new Promise(r=>setTimeout(r,150));
            const L=Foxboard.get(id); const im=new Image(); await new Promise(r=>{ im.onload=r; im.src=__fb.doc.pages[0].objects.find(o=>o.id===id).src; });
            const k=document.createElement('canvas'); k.width=im.width; k.height=im.height; const kg=k.getContext('2d'); kg.drawImage(im,0,0); const d=kg.getImageData(0,0,k.width,k.height).data;
            const cols=new Set(); let semi=0; for(let i=0;i<d.length;i+=4){ if(d[i+3]&&d[i+3]<255) semi++; if(d[i+3]) cols.add(d[i]+','+d[i+1]+','+d[i+2]); }
            return {w:im.width,h:im.height,colors:cols.size,semi,px:L.px}; })()""")
        check('pixelate: 32px + 1px outline = 34×34', g(r,'w') == 34 and g(r,'h') == 34, r)
        check('pixelate: limited palette (<= 8 + outline), no soft alpha, drawn crisp', (g(r,'colors') or 99) <= 9 and g(r,'semi') == 0 and g(r,'px') is True, r)

        # 8) sticker outline
        r = await ev("""(async()=>{ const c=document.createElement('canvas'); c.width=100; c.height=100; const g=c.getContext('2d'); g.fillStyle='#3060c0'; g.fillRect(30,30,40,40);
            const id=Foxboard.add('image',{src:c.toDataURL(),x:0,y:0,w:100,h:100}); await new Promise(r=>setTimeout(r,200));
            Foxboard.sticker(id,{width:0.05,color:'#ffffff'}); await new Promise(r=>setTimeout(r,150));
            const o=__fb.doc.pages[0].objects.find(o=>o.id===id); const im=new Image(); await new Promise(r=>{ im.onload=r; im.src=o.src; });
            const k=document.createElement('canvas'); k.width=im.width; k.height=im.height; const kg=k.getContext('2d'); kg.drawImage(im,0,0);
            const p=Math.round((im.width-100)/2); const edge=kg.getImageData(p+28,p+50,1,1).data, inside=kg.getImageData(p+50,p+50,1,1).data, far=kg.getImageData(2,2,1,1).data;
            let err=null; try{ const c2=document.createElement('canvas'); c2.width=c2.height=20; const x=c2.getContext('2d'); x.fillStyle='#fff'; x.fillRect(0,0,20,20); const id2=Foxboard.add('image',{src:c2.toDataURL(),x:0,y:0,w:20,h:20}); await new Promise(r=>setTimeout(r,150)); Foxboard.sticker(id2,{}); }catch(e){ err=e.message; }
            return {w:im.width, edge:[...edge], inside:[...inside], far:far[3], ow:o.w, err}; })()""")
        check('sticker: white ring just outside the cut-out, subject intact', (g(r,'w') or 0) > 100 and (g(r,'edge') or [0]*4)[0] > 240 and (g(r,'edge') or [0]*4)[3] > 200 and (g(r,'inside') or [0]*4)[2] > 150 and g(r,'far') == 0, r)
        check('sticker: asks to cut out first on a solid image', bool(g(r,'err')) and 'Remove background' in (g(r,'err') or ''), g(r,'err'))

        # 6) new background: mask = transparent area, subject kept
        r = await ev("""(async()=>{ const c=document.createElement('canvas'); c.width=80; c.height=80; const g=c.getContext('2d'); g.fillStyle='#e0a030'; g.fillRect(25,25,30,30);
            const id=Foxboard.add('image',{src:c.toDataURL(),x:0,y:0,w:80,h:80}); await new Promise(r=>setTimeout(r,200));
            try{ const r=Foxboard.forgeFiles({mode:'bg',id,prompt:'misty forest'}); const j=JSON.parse(r.files[Object.keys(r.files).find(k=>k.endsWith('.json'))]);
              const m=r.files[j.mask]; const im=new Image(); await new Promise(z=>{ im.onload=z; im.src='data:image/png;base64,'+m.split(':')[1]; });
              const k=document.createElement('canvas'); k.width=im.width; k.height=im.height; const kg=k.getContext('2d'); kg.drawImage(im,0,0);
              const corner=kg.getImageData(2,2,1,1).data[0], mid=kg.getImageData(Math.round(im.width/2),Math.round(im.height/2),1,1).data[0];
              return {mode:j.mode, prompt:j.prompt, corner, mid}; }catch(e){ return {err:String(e.message||e)}; } })()""")
        check('new background: edit job, background masked, subject kept', r.get('mode') == 'edit' and r.get('corner') == 255 and r.get('mid') == 0 and 'misty forest' in (r.get('prompt') or ''), r)

        # 9) before/after
        r = await ev("""(()=>{ const ids=Foxboard.list().map(l=>l.id); try{ Foxboard.compare(ids[ids.length-1]); }catch(e){ return 'ERR '+e.message; }
            const ov=document.getElementById('compare'); const ok=!!(ov&&ov.querySelector('canvas')&&ov.querySelector('input[type=range]')); if(ov) ov.remove(); return ok; })()""")
        check('compare: before/after slider opens', r is True, r)

        # image panel shows the new tools
        await ev("__fb.sel=Foxboard.list()[0].id; __fb.openProps()"); await pg.wait_for_timeout(250)
        body = await pg.inner_text('#shBody')
        for t in ['Pixelate', 'Make seamless', 'Thin outline', 'New background']:
            check('image panel: ' + t, t in body)
        miss = await ev("Object.keys(Foxboard.help()).filter(k=>typeof Foxboard[k]!=='function')")
        check('every API_DOC entry is a command', not miss, miss)
        check('no page errors', not errs, errs)
        await b.close()

        # no Claude (iPhone / installable site): tools still work, Claude-only bits hidden
        b = await getattr(p, os.environ.get('BROWSER', 'chromium')).launch()
        pg = await b.new_page(viewport={'width': 390, 'height': 820}, has_touch=True)
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)) if 'access control checks' not in str(e) else None)
        await pg.goto(APP); await pg.wait_for_timeout(700)
        try: r = await pg.evaluate("""(async()=>{ Foxboard.newDoc({w:64,h:64}); const c=document.createElement('canvas'); c.width=c.height=64; const g=c.getContext('2d'); g.fillStyle='#456'; g.fillRect(0,0,64,64); g.fillStyle='#c84'; g.fillRect(0,0,32,64);
            const id=Foxboard.add('image',{src:c.toDataURL(),x:0,y:0,w:64,h:64}); await new Promise(r=>setTimeout(r,200)); Foxboard.makeTileable(id); Foxboard.pixelate(id,{size:16,outline:false});
            __fb.openAI('forge'); await new Promise(r=>setTimeout(r,200)); return {boost:[...document.querySelectorAll('#shBody button')].some(b=>/Boost/.test(b.textContent))}; })()""")
        except Exception as e: r = {'error': str(e)[:120]}
        check('no Claude: seamless + pixelate work, boost hidden', g(r,'boost') is False, r)
        check('no page errors (no Claude)', not errs, errs)
        await b.close()

asyncio.run(main())

# Forge render command (dry run, no model): sketch -> img2img with strength; tile -> --circular
with tempfile.TemporaryDirectory() as td:
    td = pathlib.Path(td); (td / 'forge/jobs').mkdir(parents=True)
    from PIL import Image as _I
    b = io.BytesIO(); _I.new('RGB', (64, 64), (200, 50, 50)).save(b, 'PNG')
    (td / 'forge/jobs/sk1.init.b64').write_text('png:' + base64.b64encode(b.getvalue()).decode())
    (td / 'forge/jobs/sk1.json').write_text(json.dumps({'mode': 'sketch', 'prompt': 'a bridge', 'n': 1, 'w': 512, 'h': 512, 'seed': 7, 'strength': 0.55, 'tile': True, 'init': 'forge/jobs/sk1.init.b64'}))
    (td / 'forge/jobs/nw1.json').write_text(json.dumps({'mode': 'new', 'prompt': 'grass', 'n': 1, 'w': 512, 'h': 512, 'seed': 7}))
    (td / 'models.env').write_text('DIFF=d\nVAE=v\nCLIP=c\nT5GGUF=t\n')
    env = dict(os.environ, FORGE_DRY='1', SD='sd')
    out = {}
    for jid in ('sk1', 'nw1'):
        pr = subprocess.run([sys.executable, str(ROOT / 'forge/render_one.py'), jid, '0'], cwd=td, env=env, capture_output=True, text=True, timeout=60)
        try: out[jid] = json.loads(pr.stdout.strip().splitlines()[-1])
        except Exception: out[jid] = (pr.stdout + pr.stderr)[-300:]
    sk = out['sk1']
    check('render: sketch runs img2img (--init-img, --strength 0.55, no mask)', isinstance(sk, list) and '--init-img' in sk and sk[sk.index('--strength') + 1] == '0.55' and '--mask' not in sk, sk)
    check('render: tile job adds --circular', isinstance(sk, list) and '--circular' in sk)
    check('render: plain job has no --circular', isinstance(out['nw1'], list) and '--circular' not in out['nw1'], out['nw1'])

print(f'\n{sum(res)}/{len(res)} passed'); sys.exit(0 if res and all(res) else 1)
