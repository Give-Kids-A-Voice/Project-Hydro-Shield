"""Build docs/data/pools tiles for Pinellas County from Pinellas County Property Appraiser public data.

Inputs (from pcpao.gov > Tools & Data > Raw Database Files, CSV): RP_EXTRA_FEATURES.csv, RP_PROPERTY_INFO.csv
Run: python3 scripts/build_pinellas_pools.py RAW_DIR docs/data/pools
Adds [lat, lon] (pool) or [lat, lon, "spa"] points to the same 0.05-degree tiles the Pasco build writes. No owner data.
"""
import csv, json, math, os, sys, collections
csv.field_size_limit(10**8)
raw, out = sys.argv[1], sys.argv[2]
kind = {}
for r in csv.DictReader(open(os.path.join(raw, 'RP_EXTRA_FEATURES.csv'), encoding='latin-1')):
    d = r['XFEAT_DESCRIPTION'].upper().strip()
    if d == 'POOL': kind[r['STRAP']] = 'pool'
    elif d.startswith('SPA') and kind.get(r['STRAP']) != 'pool': kind[r['STRAP']] = 'spa'
tiles = collections.defaultdict(list); seen = set(); n = collections.Counter()
for r in csv.DictReader(open(os.path.join(raw, 'RP_PROPERTY_INFO.csv'), encoding='latin-1')):
    k = kind.get(r['STRAP'])
    if not k: continue
    try: lat, lon = float(r['LATITUDE']), float(r['LONGITUDE'])
    except ValueError: continue
    if not (27.4 < lat < 28.4 and -83.0 < lon < -82.4): continue
    key = (round(lat, 5), round(lon, 5))
    if key in seen: continue  # condo units share one pool
    seen.add(key); n[k] += 1
    tiles[f'{math.floor(lat*20)}_{math.floor(lon*20)}'].append([key[0], key[1]] + ([] if k == 'pool' else ['spa']))
os.makedirs(out, exist_ok=True)
for t, pts in tiles.items():
    p = os.path.join(out, t + '.json')
    old = json.load(open(p)) if os.path.exists(p) else []
    json.dump(old + pts, open(p, 'w'), separators=(',', ':'))
print(dict(n), 'in', len(tiles), 'tiles')
