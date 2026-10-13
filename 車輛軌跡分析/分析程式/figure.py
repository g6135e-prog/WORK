import sys; sys.path.insert(0, __file__.rsplit('/',1)[0])
from analyze import *

COL = [(220,30,30),(20,90,230),(0,150,60),(200,0,200),(230,120,0),(0,160,170)]

def seeds_from(moves, box):
    pts = []
    for mv in moves:
        p = fillet_path(mv['pts'], mv['r'])
        for q in list(p[:120:15]) + list(p[-120::15]) + list(p[::40]):
            x, y = q*K
            if box[0]+2 < x < box[2]-2 and box[1]+2 < y < box[3]-2: pts.append((int(x), int(y)))
    return pts

def draw(pno, box, results, title, out, page_png, extra_seed=(), mask=None):
    base = Image.open(page_png).convert('RGB').crop(box)
    if mask:
        ImageDraw.Draw(base).rectangle((mask[0]-box[0], mask[1]-box[1], mask[2]-box[0], mask[3]-box[1]), fill='white')
    base = Image.blend(base, Image.new('RGB', base.size, 'white'), 0.35)
    ov = Image.new('RGBA', base.size, (0,0,0,0)); g = ImageDraw.Draw(ov)
    fnt = lambda s: ImageFont.truetype(FONT, s)
    for k, r in enumerate(results):
        c = COL[k % len(COL)]
        geoms = r['env'].geoms if hasattr(r['env'], 'geoms') else [r['env']]
        for e in geoms:
            xy = to_px(e.exterior.coords, box)
            g.polygon(xy, fill=c+(55,), outline=c+(255,))
            g.line(xy, fill=c+(255,), width=3)
        w = wheels(r['sim'])
        for nm in ('FL', 'FR', 'RL', 'RR'):
            g.line(to_px(w[nm], box), fill=c+(200,), width=1)
        g.line(to_px(r['sim']['F'], box), fill=(40,40,40,220), width=1)
        # vehicle outline at start and end
        for i in (int(len(r['sim']['F'])*0.08), len(r['sim']['F'])-1):
            bp = body_poly(r['sim'], i)
            g.line(to_px(list(bp.exterior.coords), box), fill=(0,0,0,255), width=3)
        # arrow at end
        F = r['sim']['F']; a = F[-1]; b = F[-40]; d = (a-b)/np.linalg.norm(a-b); n = np.array([-d[1], d[0]])
        tip = a + d*1.6
        g.polygon(to_px([tip, a+n*0.9, a-n*0.9], box), fill=c+(255,))
    base = Image.alpha_composite(base.convert('RGBA'), ov)
    g = ImageDraw.Draw(base)
    # markers + legend
    circ = '①②③④⑤⑥⑦⑧'
    for k, r in enumerate(results):
        c = COL[k % len(COL)]
        x, y = r['loc'] if r.get('turn', True) else to_px([r['sim']['F'][len(r['sim']['F'])//2]], box)[0]
        g.ellipse((x-16, y-16, x+16, y+16), fill='white', outline=c, width=4)
        g.text((x-11, y-14), str(k+1), fill=c, font=fnt(26))
    rows = []
    for k, r in enumerate(results):
        t = f"{k+1}. {r['tag']}"
        t += f"　最小淨距 {r['clr']:.2f} m" if r.get('turn', True) else f"　{r.get('note','')}"
        rows.append(t)
    tw = max(g.textlength(t, font=fnt(26)) for t in rows)
    y0 = 72
    g.rectangle((10, y0, 30+tw+30, y0+16+36*len(rows)), fill='white', outline='black', width=3)
    for k, t in enumerate(rows):
        c = COL[k % len(COL)]
        g.rectangle((18, y0+14+36*k, 38, y0+34+36*k), fill=c)
        g.text((46, y0+8+36*k), t, fill='black', font=fnt(26))
    # spec box
    W, H = base.size
    spec = ['設計車種：消防車(水箱車)', f"全長 {VEH['L']:.2f}m　車寬 {VEH['W']:.2f}m",
            f"軸距 {VEH['WB']:.2f}m　輪距 {VEH['TRACK']:.2f}m", f"前懸 {VEH['FOH']:.2f}m　後懸 {VEH['ROH']:.2f}m",
            f"最大轉向角 {VEH['STEER']:.0f}°", '色帶：車身掃掠範圍　細線：輪跡', '黑框：車輛位置　○：最小淨距處']
    bw = 400; bh = 34*len(spec)+20
    g.rectangle((W-bw-12, H-bh-12, W-12, H-12), fill='white', outline='black', width=3)
    for i, t in enumerate(spec):
        g.text((W-bw, H-bh+i*34), t, fill='black', font=fnt(25))
    # scale bar 10 m
    sx, sy = 20, H-40; L = 10*K
    g.rectangle((sx, sy-40, sx+L+90, sy+28), fill='white')
    for i in range(5):
        g.rectangle((sx+i*L/5, sy, sx+(i+1)*L/5, sy+12), fill='black' if i % 2 == 0 else 'white', outline='black')
    g.text((sx, sy-34), '0', fill='black', font=fnt(22)); g.text((sx+L-20, sy-34), '10m', fill='black', font=fnt(22))
    base.convert('RGB').save(out, quality=92)
