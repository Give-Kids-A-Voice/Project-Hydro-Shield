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
"""
import json, math, sys
import numpy as np
from pyogrio.raw import read as ogr_read
import shapely

gdb, seq, ST = sys.argv[1], sys.argv[2], sys.argv[3]
CELL = 0.0003                      # ~33 m (lat); a stretch counts as covered if OSM is in its cell or a neighbor
STEP_M = 10.0                      # walk NHD lines every 10 m
MIN_RUN_M = 40.0                   # ignore uncovered scraps shorter than this (end-of-line wiggles next to OSM)
KEEP = {46000: 'stream', 46003: 'stream', 46006: 'stream', 33600: 'canal', 33601: 'canal', 33603: 'ditch'}

# 1. Cells touched by OSM waterways and by the edges of OSM water areas.
osm = set()
def mark(coords):
    prev = None
    for lon, lat, *_ in coords:
        if prev is not None:
            # fill in between vertices so long straight OSM segments still mark every cell they cross
            d = max(abs(lat - prev[1]), abs(lon - prev[0])); k = max(1, int(d / (CELL / 2)))
            for j in range(1, k + 1):
                y = prev[1] + (lat - prev[1]) * j / k; x = prev[0] + (lon - prev[0]) * j / k
                osm.add((math.floor(y / CELL), math.floor(x / CELL)))
        else:
            osm.add((math.floor(lat / CELL), math.floor(lon / CELL)))
        prev = (lon, lat)
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
        ft = json.loads(line); g = ft.get('geometry') or {}
        if g.get('type') in (None, 'Point', 'MultiPoint'): continue
        walk(g)
print('OSM water cells:', len(osm))

def covered(lat, lon):
    y, x = math.floor(lat / CELL), math.floor(lon / CELL)
    return any((y + dy, x + dx) in osm for dy in (-1, 0, 1) for dx in (-1, 0, 1))

# 2. NHD flowlines.
meta, _, geoms, fields = ogr_read(gdb, layer='NHDFlowline', columns=['fcode', 'gnis_name'])
names = dict(zip(meta['fields'], fields)); fcode = names['fcode']; gname = names['gnis_name']
lines = shapely.force_2d(shapely.from_wkb(geoms))
kept = parts = 0; km = 0.0
with open(seq, 'a') as out:
    for i in range(len(lines)):
        kind = KEEP.get(int(fcode[i]) if fcode[i] is not None else 0)
        g = lines[i]
        if not kind or g is None or g.is_empty: continue
        nm = gname[i] if isinstance(gname[i], str) and gname[i] else None
        for ln in (g.geoms if g.geom_type == 'MultiLineString' else [g]):
            c = np.asarray(ln.coords)
            if len(c) < 2: continue
            # densify to ~STEP_M so coverage is judged along the whole line, not just at its vertices
            pts = [c[0]]
            for a, b in zip(c[:-1], c[1:]):
                dm = math.hypot((b[1] - a[1]) * 110574, (b[0] - a[0]) * 111320 * math.cos(math.radians(a[1])))
                k = max(1, int(dm / STEP_M))
                for j in range(1, k + 1): pts.append(a + (b - a) * j / k)
            run = []
            def flush():
                global kept, km
                if len(run) < 2: return
                L = sum(math.hypot((q[1] - p[1]) * 110574, (q[0] - p[0]) * 111320 * math.cos(math.radians(p[1]))) for p, q in zip(run[:-1], run[1:]))
                if L < MIN_RUN_M: return
                t = {'waterway': kind, 'source': 'USGS NHD'}
                if nm: t['name'] = nm
                out.write('\x1e' + json.dumps({'type': 'Feature', 'id': 'nhd%s%d' % (ST, i), 'properties': t,
                          'geometry': {'type': 'LineString', 'coordinates': [[round(p[0], 6), round(p[1], 6)] for p in run]}}) + '\n')
                kept += 1; km += L / 1000
            for p in pts:
                if covered(p[1], p[0]):
                    flush(); run = []
                else:
                    run.append(p)
            flush()
        parts += 1
print('NHD lines checked:', parts, '| stretches added:', kept, '| km added: %.0f' % km)
