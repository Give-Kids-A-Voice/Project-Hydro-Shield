"""Build docs/data/pools tiles from Pasco County Property Appraiser public data.

Download into RAW: https://ftp01.pascopa.com/real_estate/extrafeatures.zip and https://ftp01.pascopa.com/gis/pasco_parcels.zip (unzip both).
Run: python3 scripts/build_county_pools.py RAW docs/data/pools
Output: one JSON per 0.05 degree tile, [[lat, lon], ...] parcel centroids that have a pool or spa on record. No owner data."""
import csv, json, math, os, sys, collections, shapefile
from pyproj import Transformer
raw, out = sys.argv[1], sys.argv[2]
pools = set()
for r in csv.DictReader(open(os.path.join(raw, 'extrafeatures.csv'))):
    if r['XF_Code'].startswith(('RPOOL', 'CPOOL', 'RSPA', 'CSPA')): pools.add(r['Parcel_Num'])
rd = shapefile.Reader(os.path.join(raw, 'parcels/workspace/scripts/pascoshp/pasco_parcels'))
names = [f[0] for f in rd.fields[1:]]
ip, ih = names.index('PARCEL'), names.index('HAS_POOL')
tf = Transformer.from_crs(open(os.path.join(raw, 'parcels/workspace/scripts/pascoshp/pasco_parcels.prj')).read(), 'EPSG:4326', always_xy=True)
tiles = collections.defaultdict(list); n = 0
hpvals = collections.Counter()
for i, rec in enumerate(rd.iterRecords()):
    pid = rec[ip]; hp = str(rec[ih]).strip().upper(); hpvals[hp] += 1
    if pid not in pools and hp not in ('Y', 'YES', '1', 'TRUE', 'T'): continue
    try: shp = rd.shape(i)
    except Exception: continue
    class SR: pass
    sr = SR(); sr.shape = shp
    pts = sr.shape.points
    if not pts: continue
    # polygon area centroid (first ring)
    ring = pts[:sr.shape.parts[1]] if len(sr.shape.parts) > 1 else pts
    a = cx = cy = 0.0
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
        c = x1 * y2 - x2 * y1; a += c; cx += (x1 + x2) * c; cy += (y1 + y2) * c
    if abs(a) < 1e-9: cx, cy = sum(p[0] for p in ring) / len(ring), sum(p[1] for p in ring) / len(ring)
    else: cx, cy = cx / (3 * a), cy / (3 * a)
    lon, lat = tf.transform(cx, cy)
    tiles[f'{math.floor(lat*20)}_{math.floor(lon*20)}'].append([round(lat, 5), round(lon, 5)])
    n += 1
os.makedirs(out, exist_ok=True)
for k, v in tiles.items(): json.dump(v, open(os.path.join(out, k + '.json'), 'w'), separators=(',', ':'))
print(n, 'pools in', len(tiles), 'tiles; HAS_POOL values', hpvals.most_common(5), 'xf pools', len(pools))
