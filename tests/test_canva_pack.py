"""Canva-pack features + the Foxboard command API (the way Claude drives every feature).
Each check renders through Foxboard's own renderer and reads pixels back."""
import os, asyncio, pathlib, sys
from playwright.async_api import async_playwright
APP = os.environ.get('APP_URL') or (pathlib.Path(__file__).resolve().parent.parent / 'index.html').as_uri()
results = []
def check(name, ok, extra=''):
    results.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + name + (('  ' + str(extra)) if extra != '' else ''))

PX = "(async(page,x,y)=>Array.from(Foxboard.renderCanvas(1,page).getContext('2d').getImageData(x,y,1,1).data))"

async def main():
    async with async_playwright() as p:
        b = await getattr(p, os.environ.get('BROWSER','chromium')).launch()
        pg = await b.new_page(viewport={'width': 390, 'height': 820}, device_scale_factor=2, has_touch=True)
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto(APP); await pg.wait_for_timeout(600)
        ev = pg.evaluate
        has = await ev("!!window.Foxboard")
        check('Foxboard API exists', has)
        if not has:
            print(f'\n{sum(results)}/{len(results)} passed'); sys.exit(1)
        px = lambda x, y, page=0: ev(f"{PX}({page},{x},{y})")
        help_ = await ev("Foxboard.help()")
        need = ['add','set','get','list','remove','select','group','ungroup','align','distribute','crop','mask','element','magicErase','expand','removeBg','resizeCanvas','exportFile','render','undo','redo','addPage','newDoc','load','forge']
        miss = [n for n in need if n not in help_]
        check('help() documents every command', not miss, miss)

        # shadow
        await ev("Foxboard.newDoc({w:100,h:100,bg:'#ffffff'})")
        rid = await ev("Foxboard.add('rect',{x:20,y:20,w:40,h:40,fill:'#ff0000',shadow:{c:'#000000',a:1,blur:0,x:10,y:10}})")
        s = await px(65, 65)
        check('drop shadow renders offset', s[0] < 80 and s[1] < 80, s)
        # gradient
        await ev(f"Foxboard.set('{rid}',{{shadow:null,x:0,y:0,w:100,h:100,grad:{{a:'#ff0000',b:'#0000ff',ang:0}}}})")
        l, r = await px(2, 50), await px(97, 50)
        check('gradient fill left red / right blue', l[0] > 200 and l[2] < 60 and r[2] > 200 and r[0] < 60, (l, r))
        # blend
        await ev(f"Foxboard.set('{rid}',{{grad:null,fill:'#0000ff',w:60,h:60}})")
        r2 = await ev("Foxboard.add('rect',{x:30,y:30,w:60,h:60,fill:'#ff0000',blend:'multiply'})")
        o = await px(45, 45)
        check('blend multiply: red over blue = black', o[0] < 30 and o[2] < 30, o)
        # curved text
        tid = await ev("Foxboard.add('text',{text:'CURVED TITLE',size:12,fill:'#000000',strokeW:0})")
        h0 = await ev(f"Foxboard.get('{tid}').h")
        await ev(f"Foxboard.set('{tid}',{{curve:70}})")
        h1 = await ev(f"Foxboard.get('{tid}').h")
        check('curved text bends (taller box)', h1 > h0 * 1.4, (h0, h1))

        # images: two-color 40x20 (left red, right green)
        mk = """(()=>{const c=document.createElement('canvas');c.width=40;c.height=20;const g=c.getContext('2d');g.fillStyle='#ff0000';g.fillRect(0,0,20,20);g.fillStyle='#00ff00';g.fillRect(20,0,20,20);return c.toDataURL('image/png');})()"""
        await ev("Foxboard.newDoc({w:100,h:100,bg:'#ffffff'})")
        iid = await ev(f"Foxboard.add('image',{{src:{mk},x:10,y:10,w:80,h:40}})")
        await ev(f"Foxboard.crop('{iid}',{{r:0.5}})")
        g = await ev(f"Foxboard.get('{iid}')")
        c1 = await px(int(g['x'] + g['w'] - 3), int(g['y'] + g['h'] / 2))
        check('crop right half off: only red left, box narrower', c1[0] > 200 and c1[1] < 60 and abs(g['w'] - 40) < 1.5, (c1, g['w']))
        await ev(f"Foxboard.crop('{iid}',{{r:0}})")
        await ev(f"Foxboard.set('{iid}',{{x:10,y:10,w:80,h:80}})")
        await ev(f"Foxboard.mask('{iid}','circle')")
        corner, mid = await px(12, 12), await px(30, 50)
        check('circle mask: corner clear, middle shows image', corner[0] > 240 and corner[1] > 240 and mid[0] > 200 and mid[1] < 60, (corner, mid))

        # group / align / distribute
        await ev("Foxboard.newDoc({w:200,h:100,bg:'#ffffff'})")
        ids = await ev("[Foxboard.add('rect',{x:5,y:10,w:20,h:20}),Foxboard.add('rect',{x:60,y:40,w:20,h:20}),Foxboard.add('rect',{x:150,y:5,w:30,h:20})]")
        await ev(f"Foxboard.align({ids},'top')")
        ys = await ev(f"{ids}.map(i=>Foxboard.get(i).y)")
        check('align top', len(set(round(y, 3) for y in ys)) == 1, ys)
        await ev(f"Foxboard.set('{ids[1]}',{{x:100}})")
        await ev(f"Foxboard.distribute({ids},'h')")
        gs = await ev(f"(()=>{{const o={ids}.map(i=>Foxboard.get(i)).sort((a,b)=>a.x-b.x);return [o[1].x-(o[0].x+o[0].w), o[2].x-(o[1].x+o[1].w)];}})()")
        check('distribute equal gaps', abs(gs[0] - gs[1]) < 0.01, gs)
        gid = await ev(f"Foxboard.group({ids[:2]})")
        await ev(f"Foxboard.select('{ids[0]}')")
        sel = await ev("Foxboard.selected()")
        check('selecting one grouped item selects the group', sorted(sel) == sorted(ids[:2]), sel)
        x0 = await ev(f"Foxboard.get('{ids[1]}').x")
        await ev(f"Foxboard.move('{ids[0]}',10,0)")
        x1 = await ev(f"Foxboard.get('{ids[1]}').x")
        check('moving a grouped item moves the group', abs(x1 - x0 - 10) < 0.01, (x0, x1))
        await ev(f"Foxboard.ungroup('{gid}')")
        check('ungroup', await ev(f"!Foxboard.get('{ids[0]}').gid"))

        # elements
        names = await ev("Foxboard.elements()")
        check('20+ elements available', len(names) >= 20, len(names))
        await ev("Foxboard.newDoc({w:100,h:100,bg:'#ffffff'})")
        eid = await ev("Foxboard.element('heart',{color:'#ff0000',x:10,y:10,w:80,h:80})")
        await pg.wait_for_timeout(300)
        e = await px(50, 55)
        check('heart element renders in chosen color', e[0] > 200 and e[1] < 80, e)

        # resize canvas
        await ev("Foxboard.newDoc({w:64,h:64,bg:'#ffffff'})")
        rid = await ev("Foxboard.add('rect',{x:16,y:16,w:32,h:32})")
        await ev("Foxboard.resizeCanvas(128,128,'fit')")
        g = await ev(f"Foxboard.get('{rid}')")
        check('resize 64->128 scales layout 2x', abs(g['w'] - 64) < 0.5 and abs(g['x'] - 32) < 0.5, g)

        # pdf + video
        await ev("Foxboard.addPage(true)")
        pdf = await ev("(async()=>{const bl=await Foxboard.exportFile('pdf',{scale:2}); const t=new TextDecoder('latin1').decode(new Uint8Array(await bl.arrayBuffer())); return [t.slice(0,5), (t.match(/\\/Type \\/Page\\b/g)||[]).length, t.includes('/DCTDecode'), bl.type];})()")
        check('PDF export: valid header, 2 pages, JPEG pages', pdf[0] == '%PDF-' and pdf[1] == 2 and pdf[2] and pdf[3] == 'application/pdf', pdf)
        if await ev("!!window.MediaRecorder && ['video/mp4','video/webm'].some(m=>MediaRecorder.isTypeSupported(m))"):
            vid = await ev("(async()=>{const bl=await Foxboard.exportFile('video',{scale:2,loops:1}); return [bl.size, bl.type];})()")
            check('video export makes a playable file', vid[0] > 500 and vid[1].startswith('video/'), vid)
        else: print('SKIP video: this browser build has no recorder')

        # tap-select erase + local expand
        flat = """(()=>{const c=document.createElement('canvas');c.width=60;c.height=60;const g=c.getContext('2d');g.fillStyle='#22aa44';g.fillRect(0,0,60,60);g.fillStyle='#ff0000';g.beginPath();g.arc(30,30,9,0,7);g.fill();return c.toDataURL('image/png');})()"""
        await ev("Foxboard.newDoc({w:60,h:60,bg:'#ffffff'})")
        fid = await ev(f"Foxboard.add('image',{{src:{flat},x:0,y:0,w:60,h:60}})")
        await ev(f"Foxboard.magicErase('{fid}',{{tap:[[30,30,60]]}})")
        await pg.wait_for_timeout(200)
        t = await px(30, 30)
        check('tap-select magic erase removes the red blob', not (t[0] > 200 and t[1] < 80) and t[1] > 120, t)
        await ev(f"Foxboard.expand('{fid}',{{l:10,r:10,t:10,b:10}})")
        g = await ev(f"Foxboard.get('{fid}')")
        await ev("Foxboard.resizeCanvas(80,80,'fit')")
        await ev(f"Foxboard.set('{fid}',{{x:0,y:0,w:80,h:80}})")
        ed = await px(2, 2)
        check('expand grows the image and fills new edges', g['natW'] == 80 and g['natH'] == 80 and ed[3] == 255 and ed[1] > 120, (g['natW'], ed))

        # undo works through the API
        await ev("Foxboard.newDoc({w:50,h:50})"); n0 = await ev("Foxboard.list().length")
        await ev("Foxboard.add('rect',{})"); await ev("Foxboard.undo()")
        check('undo after API add', await ev("Foxboard.list().length") == n0)

        # UI reachability by touch
        await ev("Foxboard.newDoc({w:100,h:100,bg:'#ffffff'})")
        iid = await ev(f"Foxboard.add('image',{{src:{mk},x:10,y:10,w:80,h:40}})")
        await ev(f"Foxboard.select('{iid}')"); await ev("__fb.openProps()"); await pg.wait_for_timeout(200)
        body = await pg.inner_text('#shBody')
        for k in ['Crop', 'Shape', 'Shadow', 'Blend', 'Expand']:
            check(f'image panel has {k}', k.lower() in body.lower())
        tid = await ev("Foxboard.add('text',{text:'Hi'})")
        await ev(f"Foxboard.select('{tid}')"); await ev("__fb.openProps()"); await pg.wait_for_timeout(200)
        body = await pg.inner_text('#shBody')
        for k in ['Curve', 'Gradient', 'Shadow']:
            check(f'text panel has {k}', k.lower() in body.lower())
        await pg.click('#shClose'); await pg.wait_for_timeout(150)
        check('Elements button in toolbar', await pg.locator('#tEl').count() == 1)
        await pg.click('#tEl'); await pg.wait_for_timeout(200)
        n = await pg.locator('#shBody .elgrid button').count()
        check('elements sheet shows tiles', n >= 20, n)
        await pg.locator('#shBody .elgrid button').first.click(); await pg.wait_for_timeout(200)
        await pg.click('#bMenu'); await pg.wait_for_timeout(150)
        check('menu has Resize', 'resize' in (await pg.inner_text('#shBody')).lower())
        await pg.click('#shClose'); await pg.click('#bExport'); await pg.wait_for_timeout(200)
        body = await pg.inner_text('#shBody')
        check('export offers PDF and Video', 'PDF' in body.upper() and 'VIDEO' in body.upper(), body[:120])
        await pg.click('#shClose'); await pg.wait_for_timeout(150)
        # multi-select by touch
        ids = await ev("[Foxboard.add('rect',{x:5,y:5,w:20,h:20}),Foxboard.add('rect',{x:60,y:60,w:20,h:20})]")
        await ev(f"Foxboard.select('{ids[0]}')"); await pg.wait_for_timeout(100)
        check('ctx bar has multi-select button', await pg.locator('#ctx button[data-a="multi"]').count() == 1)
        await pg.click('#ctx button[data-a="multi"]')
        st = await pg.locator('#stage').bounding_box(); v = await ev("__fb.view")
        await pg.mouse.click(st['x'] + v['x'] + 70 * v['z'], st['y'] + v['y'] + 70 * v['z']); await pg.wait_for_timeout(150)
        check('tap adds to multi-selection', sorted(await ev("Foxboard.selected()")) == sorted(ids), await ev("Foxboard.selected()"))
        check('align button shows for multi-selection', await pg.locator('#ctx button[data-a="align"]').is_visible())
        await pg.screenshot(path='/tmp/canva_pack_ui.png')
        check('no page errors', not errs, errs)
        await b.close()
    print(f'\n{sum(results)}/{len(results)} passed'); sys.exit(0 if all(results) else 1)

asyncio.run(main())
