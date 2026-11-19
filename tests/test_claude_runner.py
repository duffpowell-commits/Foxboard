"""Claude's headless runner (tools/claude/fb.js): script -> edits -> doc JSON, PNG, exported files, Forge job files."""
import json, os, pathlib, subprocess, sys, tempfile
ROOT = pathlib.Path(__file__).resolve().parent.parent
res = []
def check(n, ok, x=''):
    res.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + n + (('  ' + str(x)) if x != '' else ''))
with tempfile.TemporaryDirectory() as td:
    td = pathlib.Path(td); sc = td / 's.js'
    sc.write_text("""
F.newDoc({w:200,h:120,bg:'#ffffff'});
const c=document.createElement('canvas');c.width=64;c.height=64;const g=c.getContext('2d');g.fillStyle='#3a6';g.fillRect(0,0,64,64);
const i=F.add('image',{src:c.toDataURL(),x:10,y:10,w:64,h:64});
const t=F.add('text',{text:'Hello',size:30}); F.set(t,{curve:40,shadow:{c:'#000000',a:.5,blur:4,x:2,y:2}});
F.element('star',{color:'#ff0000',x:120,y:10,w:60,h:60});
await save(await F.exportFile('pdf'),'out/card.pdf');
const r=F.forgeFiles({jid:'testjobxyz',mode:'edit',id:i,mask:{rects:[[20,20,20,20]]},prompt:'a red apple'});
return {layers:F.list().length, forge:Object.keys(r.files)};
""")
    p = subprocess.run(['node', str(ROOT / 'tools/claude/fb.js'), str(sc), '--out', str(td / 'doc.json'), '--png', str(td / 'prev'), '--files', str(td)], capture_output=True, text=True, timeout=120)
    check('runner exits 0', p.returncode == 0, (p.stderr or p.stdout)[-400:])
    try: out = json.loads(p.stdout)
    except Exception: out = {}
    check('script return value comes back', (out.get('ret') or {}).get('layers') == 3, out.get('ret'))
    check('doc JSON written', (td / 'doc.json').exists() and len(json.loads((td / 'doc.json').read_text())['pages'][0]['objects']) == 3)
    check('preview PNG written', (td / 'prev_0.png').exists() and (td / 'prev_0.png').stat().st_size > 500)
    pdf = td / 'out/card.pdf'
    check('exported PDF saved', pdf.exists() and pdf.read_bytes()[:5] == b'%PDF-')
    fs_ = (out.get('ret') or {}).get('forge') or []
    check('forge job files built (json + init + mask)', sorted(x.split('.', 1)[1] for x in fs_) == ['init.b64', 'json', 'mask.b64'], fs_)
    check('no page errors', not out.get('pageErrors'), out.get('pageErrors'))
print(f'\n{sum(res)}/{len(res)} passed'); sys.exit(0 if res and all(res) else 1)
