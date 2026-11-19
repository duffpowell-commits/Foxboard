"""Magic eraser: brush over an object, tap Erase, it's gone and the gap is filled from the surroundings."""
import asyncio, pathlib, sys
from playwright.async_api import async_playwright
APP = (pathlib.Path(__file__).resolve().parent.parent / 'index.html').as_uri()

# 96x96 diagonal-stripe texture (period 8, two colors) with a solid red 20x20 square at (38,38)
MAKE = """(()=>{const W=96,H=96,c=document.createElement('canvas');c.width=W;c.height=H;const g=c.getContext('2d');
 const id=g.createImageData(W,H),d=id.data;
 for(let y=0;y<H;y++)for(let x=0;x<W;x++){const i=(y*W+x)*4,a=((x+y)>>2)&1; d[i]=a?40:200;d[i+1]=a?90:180;d[i+2]=a?160:60;d[i+3]=255;
   if(x>=38&&x<58&&y>=38&&y<58){d[i]=255;d[i+1]=0;d[i+2]=0;}}
 g.putImageData(id,0,0); return c;})()"""

results = []
def check(name, ok, extra=''):
    results.append(ok); print(('PASS ' if ok else 'FAIL ') + name + (('  ' + str(extra)) if extra else ''))

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={'width': 390, 'height': 820}, device_scale_factor=2, has_touch=True)
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto(APP); await pg.wait_for_timeout(700)
        ev = pg.evaluate

        # 1) the fill engine on its own
        r = await ev("""(()=>{ if(!window.__fb||!__fb.inpaint) return null; const c=""" + MAKE + """; const W=96,H=96;
          const d=c.getContext('2d').getImageData(0,0,W,H).data; const m=new Uint8Array(W*H);
          for(let y=36;y<60;y++)for(let x=36;x<60;x++) m[y*W+x]=1;
          const t0=performance.now(); const out=__fb.inpaint(d,W,H,m); const ms=performance.now()-t0;
          let red=0,match=0,n=0,foreign=0; const pal=new Set();
          for(let y=0;y<H;y++)for(let x=0;x<W;x++){ if(m[y*W+x]) continue; const i=(y*W+x)*4; pal.add(d[i]+','+d[i+1]+','+d[i+2]); }
          for(let y=36;y<60;y++)for(let x=36;x<60;x++){ const i=(y*W+x)*4; n++;
            if(out[i]>230&&out[i+1]<30) red++;
            if(!pal.has(out[i]+','+out[i+1]+','+out[i+2])) foreign++;
            const a=((x+y)>>2)&1; if(Math.abs(out[i]-(a?40:200))<30&&Math.abs(out[i+2]-(a?160:60))<30) match++; }
          let keptSame=true; for(let k=0;k<W*H;k++) if(!m[k]) for(let ch=0;ch<4;ch++) if(out[k*4+ch]!==d[k*4+ch]) keptSame=false;
          return {red,match:match/n,foreign,keptSame,ms:Math.round(ms)}; })()""")
        check('inpaint exists', r is not None)
        if r:
            check('no red left in the hole', r['red'] == 0, r)
            check('fill continues the stripes (>=80% match)', r['match'] >= 0.8, r)
            check('fill uses only colors from the picture (crisp)', r['foreign'] == 0, r)
            check('pixels outside the brush untouched', r['keptSame'])
            check('fast (<3 s)', r['ms'] < 3000, r['ms'])

        # 2) the real touch flow
        await ev("""(async()=>{const c=""" + MAKE + """; const src=c.toDataURL('image/png');
          __fb.doc={w:96,h:96,bg:'#000000',pixel:false,fps:8,cur:0,pages:[{id:'p1',objects:[{id:'img1',type:'image',x:0,y:0,w:96,h:96,rot:0,opacity:1,src,natW:96,natH:96,hidden:false,locked:false}]}]};
          await new Promise(r=>setTimeout(r,250)); __fb.sel='img1'; __fb.fit(); })()""")
        await pg.wait_for_timeout(300)
        await pg.click('#ctx button[data-a="edit"]') if await pg.locator('#ctx button[data-a="edit"]').count() else await ev("__fb.openProps()")
        await pg.wait_for_timeout(250)
        btn = pg.locator('#shBody button:has-text("Magic eraser")')
        check('image panel has a Magic eraser button', await btn.count() == 1)
        if await btn.count():
            await btn.click(); await pg.wait_for_timeout(250)
            check('magic bar shows', await pg.locator('#magicbar.show').count() == 1)
            for _ in range(12): await pg.click('#mgUp')
            st = await pg.locator('#stage').bounding_box(); v = await ev("__fb.view")
            scr = lambda x, y: (st['x'] + v['x'] + x * v['z'], st['y'] + v['y'] + y * v['z'])
            for yy in range(37, 60, 3):
                x0, y0 = scr(35, yy); x1, y1 = scr(61, yy)
                await pg.mouse.move(x0, y0); await pg.mouse.down(); await pg.mouse.move(x1, y1, steps=10); await pg.mouse.up()
            masked = await ev("__fb.magicMaskCount()")
            check('brush strokes mark the mask', masked > 500, masked)
            before = await ev("Array.from(__fb.renderToCanvas(1,false,0).getContext('2d').getImageData(48,48,1,1).data)")
            await pg.click('#mgErase'); await pg.wait_for_timeout(2500)
            after = await ev("Array.from(__fb.renderToCanvas(1,false,0).getContext('2d').getImageData(48,48,1,1).data)")
            check('center was red before', before[0] > 230 and before[1] < 30, before)
            check('center is not red after Erase', not (after[0] > 230 and after[1] < 30), after)
            check('mask cleared after Erase', await ev("__fb.magicMaskCount()") == 0)
            await pg.screenshot(path='/tmp/magic_after.png')
            await pg.click('#mgDone'); await pg.wait_for_timeout(150)
            check('magic bar hides on Done', await pg.locator('#magicbar.show').count() == 0)
            await pg.click('#bUndo'); await pg.wait_for_timeout(300)
            und = await ev("Array.from(__fb.renderToCanvas(1,false,0).getContext('2d').getImageData(48,48,1,1).data)")
            check('undo brings the object back', und[0] > 230 and und[1] < 30, und)

        # 3) rotated image is refused politely, not broken
        await ev("""(()=>{const d=__fb.doc; d.pages[0].objects[0].rot=0.5; __fb.doc=d; __fb.sel='img1';})()""")
        await ev("__fb.openProps()"); await pg.wait_for_timeout(200)
        if await pg.locator('#shBody button:has-text("Magic eraser")').count():
            await pg.click('#shBody button:has-text("Magic eraser")'); await pg.wait_for_timeout(200)
            check('rotated image does not open magic mode', await pg.locator('#magicbar.show').count() == 0)
        check('no page errors', not errs, errs)
        await b.close()
    print(f'\n{sum(results)}/{len(results)} passed'); sys.exit(0 if all(results) and results else 1)

asyncio.run(main())
