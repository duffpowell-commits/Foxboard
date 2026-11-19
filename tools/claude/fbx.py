#!/usr/bin/env python3
"""Claude <-> Foxboard link. Foxboard's shared library lives in its artifact database, which
only Claude's ArtifactData tool (signed in as Duff) can reach. This script does the packing;
the ArtifactData tool does the transport. URL: https://claude.ai/artifact/8yKrPwMSvkXuyEDM8L8eu4

  push-image IMG NAME OUTDIR [--title T] [--sub S] [--font CSS] [--color HEX] [--by WHO]
      Wraps one picture (plus optional title/subtitle text layers) as an editable Foxboard doc.
  push-doc DOC.json PREVIEW.png OUTDIR [--by WHO]
      Packs any Foxboard doc (layers, frames) you built yourself.
  pull ITEM_ID DUMPDIR OUT.json
      Rebuilds a library item from an ArtifactData read with out_dir=DUMPDIR
      (read library/ITEM_ID, then query libchunks where item == ITEM_ID).

push-* prints the ArtifactData "batch" writes (absolute file_paths) and writes OUTDIR/writes.json.
Rules: chunk <=180k chars, batch body <=1 MiB (split the writes list if bigger), <=50 writes.
"""
import sys, json, io, base64, uuid, time, os, argparse, glob
C = 180000

def _img_src(im, fmt):
    b = io.BytesIO()
    if fmt == 'png': im.save(b, 'PNG', optimize=True); m = 'image/png'
    else: im.convert('RGB').save(b, 'JPEG', quality=86); m = 'image/jpeg'
    return 'data:%s;base64,%s' % (m, base64.b64encode(b.getvalue()).decode())

def _thumb(im):
    t = im.convert('RGBA'); t.thumbnail((128, 128)); b = io.BytesIO(); t.save(b, 'PNG')
    return 'data:image/png;base64,' + base64.b64encode(b.getvalue()).decode()

def pack(doc, thumb, outdir, by=''):
    js = json.dumps(doc, separators=(',', ':'))
    parts = [js[i:i + C] for i in range(0, len(js), C)]
    iid = uuid.uuid4().hex[:16]
    os.makedirs(outdir, exist_ok=True); W = []
    for n, p in enumerate(parts):
        fp = os.path.abspath(f'{outdir}/chunk_{n}.json')
        json.dump({'item': iid, 'n': n, 'data': p}, open(fp, 'w'))
        W.append({'op': 'set', 'collection': 'libchunks', 'doc_id': f'{iid}_{n}', 'file_path': fp})
    fp = os.path.abspath(f'{outdir}/meta.json')
    json.dump({'name': doc['name'], 'w': doc['w'], 'h': doc['h'], 'frames': len(doc['pages']),
               'pixel': bool(doc.get('pixel')), 'by': by, 'at': int(time.time() * 1000),
               'thumb': thumb, 'chunks': len(parts)}, open(fp, 'w'))
    W.append({'op': 'set', 'collection': 'library', 'doc_id': iid, 'file_path': fp})  # meta LAST
    json.dump(W, open(f'{outdir}/writes.json', 'w'))
    sys.stderr.write(f'item {iid}: {len(js)} chars, {len(parts)} chunks\n')
    return iid, W

def push_image(a):
    from PIL import Image
    im = Image.open(a.img); fmt = 'png' if im.mode in ('RGBA', 'LA', 'P') else 'jpg'
    im = im.convert('RGBA' if fmt == 'png' else 'RGB')
    if abs(im.width / im.height - 16 / 9) < 0.05 and im.width != 1920: im = im.resize((1920, 1080))
    W, H = im.size; u = lambda: uuid.uuid4().hex[:8]
    objs = [{'id': u(), 'type': 'image', 'name': 'Art', 'x': 0, 'y': 0, 'w': W, 'h': H, 'rot': 0, 'opacity': 1,
             'src': _img_src(im, fmt), 'natW': W, 'natH': H, 'hidden': False, 'locked': False}]
    def text(t, size, y, sw, fill, bold):
        return {'id': u(), 'type': 'text', 'text': t, 'size': size, 'font': a.font, 'bold': bold, 'italic': False,
                'align': 'center', 'fill': fill, 'stroke': '#000000', 'strokeW': sw, 'rot': 0, 'opacity': 1,
                'x': W // 12, 'y': y, 'w': W - W // 6, 'h': 0, 'hidden': False, 'locked': False}
    if a.title: objs.append(text(a.title, min(W // 16, int(W * 1.35 / max(1, len(a.title)))), H // 18, 10, a.color, True))
    if a.sub: objs.append(text(a.sub, max(24, W // 40), H - H // 8, 6, '#ffffff', False))
    doc = {'name': a.name, 'w': W, 'h': H, 'bg': '#000000', 'pixel': False, 'grid': False, 'onion': False,
           'fps': 8, 'cur': 0, 'pages': [{'id': u(), 'objects': objs}]}
    return pack(doc, _thumb(im), a.outdir, a.by)

def push_doc(a):
    from PIL import Image
    return pack(json.load(open(a.doc)), _thumb(Image.open(a.preview)), a.outdir, a.by)

def pull(a):
    files = [f for f in glob.glob(f'{a.dumpdir}/**/*.json', recursive=True)]
    meta = chunks = None; parts = {}
    for f in files:
        d = json.load(open(f)); d = d.get('data', d) if 'item' not in d and 'chunks' not in d else d
        if os.path.basename(f) == f'{a.item}.json' and 'chunks' in d: meta = d
        elif d.get('item') == a.item: parts[d['n']] = d['data']
    if meta is None: sys.exit('meta library/%s not found in %s' % (a.item, a.dumpdir))
    if len(parts) != meta['chunks']: sys.exit('have %d of %d chunks' % (len(parts), meta['chunks']))
    doc = json.loads(''.join(parts[i] for i in range(meta['chunks'])))
    json.dump(doc, open(a.out, 'w')); print(a.out, doc['name'], doc['w'], 'x', doc['h'], len(doc['pages']), 'page(s)')

if __name__ == '__main__':
    p = argparse.ArgumentParser(); s = p.add_subparsers(dest='cmd', required=True)
    q = s.add_parser('push-image'); q.add_argument('img'); q.add_argument('name'); q.add_argument('outdir')
    q.add_argument('--title', default=''); q.add_argument('--sub', default='')
    q.add_argument('--font', default='Cinzel, Georgia, serif'); q.add_argument('--color', default='#ffffff')
    q.add_argument('--by', default='Claude')
    q = s.add_parser('push-doc'); q.add_argument('doc'); q.add_argument('preview'); q.add_argument('outdir'); q.add_argument('--by', default='Claude')
    q = s.add_parser('pull'); q.add_argument('item'); q.add_argument('dumpdir'); q.add_argument('out')
    a = p.parse_args()
    if a.cmd == 'pull': pull(a)
    else:
        iid, W = (push_image if a.cmd == 'push-image' else push_doc)(a)
        print(json.dumps(W))
