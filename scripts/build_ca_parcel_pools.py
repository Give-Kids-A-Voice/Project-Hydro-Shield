"""Southern California pools from public parcel layers that carry an Assessor pool flag (public ArcGIS services, no login).

Run: python3 scripts/build_ca_parcel_pools.py docs/data/pools [sandiego] [palmdesert]

Sources:
  sandiego   SanGIS/SANDAG regional parcels (San Diego County Assessor data), POOL = 'Y'
             https://geo.sandag.org/server/rest/services/Hosted/Parcels/FeatureServer/0
  palmdesert City of Palm Desert parcels (Riverside County CREST property tax data), HAS_POOL = '1'
             https://services2.arcgis.com/i4mrGZu1Isvl0rWt/arcgis/rest/services/Palm_Desert_Parcels_CREST/FeatureServer/0
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
}
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


def fetch(name):
    c = SOURCES[name]
    ids = sorted(q(c['url'], {'where': c['where'], 'returnIdsOnly': 'true'}).get('objectIds') or [])
    seen, pts = set(), []
    for i in range(0, len(ids), 2000):
        j = q(c['url'], {'objectIds': ','.join(map(str, ids[i:i + 2000])), 'outFields': c['key'], 'returnGeometry': 'false',
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
    ok = True
    for n in names:
        try: build(out, n)
        except Exception as e: print(n, 'skipped:', e, file=sys.stderr); ok = False
    if not ok: sys.exit(1)


def build(out, name):
    pts = fetch(name)
    if len(pts) < SOURCES[name]['min']: raise RuntimeError('too few pools (%d); keeping committed data' % len(pts))
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
    print(name, len(pts), 'county pools in', len(tiles), 'tiles; OSM points dropped as duplicates:', dropped, 'kept:', kept,
          file=sys.stderr)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2:] or list(SOURCES))
