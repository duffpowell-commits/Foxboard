"""Foxboard app icon: an original geometric fox head on midnight with a lantern glow. Writes site/icon-*.png"""
from PIL import Image, ImageDraw, ImageFilter
import pathlib
S=1024; out=pathlib.Path(__file__).resolve().parent.parent/'site'
im=Image.new('RGBA',(S,S),(11,12,18,255)); d=ImageDraw.Draw(im)
# night gradient
for y in range(S):
    t=y/S; d.line([(0,y),(S,y)],fill=(int(18-8*t),int(29-17*t),int(48-30*t),255))
glow=Image.new('RGBA',(S,S),(0,0,0,0)); g=ImageDraw.Draw(glow)
g.ellipse((300,250,724,674),fill=(240,160,64,120)); glow=glow.filter(ImageFilter.GaussianBlur(120)); im.alpha_composite(glow)
d=ImageDraw.Draw(im)
R=(194,96,47); D=(140,60,28); W=(240,226,205); K=(14,16,24); A=(240,160,64)
# ears
d.polygon([(250,250),(410,420),(300,520)],fill=R); d.polygon([(774,250),(614,420),(724,520)],fill=R)
d.polygon([(285,320),(380,430),(318,480)],fill=D); d.polygon([(739,320),(644,430),(706,480)],fill=D)
# head
d.polygon([(300,420),(724,420),(800,560),(512,860),(224,560)],fill=R)
# cheeks (white)
d.polygon([(224,560),(390,600),(512,860)],fill=W); d.polygon([(800,560),(634,600),(512,860)],fill=W)
# eyes (lantern amber)
d.polygon([(350,540),(445,575),(360,590)],fill=A); d.polygon([(674,540),(579,575),(664,590)],fill=A)
# nose
d.polygon([(470,800),(554,800),(512,860)],fill=K)
for size in (512,192,180,32):
    im.resize((size,size),Image.LANCZOS).convert('RGB').save(out/f'icon-{size}.png')
print('ok')
