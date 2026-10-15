import sys; sys.path.insert(0, __file__.rsplit('/',1)[0])
from analyze import *


def dashed(g, pts, fill, width=2, on=10, off=7):
    pts = [np.array(p, float) for p in pts]
    carry = 0.0; draw_on = True
    for a, b in zip(pts, pts[1:]):
        L = np.linalg.norm(b-a)
        if L == 0: continue
        u = (b-a)/L; t = 0.0
        while t < L:
            seg = (on if draw_on else off) - carry
            t2 = min(L, t+seg)
            if draw_on: g.line([tuple(a+u*t), tuple(a+u*t2)], fill=fill, width=width)
            if t2 - t < seg: carry += t2-t; break
            carry = 0.0; draw_on = not draw_on; t = t2

def clearance_line(g, env, box, c):
    buf = env.buffer(0.25, join_style=1)
    gs = buf.geoms if hasattr(buf, 'geoms') else [buf]
    for e in gs:
        dashed(g, to_px(e.exterior.coords, box), c+(255,), width=2)

def draw_mods(img, mods, fnt):
    """hatch the structure area that must be removed (in-place on RGBA image)."""
    if not mods: return img
    W, H = img.size
    for md in mods:
        poly = md['poly_px']
        if len(poly) < 3: continue
        m = Image.new('L', (W, H), 0); ImageDraw.Draw(m).polygon(poly, fill=255)
        h = Image.new('RGBA', (W, H), (255, 140, 0, 90)); dh = ImageDraw.Draw(h)
        for k in range(-H, W, 10): dh.line([(k, 0), (k+H, H)], fill=(200, 0, 0, 255), width=2)
        img.paste(h, (0, 0), m)
        d = ImageDraw.Draw(img); d.line(poly+[poly[0]], fill=(200, 0, 0, 255), width=3)
        cx, cy = md['centroid_px']; t = f"修正區 退縮{md['depth_m']:.2f}m"
        tw = d.textlength(t, font=fnt(22))
        d.rectangle((cx+18, cy-14, cx+26+tw, cy+16), fill=(255, 255, 220, 255), outline=(200, 0, 0, 255), width=2)
        d.text((cx+22, cy-12), t, fill=(200, 0, 0, 255), font=fnt(22))
        d.line([(cx, cy), (cx+18, cy)], fill=(200, 0, 0, 255), width=2)
    return img

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
        if r.get('turn', True): clearance_line(g, r['env'], box, c)
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
        t += (f"　最小淨距 {r['clr']:.2f} m") if r.get('turn', True) else f"　{r.get('note','')}"
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
    spec = [f"設計車種：{VEH['name']}", f"全長 {VEH['L']:.2f}m　車寬 {VEH['W']:.2f}m",
            f"軸距 {VEH['WB']:.2f}m　輪距 {VEH['TRACK']:.2f}m", f"前懸 {VEH['FOH']:.2f}m　後懸 {VEH['ROH']:.2f}m",
            f"最小轉向半徑 {VEH['RMIN']:.2f}m", '色帶：車身掃掠範圍　細線：輪跡', '黑框：車輛位置　○：最小淨距處', '虛線：25cm淨距線']
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

def draw_layers(pno, box, results, out_prefix, page_png, mask=None):
    """Write separated layers: base (design + scale bar) and one transparent PNG per movement.
    Returns dict(base=(path,w,h), moves=[(path,x,y,w,h,color)], rows=[...])."""
    fnt = lambda s: ImageFont.truetype(FONT, s)
    base = Image.open(page_png).convert('RGB').crop(box)
    if mask:
        ImageDraw.Draw(base).rectangle((mask[0]-box[0], mask[1]-box[1], mask[2]-box[0], mask[3]-box[1]), fill='white')
    base = Image.blend(base, Image.new('RGB', base.size, 'white'), 0.35)
    g = ImageDraw.Draw(base); W, H = base.size
    sx, sy = 20, H-40; L = 10*K
    g.rectangle((sx, sy-40, sx+L+90, sy+28), fill='white')
    for i in range(5):
        g.rectangle((sx+i*L/5, sy, sx+(i+1)*L/5, sy+12), fill='black' if i % 2 == 0 else 'white', outline='black')
    g.text((sx, sy-34), '0', fill='black', font=fnt(22)); g.text((sx+L-20, sy-34), '10m', fill='black', font=fnt(22))
    bp = f'{out_prefix}_base.png'; base.save(bp, optimize=True)
    out = dict(base=(bp, W, H), moves=[], rows=[])
    for k, r in enumerate(results):
        c = COL[k % len(COL)]
        ov = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
        geoms = r['env'].geoms if hasattr(r['env'], 'geoms') else [r['env']]
        for e in geoms:
            xy = to_px(e.exterior.coords, box)
            d.polygon(xy, fill=c+(60,)); d.line(xy, fill=c+(255,), width=3)
        if r.get('turn', True): clearance_line(d, r['env'], box, c)
        w = wheels(r['sim'])
        for nm in ('FL', 'FR', 'RL', 'RR'):
            d.line(to_px(w[nm], box), fill=c+(210,), width=1)
        d.line(to_px(r['sim']['F'], box), fill=(40, 40, 40, 220), width=1)
        for i in (int(len(r['sim']['F'])*0.08), len(r['sim']['F'])-1):
            bpoly = body_poly(r['sim'], i)
            d.line(to_px(list(bpoly.exterior.coords), box), fill=(0, 0, 0, 255), width=3)
        F = r['sim']['F']; a = F[-1]; bb = F[-40]; dv = (a-bb)/np.linalg.norm(a-bb); n = np.array([-dv[1], dv[0]])
        d.polygon(to_px([a+dv*1.6, a+n*0.9, a-n*0.9], box), fill=c+(255,))
        x, y = r['loc'] if r.get('turn', True) else to_px([F[len(F)//2]], box)[0]
        d.ellipse((x-16, y-16, x+16, y+16), fill=(255, 255, 255, 255), outline=c+(255,), width=4)
        d.text((x-11, y-14), str(k+1), fill=c+(255,), font=fnt(26))
        bbx = ov.getbbox()
        x0, y0 = max(0, bbx[0]-4), max(0, bbx[1]-4); x1, y1 = min(W, bbx[2]+4), min(H, bbx[3]+4)
        mp = f'{out_prefix}_mv{k+1}.png'; ov.crop((x0, y0, x1, y1)).save(mp, optimize=True)
        out['moves'].append((mp, x0, y0, x1-x0, y1-y0, c))
        t = f"{k+1}. {r['tag']}"
        t += (f"　最小淨距 {r['clr']:.2f} m") if r.get('turn', True) else f"　{r.get('note','')}"
        out['rows'].append((t, c))
    return out
