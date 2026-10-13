import sys, math, numpy as np, cv2
sys.path.insert(0, __file__.rsplit('/',1)[0])
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Polygon, MultiPolygon, LineString
from lr import render
from sim import *

SCR = __file__.rsplit('/',2)[0]
PDF = SCR + '/in/design.pdf'
FONT = '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc'
OBST_LAYERS = ['01-7', '94224_中央分隔島', '底圖|94218_人行道', '0']

def obstacles(pno, box, seeds, close_px=15):
    x0, y0, x1, y1 = box
    im = np.array(render(PDF, pno, OBST_LAYERS, mode='stroke', width=2))[y0:y1, x0:x1]
    black = (im < 128).astype(np.uint8)
    region = np.zeros((im.shape[0]+2, im.shape[1]+2), np.uint8)
    work = (1-black).astype(np.uint8)*255
    for sx, sy in seeds:
        cx, cy = sx-x0, sy-y0
        if work[cy, cx] == 255:
            cv2.floodFill(work, region, (cx, cy), 128)
    reg = (work == 128).astype(np.uint8)
    ker = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2*close_px+1, 2*close_px+1))
    regc = cv2.morphologyEx(reg, cv2.MORPH_CLOSE, ker)
    obst = (black == 1) & (regc == 0)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(obst.astype(np.uint8), 8)
    keep = np.zeros(n, bool); keep[1:] = stats[1:, cv2.CC_STAT_AREA] >= 40
    obst = keep[lab]
    return obst, regc

def to_px(pts_m, box):
    return [(x*K-box[0], y*K-box[1]) for x, y in pts_m]

def poly_mask(poly, shape, box):
    m = np.zeros(shape, np.uint8)
    geoms = poly.geoms if isinstance(poly, MultiPolygon) else [poly]
    for g in geoms:
        cv2.fillPoly(m, [np.round(np.array(to_px(g.exterior.coords, box))).astype(np.int32)], 1)
    return m.astype(bool)

def clearance(env, obst, box):
    dt = cv2.distanceTransform((~obst).astype(np.uint8), cv2.DIST_L2, 5)
    m = poly_mask(env, obst.shape, box)
    if (m & obst).any():
        ys, xs = np.nonzero(m & obst); return 0.0, (xs[0], ys[0])
    # distance from envelope boundary to nearest obstacle
    dtv = np.where(m, np.inf, dt)
    # restrict to ring just outside envelope
    ring = cv2.dilate(m.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) & ~m
    vals = np.where(ring, dt, np.inf)
    i = np.argmin(vals); y, x = np.unravel_index(i, vals.shape)
    return float(vals[y, x])/K, (x, y)

def run(pno, box, moves, seeds):
    obst, reg = obstacles(pno, box, seeds)
    res = []
    for mv in moves:
        path = fillet_path(mv['pts'], mv['r'])
        s = simulate(path)
        env = envelope(s)
        c, loc = clearance(env, obst, box)
        res.append(dict(mv, sim=s, env=env, clr=c, loc=loc, steer=float(s['steer'].max())))
    return res, obst, reg
