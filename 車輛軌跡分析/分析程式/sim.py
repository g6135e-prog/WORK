import math, numpy as np
from shapely.geometry import Polygon, LineString, Point
from shapely.ops import unary_union

K = 24.48  # px per m at 200 dpi (measured from station spacing)

# 消防車 (水箱消防車) design vehicle, meters
VEH = dict(L=9.40, W=2.50, WB=5.00, FOH=1.40, ROH=3.00, TRACK=2.10, STEER=40.0)

def fillet_path(pts, radii, step=0.05):
    """pts in px; radii (m) for each interior vertex. Returns Nx2 array in metres."""
    P = [np.array(p, float)/K for p in pts]
    out = [P[0]]
    for i in range(1, len(P)-1):
        a, b, c = P[i-1], P[i], P[i+1]
        r = radii[i-1]
        u1 = (b-a)/np.linalg.norm(b-a); u2 = (c-b)/np.linalg.norm(c-b)
        cosang = np.clip(np.dot(-u1, u2), -1, 1); ang = math.acos(cosang)  # interior angle
        if r <= 0 or abs(math.pi-ang) < 1e-3:
            out.append(b); continue
        t = r/math.tan(ang/2)
        p1 = b - u1*t; p2 = b + u2*t
        cross = u1[0]*u2[1]-u1[1]*u2[0]
        n1 = np.array([-u1[1], u1[0]]) * (1 if cross > 0 else -1)
        ctr = p1 + n1*r
        a1 = math.atan2(*(p1-ctr)[::-1]); a2 = math.atan2(*(p2-ctr)[::-1])
        da = a2-a1
        while da > math.pi: da -= 2*math.pi
        while da < -math.pi: da += 2*math.pi
        out.append(p1)
        n = max(2, int(abs(da)*r/step))
        for k in range(1, n):
            th = a1+da*k/n; out.append(ctr+r*np.array([math.cos(th), math.sin(th)]))
        out.append(p2)
    out.append(P[-1])
    line = LineString(out); L = line.length
    return np.array([line.interpolate(s).coords[0] for s in np.arange(0, L, step)] + [out[-1]])

def simulate(path, veh=VEH):
    WB = veh['WB']
    F = path
    d0 = F[min(len(F)-1, int(2/0.05))]-F[0]; d0 /= np.linalg.norm(d0)
    R = [F[0]-d0*WB]
    for f in F[1:]:
        v = f-R[-1]; R.append(f - v/np.linalg.norm(v)*WB)
    R = np.array(R)
    # pre-extend: assume vehicle came straight, so front path start already straight (we start path with straight lead-in)
    H = F-R; H /= np.linalg.norm(H, axis=1)[:, None]
    N = np.stack([-H[:, 1], H[:, 0]], 1)
    # steering angle
    tang = np.gradient(F, axis=0); tang /= np.linalg.norm(tang, axis=1)[:, None]
    steer = np.degrees(np.arccos(np.clip((tang*H).sum(1), -1, 1)))
    return dict(F=F, R=R, H=H, N=N, steer=steer)

def body_poly(s, i, veh=VEH):
    F, R, H, N = s['F'][i], s['R'][i], s['H'][i], s['N'][i]
    fr = F+H*veh['FOH']; rr = R-H*veh['ROH']; w = veh['W']/2
    return Polygon([fr+N*w, fr-N*w, rr-N*w, rr+N*w])

def envelope(s, veh=VEH, every=4):
    polys = [body_poly(s, i, veh) for i in range(0, len(s['F']), every)] + [body_poly(s, len(s['F'])-1, veh)]
    return unary_union(polys).buffer(0)

def wheels(s, veh=VEH):
    t = veh['TRACK']/2
    return dict(FL=s['F']+s['N']*t, FR=s['F']-s['N']*t, RL=s['R']+s['N']*t, RR=s['R']-s['N']*t)
