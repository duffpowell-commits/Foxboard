import asyncio, json
from playwright.async_api import async_playwright
import pathlib
APP = (pathlib.Path(__file__).resolve().parent.parent / 'index.html').as_uri()
MOCK = r"""
window.__saved=[];
const N=16; const rows=[]; for(let y=0;y<N;y++){ let r=''; for(let x=0;x<N;x++) r+= (x>3&&x<12&&y>3&&y<12)?((x+y)%2?'1':'0'):'.'; rows.push(r); }
const fakeSample=async(input,opts={})=>{ const t='<svg viewBox="0 0 64 64"><script>alert(1)</script><rect width="64" height="64" fill="#223" onclick="x()"/><circle cx="32" cy="32" r="20" fill="url(http://evil/x)"/><circle cx="32" cy="32" r="14" fill="#fc0"/></svg>'; opts.onText&&opts.onText({text:t,delta:t}); return {text: String(input).includes('senior game artist')?'Verdict: readable. - Fix contrast.':t,truncated:false}; };
fakeSample.json=async(input)=>{ if(String(input).includes('pixel artist')) return {palette:['#ff0000','#00ff00'],rows};
  return {background:'#101820',objects:[{type:'rect',x:2,y:2,w:60,h:20,fill:'#ff7a3d',radius:3},{type:'text',x:4,y:30,w:56,h:10,text:'BOSS',size:8,font:'pixel',align:'center',fill:'#ffffff'}]}; };
fakeSample.limits=async()=>({maxPromptBytes:262144,images:{maxCount:5,maxInputBytes:2e7,mediaTypes:['image/png']}});
window.claude={use:async n=> n==='sample'?fakeSample : n==='downloads'?{save:async(r)=>{window.__saved.push([r.filename, r.data.size||r.data.length]); return {status:'saved'};}}:null};
"""
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={'width':390,'height':820}, device_scale_factor=2, has_touch=True)
        errs=[]; pg.on('pageerror', lambda e: errs.append(str(e))); pg.on('console', lambda m: errs.append('console:'+m.text) if m.type=='error' and 'fonts' not in m.text and 'ERR_' not in m.text else None)
        await pg.add_init_script(MOCK)
        await pg.goto(APP); await pg.wait_for_timeout(700)
        ev = pg.evaluate
        st = await pg.locator('#stage').bounding_box()
        v = await ev("__fb.view")
        def scr(x,y): return st['x']+v['x']+x*v['z'], st['y']+v['y']+y*v['z']
        # draw mode stroke
        await pg.click('#tDraw'); await pg.wait_for_timeout(100)
        x0,y0=scr(5.5,5.5); x1,y1=scr(30.5,20.5)
        await pg.mouse.move(x0,y0); await pg.mouse.down(); await pg.mouse.move(x1,y1,steps=8); await pg.mouse.up()
        info = await ev("(()=>{const o=__fb.doc.pages[0].objects[0]; return {type:o.type,paint:o.paint,len:o.src.length}})()")
        print('after stroke', info)
        c = await ev("(()=>{const c=__fb.renderToCanvas(1,false,0);const d=c.getContext('2d').getImageData(5,5,1,1).data;const e=c.getContext('2d').getImageData(30,20,1,1).data;const f=c.getContext('2d').getImageData(50,50,1,1).data;return [Array.from(d),Array.from(e),Array.from(f)]})()")
        print('pixels start/end/empty', c)
        # fill bucket
        await pg.click('#drawbar [data-t=fill]'); x,y=scr(50.5,50.5); await pg.mouse.click(x,y)
        f = await ev("Array.from(__fb.renderToCanvas(1,false,0).getContext('2d').getImageData(50,50,1,1).data)")
        print('after fill', f)
        await pg.click('#bUndo'); f2 = await ev("Array.from(__fb.renderToCanvas(1,false,0).getContext('2d').getImageData(50,50,1,1).data)")
        print('undo fill', f2)
        await pg.click('#drawDone')
        # frames
        await pg.click('#pagebar button:has-text("＋")'); await pg.wait_for_timeout(200)
        await pg.click('#pagebar button:has-text("＋")'); await pg.wait_for_timeout(200)
        print('pages', await ev("__fb.doc.pages.length"), 'cur', await ev("__fb.doc.cur"))
        # AI pixel
        await pg.click('#tAI'); await pg.wait_for_timeout(200)
        await pg.click('.tabs button:has-text("Pixel")'); await pg.wait_for_timeout(100)
        await pg.fill('#shBody textarea','test'); await pg.click('button:has-text("Generate")'); await pg.wait_for_timeout(500)
        print('ai pixel out:', await pg.inner_text('#shBody .out'))
        # vector
        await pg.click('.tabs button:has-text("Vector")'); await pg.click('button:has-text("Generate")'); await pg.wait_for_timeout(800)
        print('ai vector out:', await pg.inner_text('#shBody .out'))
        await pg.click('.tabs button:has-text("Design")'); await pg.click('button:has-text("Generate")'); await pg.wait_for_timeout(500)
        print('ai layout out:', await pg.inner_text('#shBody .out'))
        await pg.click('.tabs button:has-text("Critique")'); await pg.click('button:has-text("Generate")'); await pg.wait_for_timeout(500)
        print('ai critique out:', await pg.inner_text('#shBody .out'))
        await pg.click('#shClose'); await pg.wait_for_timeout(300)
        print('objs on frame', await ev("__fb.doc.pages[__fb.doc.cur].objects.map(o=>o.type+(o.name?':'+o.name:''))"))
        svgsrc = await ev("__fb.cleanSVG('<svg viewBox=\"0 0 10 10\"><script>x</script><rect onload=\"y\" fill=\"url(http://e)\"/><a href=\"http://x\">z</a></svg>',10,10).src")
        import urllib.parse; print('sanitized', urllib.parse.unquote(svgsrc)[:300])
        await pg.screenshot(path='/tmp/v2a.png')
        # remove bg test: image with solid bg
        r = await ev("""(async()=>{const c=document.createElement('canvas');c.width=40;c.height=40;const g=c.getContext('2d');g.fillStyle='#00ff00';g.fillRect(0,0,40,40);g.fillStyle='#ff0000';g.fillRect(10,10,20,20);
          const src=c.toDataURL('image/png'); const d=__fb.doc; d.pages[d.cur].objects.push({id:'bgt',type:'image',x:0,y:0,w:40,h:40,rot:0,opacity:1,src,natW:40,natH:40}); __fb.doc=d; await new Promise(r=>setTimeout(r,200));
          const o=__fb.doc.pages[__fb.doc.cur].objects.find(o=>o.id==='bgt'); __fb.removeBg(o,40); await new Promise(r=>setTimeout(r,300));
          const k=__fb.renderToCanvas(1,false); const a=k.getContext('2d').getImageData(2,2,1,1).data[3]; const m=k.getContext('2d').getImageData(20,20,1,1).data; return [a,Array.from(m)]})()""")
        print('removeBg corner alpha, middle', r)
        # export sheet
        await pg.click('#bExport'); await pg.wait_for_timeout(200)
        print('export info', await pg.inner_text('#shBody .hint'))
        await pg.click('button:has-text("Save image")'); await pg.wait_for_timeout(500)
        print('saved', await ev("window.__saved"))
        await pg.click('button:has-text("Preview")'); await pg.wait_for_timeout(300)
        await pg.screenshot(path='/tmp/v2b.png')
        print('errors', errs); await b.close()
asyncio.run(main())
