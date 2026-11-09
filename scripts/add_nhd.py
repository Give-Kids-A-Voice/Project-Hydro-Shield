"""Fill gaps in OpenStreetMap streams with the USGS National Hydrography Dataset (NHD, high resolution).

  python3 scripts/add_nhd.py <NHD state .gdb> <water.geojsonseq> <state code, e.g. pa>

OpenStreetMap is thin on small creeks in many states (central Pennsylvania especially). NHD is the USGS survey of
every mapped stream, made from ground survey and imagery, so it includes creeks hidden under tree cover.
This appends NHD streams, canals and ditches to the OSM export, but only the stretches that OSM does not already
have: each NHD line is walked every ~10 m and a stretch is kept only where no OSM waterway or water area edge is
within ~35 m. So a creek that OSM already maps is never listed twice.

Kept: perennial and intermittent streams/rivers (FCode 46000/46003/46006), canals and ditches (336xx).
Left out: ephemeral washes (46007, dry except right after rain), pipelines and underground conduits, connectors,
and "artificial paths" (the center lines NHD draws through lakes and wide rivers, which are already water areas).

Built to fit a CI runner even for Texas and Oregon (1+ GB downloads): OSM cells are kept as one sorted int64 array
and NHD lines are read and checked in batches with numpy, so memory stays at a few GB.
"""
import json, sys
from array import array
import numpy as np
from pyogrio.raw import read as ogr_read
from pyogrio import read_info
import shapely

gdb, seq, ST = sys.argv[1], sys.argv[2], sys.argv[3]
CELL = 0.0003                      # ~33 m (lat); a stretch counts as covered if OSM is in its cell or a neighbor
STEP_DEG = 0.0001                  # walk lines every ~10 m (densify step, in degrees)
MIN_RUN_M = 40.0                   # ignore uncovered scraps shorter than this (end-of-line wiggles next to OSM)
BATCH = 200000                     # NHD features read per batch
KEEP = {46000: 'stream', 46003: 'stream', 46006: 'stream', 33600: 'canal', 33601: 'canal', 33603: 'ditch'}
W = 1 << 21                        # cell x index offset/width for packing (y, x) into one int64

def keys(lat, lon):
    return np.floor(lat / CELL).astype(np.int64) * (W * 2) + (np.floor(lon / CELL).astype(np.int64) + W)

# 1. Cells touched by OSM waterways and by the edges of OSM water areas.
buf = array('q')
def mark(c):
    c = np.asarray(c, dtype=float)[:, :2]
    if len(c) == 0: return
    if len(c) > 1:
        # fill in between vertices so long straight OSM segments still mark every cell they cross
        d = np.abs(np.diff(c, axis=0)).max(axis=1); k = np.maximum(1, (d / (CELL / 2)).astype(int))
        pts = [c[:1]] + [c[i] + (c[i + 1] - c[i]) * (np.arange(1, k[i] + 1)[:, None] / k[i]) for i in range(len(k))]
        c = np.vstack(pts)
    buf.extend(keys(c[:, 1], c[:, 0]).tolist())
def walk(g):
    t, c = g['type'], g.get('coordinates')
    if t == 'LineString': mark(c)
    elif t in ('MultiLineString', 'Polygon'): [mark(r) for r in c]
    elif t == 'MultiPolygon': [mark(r) for p in c for r in p]
    elif t == 'GeometryCollection': [walk(x) for x in g['geometries']]
with open(seq) as f:
    for line in f:
        line = line.strip().lstrip('\x1e')
        if not line: continue
        g = json.loads(line).get('geometry') or {}
        if g.get('type') in (None, 'Point', 'MultiPoint'): continue
        walk(g)
osm = np.unique(np.frombuffer(buf, dtype=np.int64)); del buf
print('OSM water cells:', len(osm))
NB = np.array([dy * (W * 2) + dx for dy in (-1, 0, 1) for dx in (-1, 0, 1)], dtype=np.int64)

def covered(lat, lon):
    k = keys(lat, lon)
    hit = np.zeros(len(k), dtype=bool)
    for n in NB:
        q = k + n; i = np.searchsorted(osm, q); i[i >= len(osm)] = 0
        hit |= osm[i] == q
    return hit

def seg_len_m(c):
    dl = np.diff(c, axis=0)
    return np.hypot(dl[:, 1] * 110574, dl[:, 0] * 111320 * np.cos(np.radians(c[:-1, 1])))

# 2. NHD flowlines, in batches.
total = read_info(gdb, layer='NHDFlowline')['features']
kept = checked = 0; km = 0.0
with open(seq, 'a') as out:
    for start in range(0, total, BATCH):
        meta, fids, geoms, fields = ogr_read(gdb, layer='NHDFlowline', columns=['fcode', 'gnis_name'],
                                              skip_features=start, max_features=BATCH, return_fids=True)
        f = dict(zip(meta['fields'], fields))
        fc = np.array([int(x) if x is not None else 0 for x in f['fcode']])
        sel = np.nonzero(np.isin(fc, list(KEEP)))[0]
        if not len(sel): continue
        g = shapely.from_wkb(geoms[sel])
        ok = ~(shapely.is_missing(g) | shapely.is_empty(g))
        sel, g = sel[ok], shapely.force_2d(g[ok])
        parts, pidx = shapely.get_parts(g, return_index=True)          # MultiLineString -> lines
        dense = shapely.segmentize(parts, STEP_DEG)
        xy, li = shapely.get_coordinates(dense, return_index=True)
        cov = covered(xy[:, 1], xy[:, 0])
        bounds = np.searchsorted(li, np.arange(len(dense) + 1))
        for j in range(len(dense)):
            a, b = bounds[j], bounds[j + 1]
            if b - a < 2: continue
            checked += 1
            c, m = xy[a:b], cov[a:b]
            if m.all(): continue
            src = sel[pidx[j]]; kind = KEEP[fc[src]]
            nm = f['gnis_name'][src]; nm = nm if isinstance(nm, str) and nm else None
            # runs of uncovered points
            edges = np.diff(np.concatenate(([0], (~m).astype(np.int8), [0])))
            for s, e in zip(np.nonzero(edges == 1)[0], np.nonzero(edges == -1)[0]):
                run = c[s:e]
                if len(run) < 2: continue
                L = seg_len_m(run).sum()
                if L < MIN_RUN_M: continue
                t = {'waterway': kind, 'source': 'USGS NHD'}
                if nm: t['name'] = nm
                # Every stretch of one NHD line shares an id, so the map joins them back into one listed creek.
                # The state code keeps ids unique where two states' tiles are merged along a border.
                out.write('\x1e' + json.dumps({'type': 'Feature', 'id': 'nhd%s%d' % (ST, int(fids[src])), 'properties': t,
                          'geometry': {'type': 'LineString', 'coordinates': np.round(run, 6).tolist()}}) + '\n')
                kept += 1; km += L / 1000
        print('  read %d/%d' % (min(start + BATCH, total), total), flush=True)
print('NHD lines checked:', checked, '| stretches added:', kept, '| km added: %.0f' % km)
