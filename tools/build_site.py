"""Build the installable copy (site/) from index.html: home-screen icon, manifest, offline cache.
Same app, same code; outside the Claude app the Claude-only parts (AI studio, Forge, shared library) explain themselves."""
import pathlib, hashlib, json
root=pathlib.Path(__file__).resolve().parent.parent; site=root/'site'
CDN='https://cdn.jsdelivr.net/gh/duffpowell-commits/Foxboard@main/site'
html=(root/'index.html').read_text()
head='''<link rel="manifest" href="manifest.webmanifest">
<link rel="icon" href="CDN/icon-32.png">
<link rel="apple-touch-icon" href="CDN/icon-180.png">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Foxboard">
'''
html=html.replace('<title>Foxboard</title>','<title>Foxboard</title>\n'+head.replace('CDN',CDN),1)
ver=hashlib.sha256(html.encode()).hexdigest()[:10]
html=html.replace('</body>',"<script>if('serviceWorker' in navigator) addEventListener('load',()=>navigator.serviceWorker.register('sw.js').catch(()=>{}));</script>\n</body>",1)
(site/'index.html').write_text(html)
(site/'manifest.webmanifest').write_text(json.dumps({"name":"Foxboard","short_name":"Foxboard","start_url":"./","scope":"./","display":"standalone","orientation":"portrait",
 "background_color":"#0b0c12","theme_color":"#0b0c12","description":"Phone art editor: layers, pixel art, frames, magic eraser, elements, export.",
 "icons":[{"src":CDN+"/icon-192.png","sizes":"192x192","type":"image/png"},{"src":CDN+"/icon-512.png","sizes":"512x512","type":"image/png"},{"src":CDN+"/icon-512.png","sizes":"512x512","type":"image/png","purpose":"maskable"}]},indent=1))
(site/'sw.js').write_text(f"""const C='foxboard-{ver}', FILES=['./','index.html','manifest.webmanifest'];
self.addEventListener('install',e=>{{e.waitUntil(caches.open(C).then(c=>c.addAll(FILES)));self.skipWaiting();}});
self.addEventListener('activate',e=>{{e.waitUntil(caches.keys().then(k=>Promise.all(k.filter(x=>x!==C).map(x=>caches.delete(x)))));self.clients.claim();}});
self.addEventListener('fetch',e=>{{const r=e.request; if(r.method!=='GET') return;
  e.respondWith(fetch(r).then(res=>{{ if(res.ok&&(new URL(r.url).origin===location.origin||r.url.includes('fonts.g')||r.url.includes('cdn.jsdelivr.net'))){{ const cp=res.clone(); caches.open(C).then(c=>c.put(r,cp)); }} return res; }}).catch(()=>caches.match(r).then(m=>m||caches.match('index.html'))));}});
""")
# tiny host bundle (Vercel): a loader that pulls the real app from jsDelivr, so every push to main ships
host=site/'host'; host.mkdir(exist_ok=True)
loader=f'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover">
<meta name="theme-color" content="#0b0c12"><title>Foxboard</title>
{head.replace('CDN',CDN)}</head><body style="margin:0;background:#0b0c12;color:#dae0e5;font:16px system-ui;display:flex;align-items:center;justify-content:center;height:100vh">
<div id="ld">🦊 Loading Foxboard…</div>
<script>
(function(){{ var U=(new URLSearchParams(location.search).get('src'))||'{CDN}/index.html';
 fetch(U,{{cache:'no-cache'}}).then(function(r){{ if(!r.ok) throw 0; return r.text(); }}).then(function(t){{ document.open(); document.write(t); document.close(); }})
 .catch(function(){{ document.getElementById('ld').textContent='Foxboard needs the internet the first time. Check your connection and reopen.'; }}); }})();
</script></body></html>'''
(host/'index.html').write_text(loader)
(host/'manifest.webmanifest').write_text((site/'manifest.webmanifest').read_text())
(host/'sw.js').write_text((site/'sw.js').read_text())
(host/'vercel.json').write_text('{ "headers": [ { "source": "/(.*)", "headers": [ { "key": "Cache-Control", "value": "no-cache" } ] } ] }')
(site/'_headers').write_text("/sw.js\n  Cache-Control: no-cache\n/index.html\n  Cache-Control: no-cache\n")
print('built site/ version',ver)
print('after pushing to main, purge the CDN copy: curl -s https://purge.jsdelivr.net/gh/duffpowell-commits/Foxboard@main/site/index.html')
