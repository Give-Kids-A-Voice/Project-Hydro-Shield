"""California pools from public parcel layers that carry an Assessor pool flag (public ArcGIS services, no login).

Run: python3 scripts/build_ca_parcel_pools.py docs/data/pools [source ...]   (default: all)
Sources are built in groups (GROUPS below); naming any source rebuilds its whole group, because neighbouring
sources share tiles and a tile's county points are rewritten in one pass. If any source in a group fails or returns
too few pools, that whole group is left untouched.

Sources:
  sandiego   SanGIS/SANDAG regional parcels (San Diego County Assessor data), POOL = 'Y'
             https://geo.sandag.org/server/rest/services/Hosted/Parcels/FeatureServer/0
  palmdesert City of Palm Desert parcels (Riverside County CREST property tax data), HAS_POOL = '1'
             https://services2.arcgis.com/i4mrGZu1Isvl0rWt/arcgis/rest/services/Palm_Desert_Parcels_CREST/FeatureServer/0
  pasadena   City of Pasadena Land Base parcels (LA County Assessor data), Pool = 'Y'
             https://services1.arcgis.com/SPm6TOk52QjLKxth/arcgis/rest/services/Land_Base/FeatureServer/95
  ranchomirage City of Rancho Mirage RM2GO parcels (Riverside County Assessor data), POOL = 'Y'
             https://services1.arcgis.com/LgDVQaAg05xQLgo7/arcgis/rest/services/RM2GO_Parcels/FeatureServer/0
  contracosta Contra Costa County DoIT attributed Assessor parcels (republished monthly by a county fire district), POOL = 'Y'
             https://services6.arcgis.com/CmHj285GYxHhHnTo/arcgis/rest/services/Assessor_Parcels/FeatureServer/0
  sanjoaquin San Joaquin County Assessor parcels, POOL_SPA coded (P, GP, PS, GPS ...; 'N' or blank = none)
             https://services2.arcgis.com/GQhSReJEO6f7tsvy/arcgis/rest/services/Parcels/FeatureServer/0
  solano     Solano County public Aumentum parcels, pool = 'YS'
             https://services2.arcgis.com/SCn6czzcqKAFwdGU/arcgis/rest/services/Parcels_Public_Aumentum/FeatureServer/0
Writes [lat, lon] parcel centroids (no owner data) into the shared 0.05-degree tiles. Idempotent and run AFTER the
OpenStreetMap SoCal pool build: in every tile it touches it replaces earlier county points, and drops OpenStreetMap
points that lie within ~30 m of a county pool parcel centroid as duplicates (a parcel centroid is usually 10-25 m from the pool itself, so a 4 m test would not catch the duplicate).
OpenStreetMap pools farther away (public/hotel pools, parcels the Assessor has not flagged) are kept.
Stacked parcels (condos, several APNs on one polygon) are counted once per parcel polygon / APN.
Exits non-zero without touching anything if the service fails or returns implausibly few pools.
"""
import json, math, os, sys, time, urllib.parse, urllib.request, collections

SOURCES = {
    'sandiego': dict(url='https://geo.sandag.org/server/rest/services/Hosted/Parcels/FeatureServer/0',
                     where="pool='Y'", key='parcelid', box=(32.4, 33.6, -117.7, -116.0), min=50000),
    'palmdesert': dict(url='https://services2.arcgis.com/i4mrGZu1Isvl0rWt/arcgis/rest/services/Palm_Desert_Parcels_CREST/FeatureServer/0',
                       where="HAS_POOL='1'", key='APN', box=(33.6, 33.85, -116.5, -116.2), min=5000),
    'pasadena': dict(url='https://services1.arcgis.com/SPm6TOk52QjLKxth/arcgis/rest/services/Land_Base/FeatureServer/95',
                     where="Pool='Y'", key='APN', box=(34.1, 34.26, -118.2, -118.04), min=4300),
    'ranchomirage': dict(url='https://services1.arcgis.com/LgDVQaAg05xQLgo7/arcgis/rest/services/RM2GO_Parcels/FeatureServer/0',
                         where="POOL='Y'", key='APN', box=(33.68, 33.83, -116.5, -116.35), min=4600),
    'contracosta': dict(url='https://services6.arcgis.com/CmHj285GYxHhHnTo/arcgis/rest/services/Assessor_Parcels/FeatureServer/0',
                        where="POOL='Y'", key='APN', box=(37.65, 38.15, -122.5, -121.5), min=35000),
    'sanjoaquin': dict(url='https://services2.arcgis.com/GQhSReJEO6f7tsvy/arcgis/rest/services/Parcels/FeatureServer/0',
                       where="POOL_SPA IS NOT NULL AND POOL_SPA NOT IN ('N','')", key='APN',
                       box=(37.45, 38.35, -121.65, -120.85), min=23000),
    'solano': dict(url='https://services2.arcgis.com/SCn6czzcqKAFwdGU/arcgis/rest/services/Parcels_Public_Aumentum/FeatureServer/0',
                   where="pool='YS'", key='parcelid', box=(38.0, 38.6, -122.45, -121.55), min=8500),
}
GROUPS = [['sandiego', 'palmdesert', 'pasadena', 'ranchomirage'], ['contracosta', 'sanjoaquin', 'solano']]
NEAR_M = 30.0


def q(URL, params):
    for attempt in range(6):
        try:
            data = urllib.parse.urlencode(dict(params, f='json')).encode()
            req = urllib.request.Request(URL + '/query', data=data,
                                         headers={'User-Agent': 'ProjectHydroShield/1.0 (givekidsavoice.org)'})
            with urllib.request.urlopen(req, timeout=180) as r: j = json.load(r)
            if 'error' in j: raise RuntimeError(j['error'])
            return j
        except Exception:
            if attempt == 5: raise
            time.sleep(4 * (attempt + 1))


def page(URL):
    """Records per objectIds request: the layer's maxRecordCount (some layers cap at 1000), at most 2000."""
    for attempt in range(6):
        try:
            req = urllib.request.Request(URL + '?f=json', headers={'User-Agent': 'ProjectHydroShield/1.0 (givekidsavoice.org)'})
            with urllib.request.urlopen(req, timeout=60) as r: return min(2000, int(json.load(r).get('maxRecordCount') or 1000))
        except Exception:
            if attempt == 5: raise
            time.sleep(4 * (attempt + 1))


def fetch(name):
    c = SOURCES[name]
    ids = sorted(q(c['url'], {'where': c['where'], 'returnIdsOnly': 'true'}).get('objectIds') or [])
    seen, pts, n = set(), [], page(c['url'])
    for i in range(0, len(ids), n):
        j = q(c['url'], {'objectIds': ','.join(map(str, ids[i:i + n])), 'outFields': c['key'], 'returnGeometry': 'false',
               'returnCentroid': 'true', 'outSR': 4326})
        for f in j.get('features', []):
            pid, ce = f['attributes'].get(c['key']), f.get('centroid')
            if not ce or pid in seen: continue
            seen.add(pid)
            lat, lon = round(ce['y'], 5), round(ce['x'], 5)
            b = c['box']
            if b[0] < lat < b[1] and b[2] < lon < b[3]: pts.append((lat, lon))
    print(name, len(ids), 'pool parcel records,', len(pts), 'distinct parcels placed', file=sys.stderr)
    return pts


def main(out, names):
    for n in names:
        if n not in SOURCES: sys.exit('unknown source: ' + n)
    ok = True
    for g in GROUPS:
        if not any(n in names for n in g): continue
        try: build(out, g)
        except Exception as e: print(','.join(g), 'skipped:', e, file=sys.stderr); ok = False
    if not ok: sys.exit(1)


def build(out, group):
    pts = []
    for name in group:
        p = fetch(name)
        if len(p) < SOURCES[name]['min']: raise RuntimeError('%s: too few pools (%d); keeping committed data' % (name, len(p)))
        pts += p
    tiles = collections.defaultdict(list)
    for lat, lon in pts: tiles['%d_%d' % (math.floor(lat * 20), math.floor(lon * 20))].append([lat, lon])
    # grid of county points for the OSM proximity test (cell ~ 30 m)
    cell = NEAR_M / 111000.0
    grid = set((math.floor(la / cell), math.floor(lo / cell)) for la, lo in pts)

    def near(la, lo):
        gy, gx = math.floor(la / cell), math.floor(lo / cell)
        return any((gy + dy, gx + dx) in grid for dy in (-1, 0, 1) for dx in (-1, 0, 1))

    os.makedirs(out, exist_ok=True)
    dropped = kept = 0
    for t, new in tiles.items():
        p = os.path.join(out, t + '.json'); old = []
        if os.path.exists(p):
            with open(p) as f: old = json.load(f)
        osm = []
        for e in old:
            if len(e) > 2 and e[2] == 'osm':
                if near(e[0], e[1]): dropped += 1
                else: osm.append(e); kept += 1
            # earlier county points in these tiles are replaced by this run
        with open(p, 'w') as f: json.dump(new + osm, f, separators=(',', ':'))
    print(','.join(group), len(pts), 'county pools in', len(tiles), 'tiles; OSM points dropped as duplicates:', dropped, 'kept:', kept,
          file=sys.stderr)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2:] or list(SOURCES))
