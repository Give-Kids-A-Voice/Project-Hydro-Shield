"""Build a pond training set: dark-NIR blobs in NAIP + features + 48x48 patch, labelled by overlap with mapped water.
python3 build_ds.py <out.npz> <year> <x0> <y0> <x1> <y1> [max_chunks]
Label 1: >= 50% of the blob lies inside a mapped water area (OSM/USGS on the live site). Label 0: no mapped water
within 30 m. Blobs in between (edges of mapped water, partly mapped) are left out of training.
"""
import sys, os, json, math, random, numpy as np
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, '/home/claude/project-hydro-shield/scripts/aerial'); sys.path.insert(0, '/home/claude/news')
import naip
from scipy import ndimage
from pyproj import Transformer
from shapely.geometry import Polygon, Point
from shapely.strtree import STRtree
from shapely.ops import transform as stransform
from near import get, undelta, B

STEP = 0.01; PS = 48; SC = 4  # patch 48 px at 4x downsample from 0.3-0.6 m -> ~58-115 m wide

def mapped_polys(x0, y0, x1, y1):
    out = []
    for y in range(math.floor(y0 * 20), math.floor(y1 * 20) + 1):
        for x in range(math.floor(x0 * 20), math.floor(x1 * 20) + 1):
            k = f'{y}_{x}'; feats = [f['g'] for f in (get(B + f'water/{k}.json') or [])]
            j = get(B + f'water2/{math.floor(y / 4)}_{math.floor(x / 4)}.json.gz') or {}
            feats += [[undelta(r) for r in f['d']] for f in j.get(k, [])]
            for gg in feats:
                for ring in gg:
                    pts = [(p[1], p[0]) for p in ring]
                    if len(pts) >= 4 and pts[0] == pts[-1]:
                        try: out.append(Polygon(pts).buffer(0))
                        except Exception: pass
                    elif len(pts) >= 2:
                        from shapely.geometry import LineString; out.append(LineString(pts).buffer(0.00004))
    return out

def blobs(a, res):
    """Candidate water blobs + per-blob features. a: 4xHxW uint8."""
    r, g, b, n = [a[i].astype(np.float32) for i in range(4)]
    ndwi = (g - n) / (g + n + 1e-6); ndvi = (n - r) / (n + r + 1e-6)
    m = ndimage.binary_opening((ndwi > 0.15) & (n < 70), iterations=2)
    lab, k = ndimage.label(m)
    if not k: return lab, []
    idx = np.arange(1, k + 1); area = ndimage.sum(m, lab, idx) * res * res
    sl = ndimage.find_objects(lab)
    ring_mask = None
    out = []
    for i in np.nonzero((area >= 200) & (area <= 300000))[0]:
        L = i + 1; s = sl[i]
        y0, y1, x0, x1 = s[0].start, s[0].stop, s[1].start, s[1].stop
        pad = 12
        Y0, Y1, X0, X1 = max(0, y0 - pad), min(m.shape[0], y1 + pad), max(0, x0 - pad), min(m.shape[1], x1 + pad)
        bm = lab[Y0:Y1, X0:X1] == L
        ys, xs = np.nonzero(bm)
        if len(ys) < 10: continue
        cov = np.cov(np.vstack([xs, ys])); ev = np.linalg.eigvalsh(cov); el = math.sqrt(ev[1] / max(ev[0], 1e-6))
        fill = bm.sum() / ((np.ptp(ys) + 1) * (np.ptp(xs) + 1))
        per = bm.sum() - ndimage.binary_erosion(bm).sum()
        compact = 4 * math.pi * bm.sum() / max(per, 1) ** 2
        dil = ndimage.binary_dilation(bm, iterations=8) & ~ndimage.binary_dilation(bm, iterations=2)
        f = [math.log(area[i]), el, fill, compact]
        for band in (r, g, b, n, ndwi, ndvi):
            v = band[Y0:Y1, X0:X1]
            f += [float(v[bm].mean()), float(v[bm].std()), float(v[dil].mean()) if dil.any() else 0, float(v[dil].std()) if dil.any() else 0]
        # edge sharpness: NIR gradient on the boundary
        gm = ndimage.sobel(n[Y0:Y1, X0:X1], 0) ** 2 + ndimage.sobel(n[Y0:Y1, X0:X1], 1) ** 2
        edge = bm & ~ndimage.binary_erosion(bm)
        f += [float(np.sqrt(gm[edge]).mean()) if edge.any() else 0]
        cy, cx = ndimage.center_of_mass(lab[Y0:Y1, X0:X1] == L); cy += Y0; cx += X0
        out.append((L, float(area[i]), cy, cx, f))
    return lab, out

def patch(a, cy, cx):
    h = PS * SC // 2; cy, cx = int(cy), int(cx)
    P = np.zeros((4, PS * SC, PS * SC), np.float32)
    y0, x0 = cy - h, cx - h
    ys, xs = max(0, y0), max(0, x0); ye, xe = min(a.shape[1], y0 + 2 * h), min(a.shape[2], x0 + 2 * h)
    P[:, ys - y0:ye - y0, xs - x0:xe - x0] = a[:, ys:ye, xs:xe]
    return P.reshape(4, PS, SC, PS, SC).mean((2, 4)).astype(np.uint8)

def chunk(args):
    (cx, cy), yr, polys_tree, polys = args
    bb = (cx, cy, cx + STEP, cy + STEP)
    for t in range(3):
        try:
            fs = naip.items(bb, yr)
            if not fs: return []
            a, tr, crs, res = naip.read(fs[0], bb); break
        except Exception:
            if t == 2: return []
    if a.shape[0] < 4 or a.size == 0: return []
    if res < 0.5:  # 0.3 m -> 0.6 m like the pool model
        H, W = a.shape[1] // 2 * 2, a.shape[2] // 2 * 2
        a = a[:, :H, :W].reshape(4, H // 2, 2, W // 2, 2).mean((2, 4)).astype(np.uint8); tr = tr * tr.scale(2, 2); res *= 2
    lab, bl = blobs(a, res)
    T = Transformer.from_crs(crs, 4326, always_xy=True)
    out = []
    for L, area, py, px, f in bl:
        X, Y = tr * (px + 0.5, py + 0.5); lo, la = T.transform(X, Y)
        if not (cx <= lo < cx + STEP and cy <= la < cy + STEP): continue
        lab_ = None
        if polys_tree is not None:
            ys, xs = np.nonzero(lab == L)
            sel = np.random.default_rng(0).choice(len(ys), min(60, len(ys)), replace=False)
            pts = [T.transform(*(tr * (xs[j] + 0.5, ys[j] + 0.5))) for j in sel]
            inside = 0
            cand = polys_tree.query(Point(lo, la).buffer(0.003))
            cp = [polys[c] for c in cand]
            for q in pts:
                P_ = Point(q)
                if any(pp.contains(P_) for pp in cp): inside += 1
            fr = inside / len(pts)
            near = any(pp.distance(Point(lo, la)) < 30 / 111000 + math.sqrt(area / math.pi) / 111000 for pp in cp)
            lab_ = 1 if fr >= 0.5 else (0 if not near else -1)
        out.append(dict(lat=la, lon=lo, area=area, f=f, p=patch(a, py, px), y=lab_))
    return out

if __name__ == '__main__':
    outp, yr = sys.argv[1], int(sys.argv[2]); x0, y0, x1, y1 = map(float, sys.argv[3:7])
    mx = int(sys.argv[7]) if len(sys.argv) > 7 else 10 ** 9
    polys = mapped_polys(x0, y0, x1, y1); tree = STRtree(polys) if polys else None
    cs = [(round(x, 4), round(y, 4)) for y in np.arange(y0, y1, STEP) for x in np.arange(x0, x1, STEP)]
    random.seed(1); random.shuffle(cs); cs = cs[:mx]
    rows = []
    with ThreadPoolExecutor(6) as ex:
        for i, r in enumerate(ex.map(chunk, [(c, yr, tree, polys) for c in cs])):
            rows += r
            if i % 10 == 0: print(f'{i}/{len(cs)} chunks, {len(rows)} blobs, pos={sum(1 for x in rows if x["y"]==1)}', flush=True)
    np.savez_compressed(outp, F=np.array([x['f'] for x in rows], np.float32), P=np.array([x['p'] for x in rows], np.uint8),
                        Y=np.array([-2 if x['y'] is None else x['y'] for x in rows]), LL=np.array([[x['lat'], x['lon'], x['area']] for x in rows]))
    print('saved', outp, len(rows))
