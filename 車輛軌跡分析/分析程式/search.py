import sys; sys.path.insert(0, __file__.rsplit('/',1)[0])
from figure import *
from shapely.geometry import Point, Polygon

def obstacles2(pno, box, seeds, close_px=6):
    x0, y0, x1, y1 = box; P = 40
    im = np.array(render(PDF, pno, OBST_LAYERS, mode='curb', width=2))
    H, W = im.shape
    im = im[max(0,y0-P):min(H,y1+P), max(0,x0-P):min(W,x1+P)]
    ox, oy = max(0,x0-P), max(0,y0-P)
    black = (im < 128).astype(np.uint8)
    work = (1-black).astype(np.uint8)*255
    mask = np.zeros((im.shape[0]+2, im.shape[1]+2), np.uint8)
    for sx, sy in seeds:
        cx, cy = int(sx-ox), int(sy-oy)
        if 0 <= cx < work.shape[1] and 0 <= cy < work.shape[0] and work[cy, cx] == 255:
            cv2.floodFill(work, mask, (cx, cy), 128)
    reg = (work == 128).astype(np.uint8)
    ker = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2*close_px+1, 2*close_px+1))
    regc = cv2.morphologyEx(cv2.copyMakeBorder(reg, P, P, P, P, cv2.BORDER_REPLICATE), cv2.MORPH_CLOSE, ker)[P:-P, P:-P]
    obst = (black == 1) & (regc == 0)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(obst.astype(np.uint8), 8)
    keep = np.zeros(n, bool); keep[1:] = stats[1:, cv2.CC_STAT_AREA] >= 40
    obst = keep[lab]
    sl = (slice(y0-oy, y0-oy+(y1-y0)), slice(x0-ox, x0-ox+(x1-x0)))
    obst = obst[sl].copy(); regc = regc[sl].copy()
    # ignore a thin frame at crop border
    obst[:12, :] = obst[-12:, :] = False; obst[:, :12] = obst[:, -12:] = False
    return obst, regc

def line_isect(p, d, q, e):
    p, d, q, e = map(lambda v: np.array(v, float), (p, d, q, e))
    A = np.array([d, -e]).T
    t, _ = np.linalg.solve(A, q-p)
    return p+d*t

class Ctx:
    def __init__(s, pno, box, seeds, zone=None, extra=()):
        s.pno, s.box = pno, box
        s.obst, s.reg = obstacles2(pno, box, seeds)
        ex = np.zeros(s.obst.shape, np.uint8)
        for e in extra:
            if e[0] == 'line':
                cv2.line(ex, (int(e[1][0]-box[0]), int(e[1][1]-box[1])), (int(e[2][0]-box[0]), int(e[2][1]-box[1])), 1, 3)
            elif e[0] == 'rect':
                cv2.rectangle(ex, (int(e[1][0]-box[0]), int(e[1][1]-box[1])), (int(e[2][0]-box[0]), int(e[2][1]-box[1])), 1, 3)
        s.extra = ex.astype(bool)
        s.zone = Polygon(zone) if zone is not None else None
        if zone is not None:
            zm = np.zeros(s.obst.shape, np.uint8)
            cv2.fillPoly(zm, [np.array([(x-box[0], y-box[1]) for x, y in zone], np.int32)], 1)
            s.obst = s.obst & zm.astype(bool)
        s.obst = s.obst | s.extra
        s.dt = cv2.distanceTransform((~s.obst).astype(np.uint8), cv2.DIST_L2, 5)
    def eval(s, pts, radii):
        path = fillet_path(pts, radii)
        sim = simulate(path); env = envelope(sim)
        m = poly_mask(env, s.obst.shape, s.box)
        base = dict(sim=sim, env=env, steer=float(sim['steer'].max()), pts=pts, r=radii)
        hit = m & s.obst
        if hit.any():
            de = cv2.distanceTransform(np.pad(m.astype(np.uint8), 1), cv2.DIST_L2, 5)[1:-1, 1:-1]
            v = np.where(hit, de, -1); i = np.argmax(v); y, x = np.unravel_index(i, v.shape)
            base.update(clr=-float(v[y, x])/K, loc=(x, y)); return base
        ring = cv2.dilate(m.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) & ~m
        vals = np.where(ring, s.dt, np.inf)
        i = np.argmin(vals); y, x = np.unravel_index(i, vals.shape)
        base.update(clr=float(vals[y, x])/K, loc=(x, y)); return base

def turn(ctx, entries, exits, Rs, maxsteer=VEH['STEER'], prefer=0.35):
    """entries: list of (start_pt, dir); exits: list of (end_pt, dir) ; dir = unit travel direction."""
    best = None
    for ei, (sp, sd) in enumerate(entries):
        for xi, (ep, ed) in enumerate(exits):
            v = line_isect(sp, sd, ep, ed)
            u1 = (v-np.array(sp, float)); u1 /= np.linalg.norm(u1)
            u2 = (np.array(ep, float)-v); u2 /= np.linalg.norm(u2)
            ang = math.acos(np.clip(np.dot(-u1, u2), -1, 1))
            for R in Rs:
                if ctx.zone is not None:
                    t = R*K/math.tan(ang/2)
                    zb = ctx.zone.buffer(1.0*K)
                    if not (zb.contains(Point(*(v-u1*t))) and zb.contains(Point(*(v+u2*t)))): continue
                try:
                    r = ctx.eval([tuple(sp), tuple(v), tuple(ep)], [R])
                except Exception as ex:
                    continue
                if r['steer'] > maxsteer: continue
                # score: clearance capped at `prefer`, then prefer outer lanes (low index)
                sc = (min(r['clr'], prefer), -ei-xi, r['clr'])
                if best is None or sc > best[0]: best = (sc, r, ei, xi, R)
    sc, r, ei, xi, R = best
    r.update(entry=ei, exit=xi, R=R)
    return r

def through(ctx, pts, r=(60, 60)):
    res = ctx.eval(pts, list(r)[:len(pts)-2]); res['R'] = None
    return res

def _exit_dist(zone, p, u, step=2.0, maxd=4000):
    """distance (px) from p along direction u until leaving zone polygon."""
    d = 0.0
    while d < maxd and zone.contains(Point(*(p+u*d))): d += step
    return d

def turn_rule(ctx, entry, exit_, Rs, offs_m=(0.0, -0.25, 0.25), swings_m=np.arange(0, 5.01, 0.5),
              target=0.25, maxsteer=VEH['STEER']):
    """Lane-disciplined turn (right: outer->outer, left: inner->inner).  Before/after the
    intersection zone the vehicle stays in its lane (lateral offset only within the lane);
    inside the zone it may swing outward by `s`.  Searches swing levels in increasing order and
    returns, at the first level with any feasible path, the one whose min clearance is closest
    to (but not below) `target`.  If nothing is feasible, returns the best (max clearance) path."""
    (sp0, sd), (ep0, ed) = entry, exit_
    sd = np.array(sd, float); sd /= np.linalg.norm(sd); ed = np.array(ed, float); ed /= np.linalg.norm(ed)
    ns = np.array([-sd[1], sd[0]]); ne = np.array([-ed[1], ed[0]])
    best_bad = None
    geo = []
    for oi in offs_m:
        for oe in offs_m:
            sp = np.array(sp0, float) + ns*oi*K; ep = np.array(ep0, float) + ne*oe*K
            V = line_isect(sp, sd, ep, ed)
            dA = _exit_dist(ctx.zone, V, -sd); dB = _exit_dist(ctx.zone, V, ed)
            geo.append((oi, oe, sp, ep, V, V - sd*dA, V + ed*dB))
    bis0 = (-sd + ed); bis0 /= np.linalg.norm(bis0)
    for s in swings_m:
        feas = []
        for oi, oe, sp, ep, V, A, B in geo:
            Vs = V - bis0*s*K
            for R in Rs:
                pts = [tuple(sp), tuple(A), tuple(Vs), tuple(B), tuple(ep)]
                P = [np.array(p) for p in pts]; radii = [60.0, R, 60.0]; tl = []; ok = True
                for j in range(1, 4):
                    u1 = P[j]-P[j-1]; u2 = P[j+1]-P[j]
                    n1, n2 = np.linalg.norm(u1), np.linalg.norm(u2)
                    if n1 < 1 or n2 < 1: ok = False; break
                    ang = math.acos(np.clip(np.dot(-u1/n1, u2/n2), -1, 1))
                    tl.append(radii[j-1]*K/math.tan(ang/2) if ang < math.pi-1e-3 else 0)
                if not ok: continue
                segs = [np.linalg.norm(P[j+1]-P[j]) for j in range(4)]
                if tl[0] > segs[0] or tl[0]+tl[1] > segs[1] or tl[1]+tl[2] > segs[2] or tl[2] > segs[3]: continue
                try: r = ctx.eval(pts, radii)
                except Exception: continue
                if r['steer'] > maxsteer: continue
                r.update(entry_off=oi, exit_off=oe, swing=float(s), R=float(R), entry=0, exit=0)
                if r['clr'] >= target: feas.append(r)
                elif best_bad is None or r['clr'] > best_bad['clr']: best_bad = r
        if feas:
            feas.sort(key=lambda r: (r['clr'], abs(r['entry_off'])+abs(r['exit_off'])))
            return feas[0]
    return best_bad


def modification(ctx, env, margin_m=0.25, zone_pad_m=3.0, min_area_m2=0.1, min_depth_m=0.05):
    """Area of existing structure that must be removed so that `env` keeps `margin_m` clearance.
    Returns list of dicts {poly_px (crop coords), area_m2, depth_m, centroid_px}."""
    buf = env.buffer(margin_m, join_style=1)
    m = poly_mask(buf, ctx.obst.shape, ctx.box)
    road = ctx.reg.astype(bool)
    zm = np.zeros(m.shape, np.uint8)
    if ctx.zone is not None:
        zb = ctx.zone.buffer(zone_pad_m*K)
        cv2.fillPoly(zm, [np.array([(x-ctx.box[0], y-ctx.box[1]) for x, y in zb.exterior.coords], np.int32)], 1)
    else: zm[:] = 1
    mod = m & ~road & zm.astype(bool)
    mod = mod | (m & ctx.extra)
    dtr = cv2.distanceTransform((~road).astype(np.uint8), cv2.DIST_L2, 5)
    nr, labr, statr, _ = cv2.connectedComponentsWithStats((~road).astype(np.uint8), 8)
    n, lab, stats, cen = cv2.connectedComponentsWithStats(mod.astype(np.uint8), 8)
    out = []
    for k in range(1, n):
        area = stats[k, cv2.CC_STAT_AREA]/K/K
        if area < min_area_m2: continue
        comp = (lab == k).astype(np.uint8)
        cs, _ = cv2.findContours(comp, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        c = max(cs, key=cv2.contourArea)[:, 0, :]
        depth = float(dtr[lab == k].max())/K
        if depth < min_depth_m: continue
        ids = labr[(lab == k) & ~road]
        big = 0.0
        if ids.size:
            vals, cnt = np.unique(ids[ids > 0], return_counts=True)
            if vals.size: big = statr[vals[np.argmax(cnt)], cv2.CC_STAT_AREA]/K/K
        touches_extra = bool(((lab == k) & ctx.extra).any())
        kind = '中央分隔島／島頭' if (touches_extra or big < 40) else '轉角緣石／轉角綠帶'
        out.append(dict(kind=kind, poly_px=[tuple(map(int, q)) for q in c], area_m2=float(area), depth_m=depth,
                        centroid_px=(float(cen[k][0]), float(cen[k][1]))))
    out.sort(key=lambda d: -d['area_m2'])
    return out
