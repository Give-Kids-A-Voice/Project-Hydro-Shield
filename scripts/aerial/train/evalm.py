import numpy as np, math
from scipy.spatial import cKDTree
def xy(pts, lat0):
    k = 111320 * math.cos(math.radians(lat0))
    return np.array([[p[1] * k, p[0] * 110574] for p in pts]) if len(pts) else np.zeros((0, 2))
def match(det, gt, R):
    """Greedy one-to-one matching by distance. det/gt: lists of (lat, lon). Returns (matched det idx set, matched gt idx set)."""
    if not len(det) or not len(gt): return set(), set()
    lat0 = gt[0][0]; D = xy(det, lat0); G = xy(gt, lat0)
    t = cKDTree(G); pairs = []
    for i, nb in enumerate(t.query_ball_point(D, R)):
        for j in nb: pairs.append((np.hypot(*(D[i] - G[j])), i, j))
    pairs.sort(); md, mg = set(), set()
    for d, i, j in pairs:
        if i not in md and j not in mg: md.add(i); mg.add(j)
    return md, mg
def near(det, pts, R):
    """for each det, is any of pts within R m"""
    if not len(det) or not len(pts): return np.zeros(len(det), bool)
    lat0 = pts[0][0]; t = cKDTree(xy(pts, lat0))
    d, _ = t.query(xy(det, lat0)); return d <= R
def score(det, county, other, R, shift_m=0):
    """precision: det matched one-to-one to county GT, or within R/2+10 of an OSM/spa point (those are pool-footprint centroids).
    recall: county GT matched. shift_m>0 shifts det north to estimate chance matches."""
    if shift_m: det = [(d[0] + shift_m / 110574, d[1]) for d in det]
    md, mg = match(det, county, R)
    osm_ok = near(det, other, 20)
    tp = sum(1 for i in range(len(det)) if i in md or osm_ok[i])
    return dict(n_det=len(det), n_gt=len(county), tp=tp, prec=tp / max(len(det), 1), rec=len(mg) / max(len(county), 1))
