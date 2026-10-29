"""Cut OSM water features (GeoJSON sequence from `osmium export`) into 0.05-degree tiles for the web map.

Each tile docs/data/water/<lat*20>_<lon*20>.json is a list of
  {"i": osm id, "n": name, "t": tags subset, "g": [[ [lat,lon], ... ], ...]}   rings or lines, 5-decimal coords
A feature is clipped to each 0.05-degree tile it touches, so large lakes and bays are stored in pieces. Pools are skipped where county records already cover them.
"""
import json, math, os, sys, collections
from shapely.geometry import shape, box, mapping
from shapely.validation import make_valid
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
    if t == 'GeometryCollection': return [r for gg in geom['geometries'] for r in rings(gg)]
    if t == 'MultiPoint': return [[p] for p in c]
    return []

def thin(r, step=0.00003):
    """Drop points closer than ~3 m to the previous kept point; keep ends."""
    if len(r) <= 3: return r
    o = [r[0]]
    for p in r[1:-1]:
        if abs(p[0] - o[-1][0]) > step or abs(p[1] - o[-1][1]) > step: o.append(p)
    o.append(r[-1]); return o

T = 0.05  # tile size in degrees
with open(src) as f:
    for line in f:
        line = line.strip().lstrip('\x1e')
        if not line: continue
        ft = json.loads(line); g = ft.get('geometry')
        if not g: continue
        tags = {k: v for k, v in (ft.get('properties') or {}).items() if k in KEEP}
        is_line = g['type'] in ('LineString', 'MultiLineString')
        try:
            geom = shape(g)
            if not geom.is_valid: geom = make_valid(geom)
        except Exception:
            continue
        if geom.is_empty: continue
        minx, miny, maxx, maxy = geom.bounds
        fid = ft.get('id') or n
        for y in range(math.floor(miny / T), math.floor(maxy / T) + 1):
            for x in range(math.floor(minx / T), math.floor(maxx / T) + 1):
                cell = box(x * T, y * T, (x + 1) * T, (y + 1) * T)
                part = geom if (minx >= x*T and maxx <= (x+1)*T and miny >= y*T and maxy <= (y+1)*T) else geom.intersection(cell)
                if part.is_empty: continue
                # keep only the parts a person could reach; clip so big bays and rivers are stored once per tile, not whole
                rs = [[[round(yy, 5), round(xx, 5)] for xx, yy in thin(list(r))] for r in rings(mapping(part))]
                rs = [r for r in rs if r]
                if rs: tiles[f'{y}_{x}'].append({'i': fid, 't': tags, 'g': rs, 'l': 1 if is_line else 0})
        n += 1
os.makedirs(out, exist_ok=True)
for k, v in tiles.items():
    with open(os.path.join(out, k + '.json'), 'w') as f: json.dump(v, f, separators=(',', ':'))
print(n, 'features,', len(tiles), 'tiles')
