import sys, gt
def best(tile, step=0.01, w=0.02):
    y, x = map(int, tile.split('_')); lat0, lon0 = y / 20, x / 20; best = None
    for i in range(4):
        for j in range(4):
            bb = (round(lon0 + j * step, 4), round(lat0 + i * step, 4), round(lon0 + j * step + w, 4), round(lat0 + i * step + w, 4))
            n = len(gt.load(bb))
            if not best or n > best[0]: best = (n, bb)
    return best
for t in sys.argv[1:]: print(t, best(t))
