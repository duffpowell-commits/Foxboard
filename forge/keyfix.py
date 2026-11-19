"""Make a Forge render's background EXACTLY the key colour so game importers cut it cleanly."""
import colorsys
from PIL import Image


def keyfix(im, key):
    im = im.convert("RGB"); px = im.load(); w, h = im.size
    border = [px[x, 0] for x in range(w)] + [px[x, h - 1] for x in range(w)] + [px[0, y] for y in range(h)] + [px[w - 1, y] for y in range(h)]
    ref = tuple(sorted(c[i] for c in border)[len(border) // 2] for i in range(3))
    kc = tuple(int(key[i:i + 2], 16) for i in (1, 3, 5)); tol = 60
    near = lambda c: sum((c[i] - ref[i]) ** 2 for i in range(3)) <= tol * tol
    seen = set(); stack = [(x, 0) for x in range(w)] + [(x, h - 1) for x in range(w)] + [(0, y) for y in range(h)] + [(w - 1, y) for y in range(h)]
    while stack:
        x, y = stack.pop()
        if (x, y) in seen or not (0 <= x < w and 0 <= y < h): continue
        seen.add((x, y))
        if not near(px[x, y]): continue
        px[x, y] = kc; stack += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
    # Pass 2: enclosed key-tinted patches the border flood can't reach (shadow between legs, gaps under arms).
    # A pixel is "key-ish" when its hue is within 45 deg of the key's and it is saturated and bright enough;
    # muted subject colours (a dark green coat on a green key) stay. Blobs under 12 px are left alone.
    kh = colorsys.rgb_to_hsv(*(v / 255 for v in kc))[0]
    def keyish(c):
        if c == kc: return False
        hh, s, v = colorsys.rgb_to_hsv(c[0] / 255, c[1] / 255, c[2] / 255)
        d = abs(hh - kh); d = min(d, 1 - d)
        return d <= 45 / 360 and s >= 0.5 and v >= 0.35
    done = set()
    for y0 in range(h):
        for x0 in range(w):
            if (x0, y0) in done or not keyish(px[x0, y0]): continue
            blob, st = [], [(x0, y0)]; done.add((x0, y0))
            while st:
                x, y = st.pop(); blob.append((x, y))
                for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if 0 <= n[0] < w and 0 <= n[1] < h and n not in done and keyish(px[n]):
                        done.add(n); st.append(n)
            if len(blob) >= 12:
                for q in blob: px[q] = kc
    return im
