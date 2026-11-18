import asyncio, base64, io
from playwright.async_api import async_playwright
import pathlib
APP = (pathlib.Path(__file__).resolve().parent.parent / 'index.html').as_uri()
from PIL import Image
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={'width':390,'height':820}, device_scale_factor=2)
        errs=[]; pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto(APP); await pg.wait_for_timeout(600)
        # build 3-frame pixel anim: red square moving; transparent bg
        b64 = await pg.evaluate("""(async()=>{
          const d=__fb.doc; d.w=16; d.h=16; d.pixel=true; d.bg='transparent'; d.fps=10;
          d.pages=[0,1,2].map(i=>({id:'p'+i,objects:[{id:'r'+i,type:'rect',x:2+i*4,y:5,w:4,h:4,rot:0,fill:'#ff0000',stroke:'#000',strokeW:0,opacity:1}]}));
          __fb.doc=d;
          const blob=__fb.makeGIF(2); const buf=new Uint8Array(await blob.arrayBuffer());
          let s=''; for(const x of buf) s+=String.fromCharCode(x); return btoa(s); })()""")
        im = Image.open(io.BytesIO(base64.b64decode(b64)))
        print('gif', im.format, im.size, 'frames', im.n_frames, 'loop', im.info.get('loop'), 'duration', im.info.get('duration'))
        for f in range(im.n_frames):
            im.seek(f); fr = im.convert('RGBA')
            print(' frame', f, 'px(5,11)=', fr.getpixel((5,11)), 'px(13,11)=', fr.getpixel((13,11)), 'corner', fr.getpixel((0,0)))
        # photo-ish gradient (>256 colors) to exercise median cut
        b64 = await pg.evaluate("""(async()=>{
          const c=document.createElement('canvas');c.width=120;c.height=90;const g=c.getContext('2d');
          for(let y=0;y<90;y++)for(let x=0;x<120;x++){g.fillStyle=`rgb(${x*2},${y*2.8|0},${(x+y)%256})`;g.fillRect(x,y,1,1);}
          const d=__fb.doc; d.w=120; d.h=90; d.pixel=false; d.bg='#ffffff';
          d.pages=[{id:'a',objects:[{id:'i',type:'image',x:0,y:0,w:120,h:90,rot:0,opacity:1,src:c.toDataURL()}]}]; __fb.doc=d;
          await new Promise(r=>setTimeout(r,300));
          const blob=__fb.makeGIF(1); const buf=new Uint8Array(await blob.arrayBuffer()); let s=''; for(const x of buf) s+=String.fromCharCode(x); return btoa(s); })()""")
        im = Image.open(io.BytesIO(base64.b64decode(b64))).convert('RGB')
        print('gradient gif', im.size, 'px(60,45)', im.getpixel((60,45)), 'expected ~', (120,126,105))
        # templates
        n = await pg.evaluate("__fb.BUILTIN.length")
        names = await pg.evaluate("__fb.BUILTIN.map(f=>{const d=f(); return d.name+':'+d.pages.length+':'+d.pages[0].objects.length})")
        print('templates', n, names)
        await pg.click('#bMenu'); await pg.click('text=＋ New canvas'); await pg.wait_for_timeout(400)
        await pg.screenshot(path='/tmp/v3a.png')
        await pg.click('#shBody button.preset:has-text("Boss card")'); await pg.wait_for_timeout(500)
        await pg.screenshot(path='/tmp/v3b.png')
        # save template (no artifact cap -> local)
        await pg.click('#bMenu'); await pg.click('text=Save as template'); await pg.wait_for_timeout(200)
        await pg.click('button:has-text("Save template")'); await pg.wait_for_timeout(400)
        print('toast', await pg.inner_text('#toast'), 'mine', await pg.evaluate("__fb.myTemplates.length"))
        print('errors', errs); await b.close()
asyncio.run(main())
