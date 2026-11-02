"""Parcel-polygon evaluation. TP = detection inside (<=2 m of) a pool-flagged parcel, or within 15 m of an OSM pool point.
Recall = share of pool parcels (representative point inside the inner box) holding >= 1 detection.
Chance = same precision test after shifting every detection 250 m north+east (how often a random spot lands in a pool parcel)."""
import json, numpy as np
from shapely.geometry import Point, box
from shapely.strtree import STRtree
import parcels, gt, evalm
from areas import AREAS
M = 0.0005  # ~50 m inner margin
def load(n):
    src, bb, yr, role = AREAS[n]
    P = parcels.get(src, bb); d = json.load(open(f'cand/{n}.json'))
    import detect
    for f in d['cands']: detect.add_ratios(f)
    osm = [(p[0], p[1]) for p in gt.load(bb, ('osm',))]
    inner = box(bb[0] + M, bb[1] + M, bb[2] - M, bb[3] - M)
    return P, d['cands'], osm, inner
def in_pool(P, tree, lat, lon):
    pt = Point(lon, lat)
    return any(P[i].distance(pt) < 2e-5 for i in tree.query(pt.buffer(2e-5)))
def which_pool(P, tree, lat, lon):
    pt = Point(lon, lat)
    c = [i for i in tree.query(pt.buffer(2e-5)) if P[i].distance(pt) < 2e-5]
    return min(c, key=lambda i: P[i].distance(pt)) if c else None
def evaluate(n, det, data=None):
    """det: list of (lat, lon) already filtered/merged."""
    P, _, osm, inner = data or load(n)
    tree = STRtree(P)
    det = [d for d in det if inner.contains(Point(d[1], d[0]))]
    near_osm = evalm.near(det, osm, 15) if osm else np.zeros(len(det), bool)
    # one pool parcel confirms ONE detection (det must be ordered strongest first); a solar panel or second hit on the
    # same parcel counts as unconfirmed
    claimed, ok = set(), np.zeros(len(det), bool)
    for k, (la, lo) in enumerate(det):
        w = which_pool(P, tree, la, lo)
        if w is not None and w not in claimed: claimed.add(w); ok[k] = True
    ok |= near_osm
    sh = 250 / 110574
    chance = np.mean([in_pool(P, tree, la + sh, lo + sh * 1.2) for la, lo in det]) if det else 0
    gtP = [p for p in P if inner.contains(p.representative_point())]
    dt = STRtree([Point(lo, la) for la, lo in det]) if det else None
    found = sum(1 for p in gtP if dt is not None and len(dt.query(p, predicate='intersects')))
    return dict(area=n, n_det=len(det), tp=int(ok.sum()), prec=ok.mean() if det else 0, chance=chance,
                n_gt=len(gtP), found=found, rec=found / max(len(gtP), 1), ok=ok, det=det)
