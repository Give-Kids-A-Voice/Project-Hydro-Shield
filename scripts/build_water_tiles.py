"""Cut OSM water features (GeoJSON sequence from `osmium export`) into 0.05-degree tiles for the web map.

Each tile docs/data/water/<lat*20>_<lon*20>.json is a list of
  {"i": osm id, "n": name, "t": tags subset, "g": [[ [lat,lon], ... ], ...]}   rings or lines, 5-decimal coords
A feature is written to every tile its bounding box touches. Pools are skipped where county records already cover them.
"""
import json, math, os, sys, collections
src, out = sys.argv[1], sys.argv[2]
KEEP = ('natural', 'water', 'landuse', 'leisure', 'waterway', 'amenity', 'name', 'access', 'basin')
tiles = collections.defaultdict(list); n = 0

def rings(geom):
    t, c = geom['type'], geom['coordinates']
    if t == 'Point': return [[c]]
    if t == 'LineString': return [c]
    if t == 'MultiLineString': return c
    if t == 'Polygon': return c[:1]                      # outer ring only
    if t == 'MultiPolygon': return [p[0] for p in c]
    return []

def thin(r, step=0.00003):
    """Drop points closer than ~3 m to the previous kept point; keep ends."""
    if len(r) <= 3: return r
    o = [r[0]]
    for p in r[1:-1]:
        if abs(p[0] - o[-1][0]) > step or abs(p[1] - o[-1][1]) > step: o.append(p)
    o.append(r[-1]); return o

with open(src) as f:
    for line in f:
        line = line.strip().lstrip('\x1e')
        if not line: continue
        ft = json.loads(line); g = ft.get('geometry')
        if not g: continue
        tags = {k: v for k, v in (ft.get('properties') or {}).items() if k in KEEP}
        rs = [[[round(y, 5), round(x, 5)] for x, y in thin(r)] for r in rings(g)]
        rs = [r for r in rs if r]
        if not rs: continue
        lats = [p[0] for r in rs for p in r]; lons = [p[1] for r in rs for p in r]
        rec = {'i': ft.get('id') or n, 't': tags, 'g': rs, 'l': 1 if g['type'] in ('LineString', 'MultiLineString') else 0}
        for y in range(math.floor(min(lats) * 20), math.floor(max(lats) * 20) + 1):
            for x in range(math.floor(min(lons) * 20), math.floor(max(lons) * 20) + 1):
                tiles[f'{y}_{x}'].append(rec)
        n += 1
os.makedirs(out, exist_ok=True)
for k, v in tiles.items():
    with open(os.path.join(out, k + '.json'), 'w') as f: json.dump(v, f, separators=(',', ':'))
print(n, 'features,', len(tiles), 'tiles')
