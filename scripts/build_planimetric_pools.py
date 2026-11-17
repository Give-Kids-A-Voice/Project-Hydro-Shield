"""Add pools from county planimetric / impervious-surface layers (pool outlines traced from aerial photos by the county).

Run: python3 scripts/build_planimetric_pools.py docs/data/pools [source ...]
Writes [lat, lon] pool centroids into the shared 0.05-degree tiles (dedupes existing points). No owner data.
"""
import json, math, os, sys, time, urllib.parse, urllib.request, collections
SOURCES = {
    # Prince George's County, MD: impervious surfaces (Sanborn, 2017/2020 imagery). Open license with attribution
    # to the Prince George's County Planning Department.
    'princegeorges': dict(url='https://gis.princegeorgescountymd.gov/arcgis/rest/services/DHCD/Environmental_Layers/MapServer/5',
                          where="TYPE IN ('Pool In Ground','Pool Above Ground')", page=1000, box=(38.5, 39.4, -77.2, -76.6)),
    # Anne Arundel County, MD: impervious surfaces (Bureau of Watershed Protection and Restoration).
    'annearundel': dict(url='https://gis.aacounty.org/arcgis/rest/services/OpenData/Utility_BWPR_OpenData/FeatureServer/9',
                        where="FEATURE_TYPE='SWIMMING POOL'", page=1000, box=(38.7, 39.3, -76.9, -76.3)),
}
out = sys.argv[1]; which = sys.argv[2:] or list(SOURCES)

def q(url, params):
    for attempt in range(6):
        try:
            data = urllib.parse.urlencode(dict(params, f='json')).encode()
            req = urllib.request.Request(url + '/query', data=data, headers={'User-Agent': 'ProjectHydroShield/1.0 (givekidsavoice.org)'})
            with urllib.request.urlopen(req, timeout=180) as r: j = json.load(r)
            if 'error' in j: raise RuntimeError(j['error'])
            return j
        except Exception:
            if attempt == 5: raise
            time.sleep(4 * (attempt + 1))

def center(g):
    ring = (g.get('rings') or [[]])[0]
    if not ring: return None
    # Work relative to the first vertex: pools are tiny, and the shoelace sum on raw degrees loses all precision.
    x0, y0 = ring[0]; ring = [(x - x0, y - y0) for x, y in ring]
    a = cx = cy = 0.0
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
        c = x1 * y2 - x2 * y1; a += c; cx += (x1 + x2) * c; cy += (y1 + y2) * c
    if abs(a) < 1e-20: return y0 + sum(p[1] for p in ring) / len(ring), x0 + sum(p[0] for p in ring) / len(ring)
    return y0 + cy / (3 * a), x0 + cx / (3 * a)

tiles = collections.defaultdict(list); total = collections.Counter()
for name in which:
    c = SOURCES[name]; la0, la1, lo0, lo1 = c['box']
    ids = sorted(q(c['url'], {'where': c['where'], 'returnIdsOnly': 'true'}).get('objectIds') or [])
    for i in range(0, len(ids), c['page']):
        chunk = ids[i:i + c['page']]
        try:
            j = q(c['url'], {'objectIds': ','.join(map(str, chunk)), 'outFields': 'OBJECTID', 'outSR': 4326,
                             'returnGeometry': 'true', 'geometryPrecision': 6})
        except Exception as e:
            print(name, 'chunk failed', i, e, file=sys.stderr); continue
        for f in j.get('features', []):
            p = center(f.get('geometry') or {})
            if not p: continue
            lat, lon = round(p[0], 5), round(p[1], 5)
            if not (la0 < lat < la1 and lo0 < lon < lo1): continue
            tiles[f'{math.floor(lat*20)}_{math.floor(lon*20)}'].append([lat, lon]); total[name] += 1
    print(name, len(ids), 'pool outlines,', total[name], 'placed', file=sys.stderr)
os.makedirs(out, exist_ok=True)
for t, pts in tiles.items():
    p = os.path.join(out, t + '.json')
    old = json.load(open(p)) if os.path.exists(p) else []
    have = {(a[0], a[1]) for a in old}
    json.dump(old + [x for x in pts if (x[0], x[1]) not in have and not have.add((x[0], x[1]))], open(p, 'w'), separators=(',', ':'))
print(dict(total), 'in', len(tiles), 'tiles', file=sys.stderr)
