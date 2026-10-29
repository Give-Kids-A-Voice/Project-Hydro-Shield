"""Add Hillsborough County pools/spas to docs/data/pools tiles from the Hillsborough County Property Appraiser
public Parcel feature service (updated nightly, free to use; credit HCPA on the map).

Run: python3 scripts/build_hillsborough_pools.py docs/data/pools
Writes [lat, lon] (pool) or [lat, lon, "spa"] parcel centroids into the shared 0.05-degree tiles. No owner data.
"""
import json, math, os, sys, time, urllib.parse, urllib.request, collections
B = 'https://services.arcgis.com/apTfC6SUmnNfnxuF/arcgis/rest/services/HCPA_Parcels_Daily/FeatureServer'
out = sys.argv[1]

def q(layer, params):
    for attempt in range(5):
        try:
            data = urllib.parse.urlencode(dict(params, f='json')).encode()
            with urllib.request.urlopen(urllib.request.Request(f'{B}/{layer}/query', data=data), timeout=120) as r:
                j = json.load(r)
            if 'error' in j: raise RuntimeError(j['error'])
            return j
        except Exception as e:
            if attempt == 4: raise
            time.sleep(3 * (attempt + 1))

# 1. folios with a pool or spa
kind, off = {}, 0
where = "XF_DSC LIKE 'POOL%' OR XF_DSC LIKE 'UNIQUE POOL%' OR XF_DSC LIKE 'LAGOON POOL%' OR XF_DSC LIKE 'SPA %'"
while True:
    j = q(2, {'where': where, 'outFields': 'FOLIO,XF_DSC', 'returnGeometry': 'false', 'resultOffset': off, 'resultRecordCount': 2000, 'orderByFields': 'OBJECTID'})
    fs = j.get('features', [])
    for f in fs:
        a = f['attributes']; fo = (a['FOLIO'] or '').strip(); d = (a['XF_DSC'] or '').upper()
        if not fo: continue
        if 'POOL' in d: kind[fo] = 'pool'
        elif kind.get(fo) != 'pool': kind[fo] = 'spa'
    off += len(fs)
    if not fs or not j.get('exceededTransferLimit'): break
print(len(kind), 'parcels with a pool or spa', file=sys.stderr)

# 2. parcel centroids for those folios
folios = list(kind); tiles = collections.defaultdict(list); seen = set(); n = collections.Counter()
for i in range(0, len(folios), 400):
    chunk = folios[i:i + 400]
    w = 'FOLIO IN (' + ','.join("'" + f.replace("'", "''") + "'" for f in chunk) + ')'
    j = q(0, {'where': w, 'outFields': 'FOLIO', 'returnGeometry': 'false', 'returnCentroid': 'true', 'outSR': 4326})
    for f in j.get('features', []):
        c = f.get('centroid'); fo = (f['attributes']['FOLIO'] or '').strip()
        if not c or fo not in kind: continue
        lat, lon = round(c['y'], 5), round(c['x'], 5)
        if (lat, lon) in seen: continue
        seen.add((lat, lon)); k = kind[fo]; n[k] += 1
        tiles[f'{math.floor(lat*20)}_{math.floor(lon*20)}'].append([lat, lon] + ([] if k == 'pool' else ['spa']))
os.makedirs(out, exist_ok=True)
for t, pts in tiles.items():
    p = os.path.join(out, t + '.json')
    old = json.load(open(p)) if os.path.exists(p) else []
    have = {(a[0], a[1]) for a in old}
    json.dump(old + [x for x in pts if (x[0], x[1]) not in have], open(p, 'w'), separators=(',', ':'))
print(dict(n), 'in', len(tiles), 'tiles', file=sys.stderr)
