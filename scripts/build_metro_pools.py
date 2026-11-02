"""Pool points for metros outside Florida/California, from free public assessor / appraisal-district data (no login).

Run: python3 scripts/build_metro_pools.py <pools-dir> <raw-root> [source ...]   (bulk files in <raw-root>/<source>/)

Sources (config below; one generic builder, four fetch kinds):
  maricopa  Maricopa County (AZ) Enterprise GIS parcel view, Pool = 'YES'; Latitude_DD / Longitude_DD in the layer
  clark     Clark County (NV) Assessor residential extract (AORES, republished by City of Las Vegas GIS), POOL >= 1,
            joined on PARCEL to the Clark County parcel polygons (CC_PARCELS_SHP, same publisher) for a centroid
  collin    Collin Central Appraisal District parcel layer, imprvPoolFlag = 'T'
  tarrant   Tarrant Appraisal District PropertyData(Delimited)_R.ZIP, Swimming_Pool_Ind = 'Y', GIS_Link joined to
            TAXPIN in TAD's OD_Parcels MapServer                                    raw-dir must hold prop.zip
  dallas    Dallas Central Appraisal District DCAD2026_CURRENT.ZIP RES_DETAIL.CSV POOL_IND = 'Y', joined on ACCOUNT_NUM
            to DCAD's own PARCEL2026 shapefile (GIS data products)                  raw-dir: cur.zip, PARCEL2026/**.shp
  harris    Harris Central Appraisal District Real_building_land.zip extra_features.txt, cd RRP1-RRP7 (residential pools),
            joined on acct to HCAD's Parcels.gdb (HCAD_NUM_1)                       raw-dir: rbl.zip, Parcels.gdb

Only [lat, lon] (a point inside / centroid of the pool parcel) is written; owner names, addresses and parcel ids are
read only to join and dedupe, then dropped. Same tile scheme and OSM-duplicate rule (~30 m) as
scripts/build_ca_parcel_pools.py, run AFTER the region's OSM pool copy. Exits non-zero without writing anything if a
source fails, returns implausibly few pools, or places points outside the county box, so committed data stays.
"""
import csv, glob, io, json, math, os, sys, time, zipfile, collections, urllib.parse, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_ca_parcel_pools import q   # paged ArcGIS query with retries

NEAR_M = 30.0
SOURCES = {
    'maricopa': dict(kind='arcgis_latlon', box=(32.5, 34.1, -113.4, -111.0), min=300000,
                     url='https://services.arcgis.com/ykpntM6e3tHvzKRJ/arcgis/rest/services/Parcel_Data_View/FeatureServer/0',
                     where="Pool='YES'", key='APN', lat='Latitude_DD', lon='Longitude_DD'),
    'collin': dict(kind='arcgis_centroid', box=(32.95, 33.45, -96.85, -96.25), min=45000,
                   url='https://services2.arcgis.com/uXyoacYrZTPTKD3R/arcgis/rest/services/CCAD_Parcel_Feature_Set/FeatureServer/4',
                   where="imprvPoolFlag='T'", key='PROP_ID'),
    'clark': dict(kind='arcgis_join', box=(35.0, 36.9, -115.9, -114.0), min=100000,
                  table='https://services1.arcgis.com/F1v0ufATbBQScMtY/arcgis/rest/services/AORES/FeatureServer/0',
                  where='POOL>=1', tkey='PARCEL',
                  url='https://services1.arcgis.com/F1v0ufATbBQScMtY/arcgis/rest/services/CC_PARCELS_SHP/FeatureServer/1',
                  key='PARCEL', centroid=True),
    'tarrant': dict(kind='tarrant', box=(32.5, 33.0, -97.6, -97.0), min=60000,
                    url='https://tad.newedgeservices.com/arcgis/rest/services/OD_TAD/OD_Parcels/MapServer/0', key='TAXPIN'),
    'dallas': dict(kind='dallas', box=(32.5, 33.03, -97.05, -96.5), min=50000),
    'harris': dict(kind='harris', box=(29.45, 30.2, -95.97, -94.9), min=90000),
}


def tile(lat, lon): return '%d_%d' % (math.floor(lat * 20), math.floor(lon * 20))


def ids_for(url, where):
    return sorted(q(url, {'where': where, 'returnIdsOnly': 'true'}).get('objectIds') or [])


def arcgis_points(c):
    ids = ids_for(c['url'], c['where']); seen, pts = set(), []
    for i in range(0, len(ids), 1000):
        p = {'objectIds': ','.join(map(str, ids[i:i + 1000])), 'returnGeometry': 'false', 'outSR': 4326}
        if c['kind'] == 'arcgis_latlon': p['outFields'] = '%s,%s,%s' % (c['key'], c['lat'], c['lon'])
        else: p.update(outFields=c['key'], returnCentroid='true')
        for f in q(c['url'], p).get('features', []):
            a = f['attributes']; k = a.get(c['key'])
            if c['kind'] == 'arcgis_latlon': la, lo = a.get(c['lat']), a.get(c['lon'])
            else:
                ce = f.get('centroid') or {}; la, lo = ce.get('y'), ce.get('x')
            if la is None or lo is None or k in seen: continue
            seen.add(k); pts.append((la, lo))
    print(len(ids), 'pool records', file=sys.stderr)
    return pts


def in_query(url, key, keys, extra, batch=250):
    """Query a layer for many key values (WHERE key IN (...)), yielding features."""
    keys = sorted(keys)
    for i in range(0, len(keys), batch):
        w = '%s IN (%s)' % (key, ','.join("'%s'" % k.replace("'", "''") for k in keys[i:i + batch]))
        yield from q(url, dict(extra, where=w)).get('features', [])


def arcgis_join(c):
    ids = ids_for(c['table'], c['where']); keys = set()
    for i in range(0, len(ids), 1000):
        for f in q(c['table'], {'objectIds': ','.join(map(str, ids[i:i + 1000])), 'outFields': c['tkey'],
                                'returnGeometry': 'false'}).get('features', []):
            v = (f['attributes'].get(c['tkey']) or '').strip()
            if v: keys.add(v)
    print(len(ids), 'pool records,', len(keys), 'distinct parcels', file=sys.stderr)
    pts, seen = [], set()
    for f in in_query(c['url'], c['key'], keys, {'outFields': c['key'], 'returnGeometry': 'false', 'returnCentroid': 'true',
                                                 'outSR': 4326}):
        k = f['attributes'].get(c['key']); ce = f.get('centroid')
        if ce and k not in seen: seen.add(k); pts.append((ce['y'], ce['x']))
    return pts


def poly_center(rings):
    """Point inside the largest ring of an Esri polygon (shapely representative point)."""
    from shapely.geometry import Polygon
    best = max((Polygon(r) for r in rings if len(r) >= 4), key=lambda p: abs(p.area), default=None)
    if best is None: return None
    pt = best.buffer(0).representative_point() if not best.is_valid else best.representative_point()
    return pt.y, pt.x


def tarrant(c, raw):
    keys = set(); n = 0
    with zipfile.ZipFile(os.path.join(raw, 'prop.zip')) as z:
        name = [m for m in z.namelist() if m.lower().endswith('.txt')][0]
        with z.open(name) as fh:
            r = csv.reader(io.TextIOWrapper(fh, encoding='latin-1'), delimiter='|', quoting=csv.QUOTE_NONE)
            hdr = next(r); ip, ig = hdr.index('Swimming_Pool_Ind'), hdr.index('GIS_Link')
            for row in r:
                if len(row) > max(ip, ig) and row[ip].strip() == 'Y' and row[ig].strip():
                    n += 1; keys.add(row[ig].strip())
    print(n, 'pool accounts,', len(keys), 'distinct GIS links', file=sys.stderr)
    pts, seen = [], set()
    for f in in_query(c['url'], c['key'], keys, {'outFields': c['key'], 'returnGeometry': 'true', 'outSR': 4326,
                                                 'maxAllowableOffset': 0.00002}):
        k = f['attributes'].get(c['key'])
        if k in seen or not f.get('geometry'): continue
        p = poly_center(f['geometry'].get('rings') or [])
        if p: seen.add(k); pts.append(p)
    return pts


def file_points(path, keyfield, keys):
    """Points inside the parcel polygons (any OGR format) whose keyfield is in keys, in WGS84."""
    import pyogrio, shapely, pyproj
    meta, _, geom, fields = pyogrio.raw.read(path, columns=[keyfield])
    vals = fields[0]
    sel = [i for i, v in enumerate(vals) if v is not None and str(v).strip() in keys]
    g = shapely.from_wkb([geom[i] for i in sel])
    g = shapely.force_2d(g); bad = ~shapely.is_valid(g); g[bad] = shapely.make_valid(g[bad])
    p = shapely.point_on_surface(g)
    tr = pyproj.Transformer.from_crs(meta['crs'], 'EPSG:4326', always_xy=True)
    lon, lat = tr.transform(shapely.get_x(p), shapely.get_y(p))
    seen, pts = set(), []
    for i, la, lo in zip(sel, lat, lon):
        k = str(vals[i]).strip()
        if k in seen or not (la == la): continue
        seen.add(k); pts.append((la, lo))
    return pts


def dallas(c, raw):
    keys = set(); n = 0
    with zipfile.ZipFile(os.path.join(raw, 'cur.zip')) as z, z.open('RES_DETAIL.CSV') as fh:
        for row in csv.DictReader(io.TextIOWrapper(fh, encoding='latin-1')):
            if row['POOL_IND'].strip() == 'Y': n += 1; keys.add(row['ACCOUNT_NUM'].strip())
    print(n, 'pool rows,', len(keys), 'distinct accounts', file=sys.stderr)
    shp = glob.glob(os.path.join(raw, '**', 'PARCEL20*.shp'), recursive=True)[0]
    return file_points(shp, 'Acct', keys)


def harris(c, raw):
    keys = set(); n = 0
    with zipfile.ZipFile(os.path.join(raw, 'rbl.zip')) as z, z.open('extra_features.txt') as fh:
        r = csv.reader(io.TextIOWrapper(fh, encoding='latin-1'), delimiter='\t', quoting=csv.QUOTE_NONE)
        hdr = next(r); ia, ic = hdr.index('acct'), hdr.index('cd')
        for row in r:
            if len(row) > ic and row[ic].strip()[:3] == 'RRP' and row[ic].strip()[3:4] in '1234567':
                n += 1; keys.add(row[ia].strip())
    print(n, 'pool feature rows,', len(keys), 'distinct accounts', file=sys.stderr)
    return file_points(os.path.join(raw, 'Parcels.gdb'), 'HCAD_NUM_1', keys)


def fetch(name, raw):
    c = SOURCES[name]; k = c['kind']
    if k in ('arcgis_latlon', 'arcgis_centroid'): pts = arcgis_points(c)
    elif k == 'arcgis_join': pts = arcgis_join(c)
    else: pts = globals()[k](c, raw)
    b = c['box']; out = []
    for la, lo in pts:
        la, lo = round(la, 5), round(lo, 5)
        if b[0] < la < b[1] and b[2] < lo < b[3]: out.append((la, lo))
    print(name, len(pts), 'parcels placed,', len(out), 'inside the county box', file=sys.stderr)
    if len(out) < c['min']: raise RuntimeError('too few pools (%d < %d); keeping committed data' % (len(out), c['min']))
    if len(out) < 0.97 * len(pts): raise RuntimeError('too many points outside the county box; keeping committed data')
    return out


def inbox(b, la, lo): return b[0] < la < b[1] and b[2] < lo < b[3]


def write(out, got, failed):
    """got: {source: points}. Neighbouring counties share tiles, so all sources are written in one pass: in every tile a
    run touches, old county points are replaced when they lie in a refreshed county's box, and kept when they also lie
    in the box of a county whose refresh failed (its committed points must survive)."""
    pts = [p for v in got.values() for p in v]
    tiles = collections.defaultdict(list)
    for lat, lon in pts: tiles[tile(lat, lon)].append([lat, lon])
    okb = [SOURCES[n]['box'] for n in got]; badb = [SOURCES[n]['box'] for n in failed]
    cell = NEAR_M / 111000.0
    grid = set((math.floor(la / cell), math.floor(lo / cell)) for la, lo in pts)

    def near(la, lo):
        gy, gx = math.floor(la / cell), math.floor(lo / cell)
        return any((gy + dy, gx + dx) in grid for dy in (-1, 0, 1) for dx in (-1, 0, 1))

    os.makedirs(out, exist_ok=True); dropped = kept = held = 0
    for t, new in tiles.items():
        p = os.path.join(out, t + '.json'); old = []
        if os.path.exists(p):
            with open(p) as f: old = json.load(f)
        rest = []
        for e in old:
            if len(e) > 2 and e[2] == 'osm':
                if near(e[0], e[1]): dropped += 1
                else: rest.append(e); kept += 1
            elif any(inbox(b, e[0], e[1]) for b in badb) or not any(inbox(b, e[0], e[1]) for b in okb):
                rest.append(e); held += 1
        with open(p, 'w') as f: json.dump(new + rest, f, separators=(',', ':'))
    print(','.join(got), len(pts), 'county pools in', len(tiles), 'tiles; OSM points dropped as duplicates:', dropped,
          'kept:', kept, '; older county points kept for failed/other counties:', held, file=sys.stderr)


def main(out, raw_root, names):
    got, failed = {}, []
    for n in names:
        try: got[n] = fetch(n, os.path.join(raw_root, n))
        except Exception as e: print(n, 'skipped:', repr(e)[:300], file=sys.stderr); failed.append(n)
    if got: write(out, got, failed)
    if failed: sys.exit(1)


if __name__ == '__main__':
    # python3 scripts/build_metro_pools.py <pools-dir> <raw-root> [source ...]   (raw-root/<source>/ holds bulk files)
    if len(sys.argv) < 3 or any(n not in SOURCES for n in sys.argv[3:]): sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2], sys.argv[3:] or list(SOURCES))
