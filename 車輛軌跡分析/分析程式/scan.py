import sys, numpy as np
from PIL import Image
def runs(a, off):
    r = []
    for x in np.nonzero(a)[0]+off:
        if r and x-r[-1][1] <= 3: r[-1][1] = x
        else: r.append([x, x])
    return [(int(a_), int(b_)) for a_, b_ in r]
def scan(png, rows=(), cols=(), xr=(0, 99999), yr=(0, 99999), thr=200):
    im = np.array(Image.open(png).convert('L'))
    for y in rows: print('row y=%d' % y, runs(im[y, xr[0]:xr[1]] < thr, xr[0]))
    for x in cols: print('col x=%d' % x, runs(im[yr[0]:yr[1], x] < thr, yr[0]))
if __name__ == '__main__':
    png = sys.argv[1]; rows = eval(sys.argv[2]); cols = eval(sys.argv[3])
    xr = eval(sys.argv[4]) if len(sys.argv) > 4 else (0, 99999); yr = eval(sys.argv[5]) if len(sys.argv) > 5 else (0, 99999)
    scan(png, rows, cols, xr, yr)
