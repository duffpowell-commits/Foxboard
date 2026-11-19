"""Installable copy (site/) for iPhone/Android home screens: builds, serves, installs, works without Claude, saves files."""
import asyncio, os, pathlib, subprocess, sys, threading, http.server, functools
from playwright.async_api import async_playwright
ROOT = pathlib.Path(__file__).resolve().parent.parent; SITE = ROOT / 'site'
res = []
def check(n, ok, x=''):
    res.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + n + (('  ' + str(x)) if x != '' else ''))
need = ['index.html', 'manifest.webmanifest', 'sw.js', 'icon-180.png', 'icon-192.png', 'icon-512.png']
check('site files present', all((SITE / f).exists() for f in need), [f for f in need if not (SITE / f).exists()])
if all((SITE / f).exists() for f in need):
    built = (SITE / 'index.html').read_text(); src = (ROOT / 'index.html').read_text()
    check('site matches current index.html (run tools/build_site.py)', src.split('<title>Foxboard</title>')[1][:2000] in built or 'apple-touch-icon' in built and len(built) - len(src) < 2000, len(built) - len(src))
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 8799), functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(SITE)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    async def main():
        async with async_playwright() as p:
            for eng in ['chromium', 'webkit']:
                b = await getattr(p, eng).launch(); ctx = await b.new_context(**p.devices['iPhone 13' if eng == 'webkit' else 'Pixel 7']); pg = await ctx.new_page(); errs = []
                pg.on('pageerror', lambda e: errs.append(str(e)))
                await pg.goto('http://127.0.0.1:8799/'); await pg.wait_for_timeout(1200)
                check(f'{eng}: apple icon + manifest linked', await pg.evaluate("!!document.querySelector('link[rel=apple-touch-icon]') && !!document.querySelector('link[rel=manifest]')"))
                check(f'{eng}: offline worker registered', await pg.evaluate("navigator.serviceWorker.getRegistrations().then(r=>r.length)") >= 1)
                await pg.click('#tAI'); await pg.wait_for_timeout(300)
                check(f'{eng}: Claude-only parts explain themselves', await pg.locator('#shBody .cloudnote').count() == 1)
                await pg.click('#shClose'); await pg.click('#bExport'); await pg.wait_for_timeout(300)
                async with pg.expect_download(timeout=6000) as dl:
                    await pg.click('#shBody button:has-text("Save image")')
                check(f'{eng}: export saves a file', (await dl.value).suggested_filename.endswith('.png'))
                check(f'{eng}: no page errors', not errs, errs)
                await b.close()
    asyncio.run(main()); srv.shutdown()
print(f'\n{sum(res)}/{len(res)} passed'); sys.exit(0 if res and all(res) else 1)
