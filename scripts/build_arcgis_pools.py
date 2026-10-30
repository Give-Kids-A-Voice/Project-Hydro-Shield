"""Add pools from county ArcGIS parcel services that carry a pool flag (Manatee, Orange, Lee).

Run: python3 scripts/build_arcgis_pools.py docs/data/pools [county ...]
Writes [lat, lon] parcel centroids for pool parcels into the shared 0.05-degree tiles (dedupes existing points). No owner data.
"""
import json, math, os, sys, time, urllib.parse, urllib.request, collections
COUNTIES = {
    'manatee': dict(url='https://gis.manateepao.com/arcgis/rest/services/Website/WebLayers/MapServer/0',
                    where="PAR_SWIMPOOL_FLAG='Y'", key='PARID', page=2000, credit='Manatee County Property Appraiser'),
    'orange':  dict(url='https://vgispublic.ocpafl.org/server/rest/services/DYNAMIC/Dynamic_Parcels/MapServer/0',
                    where="POOL='Y'", key='PARCEL', page=1000, point=True, credit='Orange County Property Appraiser'),
    'lee':     dict(url='https://services2.arcgis.com/LvWGAAhHwbCJ2GMP/arcgis/rest/services/Lee_County_Parcels/FeatureServer/0',
                    where="POOL='Y'", key='STRAP', page=2000, credit='Lee County'),
}
out = sys.argv[1]; which = sys.argv[2:] or list(COUNTIES)

def q(url, params):
    for attempt in range(6):
        try:
            data = urllib.parse.urlencode(dict(params, f='json')).encode()
            req = urllib.request.Request(url + '/query', data=data, headers={'User-Agent': 'ProjectHydroShield/1.0 (givekidsavoice.org)'})
            with urllib.request.urlopen(req, timeout=180) as r: j = json.load(r)
            if 'error' in j: raise RuntimeError(j['error'])
            return j
        except Exception as e:
            if attempt == 5: raise
            time.sleep(4 * (attempt + 1))

def center(g):
    if 'x' in g: return g['y'], g['x']
    ring = (g.get('rings') or [[]])[0]
    if not ring: return None
    a = cx = cy = 0.0
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
        c = x1 * y2 - x2 * y1; a += c; cx += (x1 + x2) * c; cy += (y1 + y2) * c
    if abs(a) < 1e-15: return sum(p[1] for p in ring) / len(ring), sum(p[0] for p in ring) / len(ring)
    return cy / (3 * a), cx / (3 * a)

tiles = collections.defaultdict(list); total = collections.Counter()
for name in which:
    c = COUNTIES[name]; off = 0
    ids = q(c['url'], {'where': c['where'], 'returnIdsOnly': 'true'}).get('objectIds') or []
    ids.sort()
    for i in range(0, len(ids), c['page']):
        chunk = ids[i:i + c['page']]
        params = {'objectIds': ','.join(map(str, chunk)), 'outFields': c['key'], 'outSR': 4326, 'returnGeometry': 'true',
                  'geometryPrecision': 6, 'maxAllowableOffset': 0.00005}
        try:
            j = q(c['url'], params)
        except Exception as e:
            print(name, 'chunk failed', i, e, file=sys.stderr); continue
        for f in j.get('features', []):
            p = center(f.get('geometry') or {})
            if not p: continue
            lat, lon = round(p[0], 5), round(p[1], 5)
            if not (24 < lat < 31.5 and -88 < lon < -79): continue
            tiles[f'{math.floor(lat*20)}_{math.floor(lon*20)}'].append([lat, lon]); total[name] += 1
    print(name, len(ids), 'pool parcels,', total[name], 'placed', file=sys.stderr)
os.makedirs(out, exist_ok=True)
for t, pts in tiles.items():
    p = os.path.join(out, t + '.json')
    old = json.load(open(p)) if os.path.exists(p) else []
    have = {(a[0], a[1]) for a in old}
    json.dump(old + [x for x in pts if (x[0], x[1]) not in have and not have.add((x[0], x[1]))], open(p, 'w'), separators=(',', ':'))
print(dict(total), 'in', len(tiles), 'tiles', file=sys.stderr)
