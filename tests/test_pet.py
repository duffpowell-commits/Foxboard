"""ChatGPT pet export (Nov 20): a cut-out image becomes a ChatGPT/Codex pet sprite sheet.
Contract (OpenAI hatch-pet): 1536x1872 PNG/WebP, transparent, 8 cols x 9 rows of 192x208 cells, rows =
idle 6, running-right 8, running-left 8, waving 4, jumping 5, failed 8, waiting 6, running 6, review 6 frames;
unused cells fully transparent. pet.json = {id, displayName, description, spritesheetPath}."""
import json, os, pathlib, asyncio
from playwright.async_api import async_playwright
ROOT = pathlib.Path(__file__).resolve().parent.parent
APP = os.environ.get('APP_URL') or (ROOT / 'index.html').as_uri()

res = []
def check(n, ok, x=''):
    res.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + n + (('  ' + str(x)) if x != '' else ''))

FRAMES = [6, 8, 8, 4, 5, 8, 6, 6, 6]

async def main():
    async with async_playwright() as p:
        b = await getattr(p, os.environ.get('BROWSER', 'chromium')).launch()
        pg = await b.new_page(viewport={'width': 390, 'height': 820}, has_touch=True)
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)) if 'access control checks' not in str(e) else None)
        await pg.goto(APP); await pg.wait_for_timeout(900)
        async def ev(x):
            try: return await pg.evaluate(x)
            except Exception as e: return {'error': str(e)[:160]}
        await ev("Foxboard.newDoc({w:200,h:200,bg:'transparent'})")
        # a cut-out: an orange blob with a dark eye on the right, transparent around it (asymmetric, so mirroring shows)
        pid = await ev("""(async()=>{ const c=document.createElement('canvas'); c.width=120; c.height=90; const g=c.getContext('2d');
            g.fillStyle='#e07a2f'; g.beginPath(); g.ellipse(60,50,50,38,0,0,Math.PI*2); g.fill();
            g.fillStyle='#111'; g.beginPath(); g.arc(90,40,7,0,Math.PI*2); g.fill();
            const id=Foxboard.add('image',{src:c.toDataURL(),x:40,y:40,w:120,h:90}); await new Promise(r=>setTimeout(r,250)); return id; })()""")
        check('Foxboard.petSheet exists', await ev("typeof Foxboard.petSheet==='function' && typeof Foxboard.petFiles==='function'"))
        r = await ev("""(async()=>{ try{ const url=Foxboard.petSheet(%s,{name:'Ember'}); const im=await new Promise((ok,no)=>{ const i=new Image(); i.onload=()=>ok(i); i.onerror=no; i.src=url; });
            const c=document.createElement('canvas'); c.width=im.width; c.height=im.height; const g=c.getContext('2d'); g.drawImage(im,0,0);
            const d=g.getImageData(0,0,c.width,c.height).data; const W=c.width;
            const cell=(r,k)=>{ let n=0,gray=0,sat=0,cx=0; for(let y=r*208;y<r*208+208;y++) for(let x=k*192;x<k*192+192;x++){ const i=(y*W+x)*4; if(d[i+3]>40){ n++; cx+=x-k*192; const mx=Math.max(d[i],d[i+1],d[i+2]), mn=Math.min(d[i],d[i+1],d[i+2]); sat+=mx-mn; } } return {n, sat:n?sat/n:0, cx:n?cx/n:0}; };
            const frames=%s, used=[], empty=[]; for(let r=0;r<9;r++) for(let k=0;k<8;k++){ const s=cell(r,k); if(k<frames[r]) used.push(s.n); else empty.push(s.n); }
            let edge=0; for(let r=0;r<9;r++) for(let k=0;k<8;k++){ for(let x=k*192;x<k*192+192;x++){ for(const y of [r*208, r*208+207]) if(d[(y*W+x)*4+3]>40) edge++; } }
            const rr=cell(1,0), rl=cell(2,0), idle=cell(0,0), fail=cell(5,3);
            const pngSig=url.startsWith('data:image/png');
            const idleDiff=(()=>{ let diff=0; for(let y=0;y<208;y++) for(let x=0;x<192;x++){ const a=(y*W+x)*4, b2=(y*W+x+192*2)*4; if(Math.abs(d[a+3]-d[b2+3])>40) diff++; } return diff; })();
            return {w:im.width,h:im.height,png:pngSig,usedMin:Math.min(...used),emptyMax:Math.max(...empty),edge,rr:rr.cx,rl:rl.cx,idleSat:idle.sat,failSat:fail.sat,idleDiff}; }catch(e){ return {err:String(e.message||e)}; } })()""" % (json.dumps(pid), json.dumps(FRAMES)))
        ok = isinstance(r, dict) and 'err' not in r and 'error' not in r
        check('sheet is 1536 x 1872 PNG', ok and r['w'] == 1536 and r['h'] == 1872 and r['png'], r)
        check('every frame cell the contract uses has the pet in it', ok and r['usedMin'] > 1500, ok and r.get('usedMin'))
        check('cells past each row\'s frame count are fully transparent', ok and r['emptyMax'] == 0, ok and r.get('emptyMax'))
        check('nothing touches a cell\'s top or bottom edge (no bleed between rows)', ok and r['edge'] == 0, ok and r.get('edge'))
        check('running-left is running-right mirrored (eye on the other side)', ok and r['rr'] > 96 and r['rl'] < 96 or (ok and abs((r['rr'] - 96) + (r['rl'] - 96)) < 6 and r['rr'] != r['rl']), ok and (r.get('rr'), r.get('rl')))
        check('failed row is drained of colour', ok and r['failSat'] < r['idleSat'] * 0.5, ok and (r.get('idleSat'), r.get('failSat')))
        check('idle frames actually move (frame 0 vs 2 differ)', ok and r['idleDiff'] > 50, ok and r.get('idleDiff'))
        f = await ev("(()=>{ try{ const r=Foxboard.petFiles(%s,{name:'Ember the Fox!'}); return {json:JSON.parse(r.json), sheet:r.sheet.slice(0,22), file:r.sheetName}; }catch(e){ return {err:String(e.message||e)}; } })()" % json.dumps(pid))
        j = isinstance(f, dict) and f.get('json') or {}
        check('pet.json has id / displayName / description / spritesheetPath', j.get('id') == 'ember-the-fox' and j.get('displayName') == 'Ember the Fox!' and j.get('description') and j.get('spritesheetPath') == f.get('file'), f)
        # an image with no transparency is refused with a plain message
        r = await ev("""(async()=>{ const c=document.createElement('canvas'); c.width=c.height=64; const g=c.getContext('2d'); g.fillStyle='#456'; g.fillRect(0,0,64,64);
            const id=Foxboard.add('image',{src:c.toDataURL(),x:0,y:0,w:64,h:64}); await new Promise(r=>setTimeout(r,200));
            try{ Foxboard.petSheet(id); return 'no error'; }catch(e){ return String(e.message||e); } })()""")
        check('an image without a cut-out is refused with a hint', isinstance(r, str) and 'Remove background' in r, r)
        # the image panel offers it, and the sheet opens with a live preview + save buttons
        await ev("__fb.sel=%s; __fb.openProps()" % json.dumps(pid)); await pg.wait_for_timeout(250)
        body = await pg.inner_text('#shBody')
        check('image panel: ChatGPT pet button', 'ChatGPT pet' in body)
        try:
            await pg.click('text=🐾 ChatGPT pet', timeout=2000); await pg.wait_for_timeout(400)
        except Exception as e: pass
        body = await pg.inner_text('#shBody')
        prev = await ev("(()=>{ const c=document.querySelector('#shBody canvas.petPrev'); return c?[c.width,c.height]:null; })()")
        check('pet sheet: preview canvas 192x208', prev == [192, 208], prev)
        check('pet sheet: save buttons + upload steps', 'Save sprite sheet' in body and 'pet.json' in body and 'Upload pet' in body, body[:200])
        wide = await ev("document.documentElement.scrollWidth <= window.innerWidth + 1")
        check('pet sheet fits a 390px phone (no sideways scroll)', wide)
        miss = await ev("Object.keys(Foxboard.help()).filter(k=>typeof Foxboard[k]!=='function')")
        check('every API_DOC entry is a command', not miss, miss)
        check('petSheet + petFiles are documented', await ev("!!(Foxboard.help().petSheet && Foxboard.help().petFiles)"))
        check('no page errors', not errs, errs)
        await b.close()

asyncio.run(main())
print(f'\n{sum(res)}/{len(res)} passed'); import sys; sys.exit(0 if res and all(res) else 1)
