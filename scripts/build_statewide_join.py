"""Place pools for counties whose Property Appraiser publishes a pool list without locations, using the
Florida Department of Revenue statewide parcel centroids (FDOR Cadastral Centroids, via Florida GIO).

  python3 scripts/build_statewide_join.py sarasota RAW_DIR docs/data/pools   # RAW_DIR/SFYI.txt from SCPA_Detailed_Data.zip
  python3 scripts/build_statewide_join.py duval    RAW_DIR docs/data/pools   # RAW_DIR/*.txt pipe-delimited roll (record 00011 = extra features)
  python3 scripts/build_statewide_join.py citrus   RAW_DIR docs/data/pools   # RAW_DIR/VD_PARCELDATA.CSV (POOLFLG = Y)
Writes [lat, lon] (pool) or [lat, lon, "spa"] into the shared tiles, deduped. No owner data.
"""
import csv, glob, json, math, os, sys, time, urllib.parse, urllib.request, collections
csv.field_size_limit(10**8)
URL = 'https://services9.arcgis.com/Gh9awoU677aKree0/arcgis/rest/services/Florida_Statewide_Parcel_Centroid_Version/FeatureServer/0/query'
county, raw, out = sys.argv[1], sys.argv[2], sys.argv[3]
kind = {}
key_field = 'PARCEL_ID'

if county == 'sarasota':
    co = 68
    for r in csv.DictReader(open(os.path.join(raw, 'SFYI.txt'), encoding='latin-1')):
        t = r['outbuildingtype'].strip(); pid = r['parcelid'].strip()
        if t in ('POOL', 'POOLCO'): kind[pid] = 'pool'
        elif t == 'SPA' and kind.get(pid) != 'pool': kind[pid] = 'spa'
elif county == 'duval':
    co = int(os.environ.get('DUVAL_CO_NO', '26'))
    for fp in glob.glob(os.path.join(raw, '*.txt')) + glob.glob(os.path.join(raw, '*.TXT')):
        for line in open(fp, encoding='latin-1'):
            if not line.startswith('00011|'): continue
            p = line.split('|')
            if len(p) < 5: continue
            code, desc = p[3].strip().upper(), p[4].upper()
            if code.startswith('POL') or 'POOL' in desc: kind[p[1].strip()] = 'pool'
elif county == 'citrus':
    # VD_PARCELDATA.CSV from the Citrus County Property Appraiser vendor dump (Google Drive folder linked on citruspa.org Downloads).
    co, key_field = 19, 'ALT_KEY'
    for r in csv.DictReader(open(os.path.join(raw, 'VD_PARCELDATA.CSV'), encoding='latin-1')):
        if (r.get('POOLFLG') or '').strip().upper() == 'Y': kind[r['ALTKEY'].strip()] = 'pool'
else:
    sys.exit('unknown county')
print(county, len(kind), 'parcels with a pool or spa', file=sys.stderr)

def q(params):
    for attempt in range(6):
        try:
            data = urllib.parse.urlencode(dict(params, f='json')).encode()
            with urllib.request.urlopen(urllib.request.Request(URL, data=data, headers={'User-Agent': 'ProjectHydroShield/1.0'}), timeout=180) as r: j = json.load(r)
            if 'error' in j: raise RuntimeError(j['error'])
            return j
        except Exception:
            if attempt == 5: raise
            time.sleep(4 * (attempt + 1))

def norm(s): return ''.join(ch for ch in s if ch.isalnum())
want = {norm(k): v for k, v in kind.items()}
# Download every parcel point in the county (paged), then match locally. Much faster than ID lookups.
from concurrent.futures import ThreadPoolExecutor
# Page by OBJECTID ranges (offset paging fails on some large counties)
oids = sorted(q({'where': f'CO_NO={co}', 'returnIdsOnly': 'true'}).get('objectIds') or [])
count = len(oids)
def page(i):
    lo, hi = oids[i], oids[min(i + 1999, count - 1)]
    return q({'where': f'CO_NO={co} AND OBJECTID>={lo} AND OBJECTID<={hi}', 'outFields': key_field, 'outSR': 4326}).get('features', [])
tiles = collections.defaultdict(list); n = collections.Counter(); seen = set()
with ThreadPoolExecutor(4) as ex:
    for feats in ex.map(page, range(0, count, 2000)):
        for f in feats:
            g = f.get('geometry') or {}; pid = norm(str(f['attributes'].get(key_field) or ''))
            if 'x' not in g or pid not in want: continue
            lat, lon = round(g['y'], 5), round(g['x'], 5)
            if (lat, lon) in seen: continue
            seen.add((lat, lon)); k = want[pid]; n[k] += 1
            tiles[f'{math.floor(lat*20)}_{math.floor(lon*20)}'].append([lat, lon] + ([] if k == 'pool' else ['spa']))
print(county, count, 'parcels scanned', file=sys.stderr)
os.makedirs(out, exist_ok=True)
for t, pts in tiles.items():
    fp = os.path.join(out, t + '.json')
    old = json.load(open(fp)) if os.path.exists(fp) else []
    have = {(a[0], a[1]) for a in old}
    json.dump(old + [x for x in pts if (x[0], x[1]) not in have and not have.add((x[0], x[1]))], open(fp, 'w'), separators=(',', ':'))
print(county, dict(n), 'placed in', len(tiles), 'tiles', file=sys.stderr)
