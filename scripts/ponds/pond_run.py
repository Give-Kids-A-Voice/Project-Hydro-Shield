"""python3 pond_run.py <name> <x0> <y0> <x1> <y1> <year> [--thr 0.7]
Find ponds in NAIP that are not on the map. Per 0.01-degree chunk: dark-NIR blobs (build_ds.blobs) scored by the pond
model (GBM + 3 CNNs, model/); keep score >= thr whose centre has no mapped water (OSM/USGS on the live site) within
30 m + the pond's radius. Writes <name>/chunks.jsonl (checkpoint) and <name>/ponds.jsonl:
[lat, lon, area_m2, score, outline [[lat, lon], ...]]."""
import sys, os, json, math, numpy as np
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, '/home/claude/ponds')
import build_ds as bd, naip
from score import score
from pyproj import Transformer
from shapely.geometry import Polygon, Point
from shapely.strtree import STRtree
from skimage import measure
name = sys.argv[1]; x0, y0, x1, y1 = map(float, sys.argv[2:6]); yr = int(sys.argv[6])
thr = float(sys.argv[sys.argv.index('--thr') + 1]) if '--thr' in sys.argv else 0.7
os.makedirs(name, exist_ok=True)
polys = bd.mapped_polys(x0, y0, x1, y1); tree = STRtree(polys) if polys else None

def chunk(c):
    cx, cy = c; bb = (cx, cy, cx + bd.STEP, cy + bd.STEP)
    for t in range(3):
        try:
            fs = naip.items(bb, yr)
            if not fs: return []
            a, tr, crs, res = naip.read(fs[0], bb); break
        except Exception:
            if t == 2: return None
    if a.shape[0] < 4 or a.size == 0: return []
    if res < 0.5:
        H, W = a.shape[1] // 2 * 2, a.shape[2] // 2 * 2
        a = a[:, :H, :W].reshape(4, H // 2, 2, W // 2, 2).mean((2, 4)).astype(np.uint8); tr = tr * tr.scale(2, 2); res *= 2
    lab, bl = bd.blobs(a, res)
    if not bl: return []
    T = Transformer.from_crs(crs, 4326, always_xy=True)
    F = np.array([b[4] for b in bl], np.float32); P = np.array([bd.patch(a, b[2], b[3]) for b in bl], np.uint8)
    s = score(F, P); out = []
    for (L, area, py, px, f), sc in zip(bl, s):
        if sc < thr: continue
        X, Y = tr * (px + 0.5, py + 0.5); lo, la = T.transform(X, Y)
        if not (cx <= lo < cx + bd.STEP and cy <= la < cy + bd.STEP): continue
        rad = math.sqrt(area / math.pi) / 111000
        if tree is not None and len(tree.query(Point(lo, la).buffer(30 / 111000 + rad), predicate='intersects')): continue
        bm = lab == L; R_, G_, B_ = (float(a[i][bm].mean()) for i in range(3))
        if G_ >= 105: continue  # artificial turf: bright green, dark in near-infrared like water
        m = np.pad(bm, 1)
        cs = measure.find_contours(m.astype(np.uint8), 0.5)
        if not cs: continue
        ring = max(cs, key=len)
        pts = [T.transform(*(tr * (q[1] - 1 + 0.5, q[0] - 1 + 0.5))) for q in ring]
        pg = Polygon(pts).simplify(1.5 / 111000)
        if pg.is_empty or pg.geom_type != 'Polygon': continue
        outl = [[round(q[1], 6), round(q[0], 6)] for q in pg.exterior.coords]
        out.append([round(la, 6), round(lo, 6), round(area), round(float(sc), 3), outl, [round(R_), round(G_), round(B_)]])
    return out

done = set(); outf = name + '/chunks.jsonl'
if os.path.exists(outf):
    for l in open(outf): done.add(tuple(json.loads(l)['c']))
cs = [(round(x, 4), round(y, 4)) for y in np.arange(y0, y1, bd.STEP) for x in np.arange(x0, x1, bd.STEP)]
todo = [c for c in cs if c not in done]
print(f'{name}: {len(cs)} chunks, {len(todo)} to do', flush=True)
with open(outf, 'a') as o, ThreadPoolExecutor(3) as ex:
    for i, (c, r) in enumerate(zip(todo, ex.map(chunk, todo))):
        if r is None: print('chunk failed', c, flush=True); continue
        o.write(json.dumps({'c': c, 'p': r}) + '\n'); o.flush()
        if i % 25 == 0: print(f'{i}/{len(todo)}', flush=True)
P = [p for l in open(outf) for p in json.loads(l)['p']]
with open(name + '/ponds.jsonl', 'w') as o:
    for p in P: o.write(json.dumps(p) + '\n')
if len(done) + len(todo) == len(cs): open(name + '/DONE', 'w').write('')
print(f'{name}: {len(P)} unmapped ponds', flush=True)
