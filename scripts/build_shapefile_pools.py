"""Add pools for counties that publish an extra-features file plus a parcel shapefile (Polk), or a features file plus an ArcGIS parcel layer (Hernando).

Polk:     python3 scripts/build_shapefile_pools.py polk RAW_DIR docs/data/pools
          RAW_DIR has FTP_CAMA/ftp_misc.txt (ftp_misc.zip) and FTP_GIS/parcel.shp (parcel.zip) from polkflpa.gov Downloads.
Hernando: python3 scripts/build_shapefile_pools.py hernando RAW_DIR docs/data/pools
          RAW_DIR has FEAT.TXT (FEAT.ZIP from hernandocountypa-florida.us/Downloads); locations come from the county Parcels FeatureServer.
Writes [lat, lon] parcel centroids into the shared tiles, deduped. No owner data.
"""
import csv, json, math, os, sys, time, urllib.parse, urllib.request, collections
county, raw, out = sys.argv[1], sys.argv[2], sys.argv[3]
pts = []

def centroid(ring):
    a = cx = cy = 0.0
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1]):
        c = x1 * y2 - x2 * y1; a += c; cx += (x1 + x2) * c; cy += (y1 + y2) * c
    if abs(a) < 1e-12: return sum(p[0] for p in ring) / len(ring), sum(p[1] for p in ring) / len(ring)
    return cx / (3 * a), cy / (3 * a)

if county == 'polk':
    import shapefile
    from pyproj import Transformer
    pools = set()
    for r in csv.DictReader(open(os.path.join(raw, 'FTP_CAMA/ftp_misc.txt'), encoding='latin-1')):
        if r['CODE'].strip().startswith('PL') and 'POOL' in r['CDDESC'].upper(): pools.add(r['PARCEL_ID'].strip())
    rd = shapefile.Reader(os.path.join(raw, 'FTP_GIS/parcel'))
    tf = Transformer.from_crs(open(os.path.join(raw, 'FTP_GIS/parcel.prj')).read(), 'EPSG:4326', always_xy=True)
    for i, rec in enumerate(rd.iterRecords()):
        if str(rec[0]).strip() not in pools: continue
        try: s = rd.shape(i)
        except Exception: continue
        if not s.points: continue
        ring = s.points[:s.parts[1]] if len(s.parts) > 1 else s.points
        x, y = centroid(ring); lon, lat = tf.transform(x, y); pts.append((lat, lon))
    print('polk', len(pools), 'pool parcels,', len(pts), 'placed', file=sys.stderr)

elif county == 'hernando':
    keys = set()
    for line in open(os.path.join(raw, 'FEAT.TXT'), encoding='latin-1'):
        code = line[8:11]
        if code in ('SP1', 'SP2', 'SP3', 'SP4', 'SP5', 'SP6', 'SP7', 'SP8', 'SP9'): keys.add(line[0:8].strip())
    url = 'https://services2.arcgis.com/x5zvhhxfUuRDntRe/arcgis/rest/services/Parcels/FeatureServer/0/query'
    kl = sorted(keys)
    for i in range(0, len(kl), 300):
        w = 'PARCEL_KEY IN (' + ','.join("'" + k + "'" for k in kl[i:i + 300]) + ')'
        for attempt in range(5):
            try:
                data = urllib.parse.urlencode({'where': w, 'outFields': 'PARCEL_KEY', 'returnGeometry': 'false', 'returnCentroid': 'true', 'outSR': 4326, 'f': 'json'}).encode()
                with urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=120) as r: j = json.load(r)
                if 'error' in j: raise RuntimeError(j['error'])
                break
            except Exception as e:
                if attempt == 4: raise
                time.sleep(3 * (attempt + 1))
        for f in j.get('features', []):
            c = f.get('centroid')
            if c: pts.append((c['y'], c['x']))
    print('hernando', len(keys), 'pool parcels,', len(pts), 'placed', file=sys.stderr)

tiles = collections.defaultdict(list)
for lat, lon in pts:
    if 24 < lat < 31.5 and -88 < lon < -79:
        tiles[f'{math.floor(lat*20)}_{math.floor(lon*20)}'].append([round(lat, 5), round(lon, 5)])
os.makedirs(out, exist_ok=True)
for t, p in tiles.items():
    fp = os.path.join(out, t + '.json')
    old = json.load(open(fp)) if os.path.exists(fp) else []
    have = {(a[0], a[1]) for a in old}
    json.dump(old + [x for x in p if (x[0], x[1]) not in have and not have.add((x[0], x[1]))], open(fp, 'w'), separators=(',', ':'))
print(county, 'done,', len(tiles), 'tiles', file=sys.stderr)
