// node tools/claude/render.js DOC.json OUTPREFIX [scale]
// Renders every page of a Foxboard doc with Foxboard's own renderer -> OUTPREFIX_<n>.png
const {chromium}=require('playwright'); const fs=require('fs'); const path=require('path');
(async()=>{ const [docPath,out,scale='1']=process.argv.slice(2);
  const b=await chromium.launch(); const p=await b.newPage({viewport:{width:390,height:844}});
  await p.goto('file://'+path.resolve(__dirname,'../../index.html')); await p.waitForFunction(()=>window.__fb);
  const pages=await p.evaluate(async([s,k])=>{ window.__fb.useTemplate(JSON.parse(s)); await new Promise(r=>setTimeout(r,1500));
    const d=window.__fb.doc; return d.pages.map((_,i)=>window.__fb.renderToCanvas(+k,false,i).toDataURL('image/png')); },[fs.readFileSync(docPath,'utf8'),scale]);
  pages.forEach((u,i)=>fs.writeFileSync(`${out}_${i}.png`,Buffer.from(u.split(',')[1],'base64'))); console.log(pages.length,'page(s) ->',out+'_*.png'); await b.close(); })();
