import math,random
random.seed(7)
K="#0d0d10"
def gear(cx,cy,r1,r2,n):
    p=[]
    for i in range(n*2):
        a=math.pi*i/n-math.pi/2; r=r1 if i%2==0 else r2
        p.append(f"{cx+r*math.cos(a):.1f},{cy+r*math.sin(a):.1f}")
    return "M"+" L".join(p)+"Z"
def hatch(pts,ang,ln,w=2.4,col=K,op=.55):
    s=""
    for (x,y) in pts:
        a=math.radians(ang+random.uniform(-12,12)); l=ln*random.uniform(.7,1.2)
        s+=f"M{x:.0f},{y:.0f} l{l*math.cos(a):.1f},{l*math.sin(a):.1f} "
    return f'<path d="{s}" stroke="{col}" stroke-width="{w}" stroke-linecap="round" opacity="{op}"/>'
def fang(x,y,w,h,down=True):
    t=y+h if down else y-h
    return f"M{x-w/2:.1f},{y} Q{x-w/6:.1f},{(y+t)/2:.1f} {x+w*.12:.1f},{t:.1f} Q{x+w/4:.1f},{(y+t)/2:.1f} {x+w/2:.1f},{y} Z "
up="".join(fang(x,452+abs(x-300)*.12,w,h) for x,w,h in [(244,20,26),(266,22,40),(290,18,30),(310,18,30),(334,22,40),(356,20,26)])
lo="".join(fang(x,548-abs(x-300)*.25,w,h,False) for x,w,h in [(256,18,22),(280,18,30),(300,16,22),(320,18,30),(344,18,22)])
fur_cheek_l=[(185+random.uniform(0,40),330+random.uniform(0,80)) for _ in range(14)]
fur_cheek_r=[(375+random.uniform(0,40),330+random.uniform(0,80)) for _ in range(14)]
fur_fore=[(230+random.uniform(0,140),215+random.uniform(0,45)) for _ in range(16)]
g=f'''<g id="tfox">
 <path d="M128,250 L160,170 L198,188 L232,110 L268,150 L300,78 L334,140 L372,96 L404,180 L440,160 L474,250 Z" fill="#2f4877" stroke="{K}" stroke-width="7" stroke-linejoin="round"/>
 <path d="M160,170 L205,250 M232,110 L250,250 M300,78 L290,200 M372,96 L350,240 M404,180 L395,250 M198,188 L250,230 M268,150 L300,200 M334,140 L300,200" stroke="#86a6d8" stroke-width="3.5" opacity=".75"/>
 <path d="M196,262 Q148,180 150,86 Q226,118 272,196 Z" fill="#b5532a" stroke="{K}" stroke-width="7" stroke-linejoin="round"/>
 <path d="M200,240 Q166,178 166,112 Q216,138 252,196 Z" fill="#1b1310"/>
 {hatch([(172+i*9,150+i*8) for i in range(8)],-30,22,2.2,"#efe2c8",.5)}
 <path d="M404,262 Q452,180 450,86 Q374,118 328,196 Z" fill="#b5532a" stroke="{K}" stroke-width="7" stroke-linejoin="round"/>
 <path d="M400,240 Q434,178 434,112 Q384,138 348,196 Z" fill="#1b1310"/>
 <path d="M194,250 Q228,192 300,186 Q372,192 406,250 Q430,295 446,350 L420,352 L438,378 L404,382 L416,410 L382,408 Q366,450 352,470 L248,470 Q234,450 218,408 L184,410 L196,382 L162,378 L180,352 L154,350 Q170,295 194,250 Z" fill="#c2602f" stroke="{K}" stroke-width="7" stroke-linejoin="round"/>
 <path d="M396,250 Q440,300 438,352 L418,354 L432,378 L402,382 L410,404 L384,402 Q400,330 396,250 Z" fill="#2f4877" opacity=".85"/>
 {hatch(fur_fore,-90,16,2.2,K,.35)}
 {hatch(fur_cheek_l,200,20,2.4,K,.45)}
 {hatch(fur_cheek_r,-20,20,2.4,"#c9d6f0",.35)}
 <path d="M262,300 Q300,292 338,300 L322,440 Q300,452 278,440 Z" fill="#a84d24" opacity=".55"/>
 <path d="M288,330 L292,430 M312,330 L308,430" stroke="{K}" stroke-width="2.5" opacity=".4"/>
 <path d="M218,408 Q240,392 270,404 L278,440 Q300,452 322,440 L330,404 Q360,392 382,408 Q366,450 352,470 L248,470 Q234,450 218,408 Z" fill="#efe2c8" stroke="{K}" stroke-width="5" stroke-linejoin="round"/>
 {hatch([(232+i*7,412+(i%3)*8) for i in range(6)],120,16,2,K,.4)}{hatch([(330+i*7,412+(i%3)*8) for i in range(6)],60,16,2,K,.4)}
 <path d="{gear(300,248,34,26,10)}" fill="#4a6fa8" stroke="{K}" stroke-width="5" stroke-linejoin="round"/>
 <path d="M276,248 Q300,230 324,248 Q300,266 276,248 Z" fill="#cfe0ff" stroke="{K}" stroke-width="3.5"/>
 <circle cx="300" cy="248" r="7" fill="{K}"/><circle cx="302.5" cy="245.5" r="2.2" fill="#fff"/>
 <path d="M214,318 Q244,292 282,322 Q246,338 214,318 Z" fill="#f0a040" stroke="{K}" stroke-width="5.5" stroke-linejoin="round"/>
 <ellipse cx="250" cy="320" rx="4" ry="11" fill="{K}"/>
 <path d="M282,322 Q284,350 272,372" stroke="{K}" stroke-width="5" stroke-linecap="round" fill="none"/>
 <path d="M386,318 Q356,292 318,322 Q354,338 386,318 Z" fill="#f0a040" stroke="{K}" stroke-width="5.5" stroke-linejoin="round"/>
 <ellipse cx="350" cy="320" rx="4" ry="11" fill="{K}"/>
 <path d="M318,322 Q316,350 328,372" stroke="{K}" stroke-width="5" stroke-linecap="round" fill="none"/>
 <path d="M206,312 Q196,300 192,292 M394,312 Q404,300 408,292" stroke="{K}" stroke-width="5" stroke-linecap="round" fill="none"/>
 <path d="M282,426 Q300,416 318,426 Q314,446 300,450 Q286,446 282,426 Z" fill="{K}"/>
 <path d="M222,444 Q232,560 300,602 Q368,560 378,444 Z" fill="#efe2c8" stroke="{K}" stroke-width="6" stroke-linejoin="round"/>
 <path d="M228,452 Q300,472 372,452 Q358,540 300,566 Q242,540 228,452 Z" fill="#2a0b0b" stroke="{K}" stroke-width="6" stroke-linejoin="round"/>
 <path d="{up}" fill="#f3ead8" stroke="{K}" stroke-width="2.5" stroke-linejoin="round"/>
 <path d="{lo}" fill="#f3ead8" stroke="{K}" stroke-width="2.5" stroke-linejoin="round"/>
 <path d="M236,446 L150,420 M236,456 L142,462 M240,466 L160,500 M364,446 L450,420 M364,456 L458,462 M360,466 L440,500" stroke="#efe2c8" stroke-width="2.6" stroke-linecap="round"/>
</g>'''
open("tfox3.svgfrag","w").write(g)
open("fox3-solo.svg","w").write(f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="600" height="640" viewBox="0 0 600 640"><rect width="600" height="640" fill="#17171a"/><defs>{g}</defs><use xlink:href="#tfox"/></svg>')
