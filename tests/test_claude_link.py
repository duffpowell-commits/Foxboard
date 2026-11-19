"""Round trip for tools/claude/fbx.py: push-image packs a doc into library/libchunks writes,
pull rebuilds the same doc from those files (as ArtifactData out_dir would save them)."""
import subprocess, json, os, sys, tempfile, shutil
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FBX = os.path.join(ROOT, 'tools', 'claude', 'fbx.py')

def main():
    t = tempfile.mkdtemp()
    try:
        Image.new('RGB', (1600, 900), (40, 20, 20)).save(f'{t}/a.png')
        out = subprocess.run([sys.executable, FBX, 'push-image', f'{t}/a.png', 'Test art', f'{t}/out',
                              '--title', 'HELLO'], capture_output=True, text=True, check=True).stdout
        W = json.loads(out)
        assert W[-1]['collection'] == 'library', 'meta must be written last'
        iid = W[-1]['doc_id']
        dump = f'{t}/dump'
        for w in W:  # mimic ArtifactData out_dir layout: <dir>/<collection>/<doc_id>.json
            os.makedirs(f"{dump}/{w['collection']}", exist_ok=True)
            shutil.copy(w['file_path'], f"{dump}/{w['collection']}/{w['doc_id']}.json")
        for w in W[:-1]:
            assert len(json.load(open(w['file_path']))['data']) <= 180000
        subprocess.run([sys.executable, FBX, 'pull', iid, dump, f'{t}/doc.json'], check=True, capture_output=True)
        doc = json.load(open(f'{t}/doc.json'))
        assert doc['name'] == 'Test art' and (doc['w'], doc['h']) == (1920, 1080), doc['w']
        objs = doc['pages'][0]['objects']
        assert objs[0]['type'] == 'image' and objs[0]['src'].startswith('data:image/')
        assert objs[1]['type'] == 'text' and objs[1]['text'] == 'HELLO'
        print('claude link round trip: PASS')
    finally:
        shutil.rmtree(t)

if __name__ == '__main__':
    main()
