"""Water features and pool points for a region outside Florida, straight from an OpenStreetMap extract.

Used for Southern California (Los Angeles, Orange, Ventura, Riverside, San Bernardino and San Diego counties), where most
assessors publish no pool flag (San Diego pool records come from scripts/build_ca_parcel_pools.py). Pure Python (pyosmium + shapely), so it runs the same in CI and locally.

  python3 scripts/build_osm_region.py filter  socal-latest.osm.pbf  socal-water.osm.pbf  [region]
  python3 scripts/build_osm_region.py export  socal-water.osm.pbf  socal-water.geojsonseq  pools-out-dir  [region]

region (default socal) picks the counties from REGIONS below: socal, arizona (Maricopa), nevada (Clark),
texas (Harris, Tarrant, Dallas, Collin). The input can be any OSM file pyosmium reads (.osm.pbf, or .osm XML).

filter: keeps the same water tags as the Florida build (plus pool nodes/relations and county boundaries), with the nodes they need.
  python3 scripts/build_osm_region.py merge   pools-out-dir  docs/data/pools

export: clips to the region's counties and writes
  - a GeoJSON sequence in `osmium export` form for scripts/build_water_tiles.py (pools left out: they become points instead,
    so one pool is never counted twice), and
  - pool points into <pools-out-dir>/<floor(lat*20)>_<floor(lon*20)>.json as [lat, lon, "osm"], deduplicated
    (a pool mapped twice, or as both a node and an outline, within ~4 m is kept once), plus _region.json (the clip area).
merge: folds a fresh export's pool points into the committed tiles (see do_merge), so a water refresh never needs
the county pool downloads again.
"""
import json, math, os, sys, collections
import osmium
from shapely.geometry import shape
from shapely.ops import unary_union
from shapely.prepared import prep

# region -> (county names, bbox lat0, lat1, lon0, lon1 that each county's interior point must fall in)
REGIONS = {
    'socal': ({'Los Angeles County', 'Orange County', 'Ventura County', 'Riverside County', 'San Bernardino County',
               'San Diego County'}, (32.4, 35.9, -121.5, -114.0)),
    'arizona': ({'Maricopa County'}, (32.4, 34.1, -113.4, -111.0)),
    'nevada': ({'Clark County'}, (35.0, 37.0, -115.9, -114.0)),
    'texas': ({'Harris County', 'Tarrant County', 'Dallas County', 'Collin County'}, (29.4, 33.5, -97.6, -94.9)),
}
COUNTIES, BBOX = REGIONS['socal']
WATERWAY_LINES = {'canal', 'ditch', 'drain', 'stream', 'river'}


def is_county(t):
    return t.get('boundary') == 'administrative' and t.get('admin_level') == '6' and t.get('name') in COUNTIES


def is_pool(t):
    return t.get('leisure') == 'swimming_pool'


def is_water(t, kind):
    """Same selection as the Florida osmium tags-filter in .github/workflows/water-tiles.yml."""
    if t.get('natural') == 'water' or t.get('landuse') in ('basin', 'reservoir'): return True
    if kind == 'n': return t.get('amenity') == 'fountain'
    if kind == 'w':
        return (t.get('leisure') == 'water_park' or t.get('waterway') in WATERWAY_LINES | {'riverbank'}
                or t.get('amenity') == 'fountain')
    return False


def keep(o, kind):
    t = o.tags
    return is_pool(t) or is_water(t, kind) or (kind == 'r' and is_county(t))


def do_filter(src, dst):
    with osmium.BackReferenceWriter(dst, ref_src=src, overwrite=True) as w:
        for o in osmium.FileProcessor(src):
            kind = 'n' if o.is_node() else 'w' if o.is_way() else 'r'
            if keep(o, kind): w.add(o)


def do_export(src, out_seq, pool_dir):
    gj = osmium.geom.GeoJSONFactory()
    counties, feats, pools = [], [], []

    class H(osmium.SimpleHandler):
        def node(self, n):
            t = dict(n.tags)
            if is_pool(t): pools.append((n.location.lat, n.location.lon))
            elif t.get('amenity') == 'fountain':
                feats.append(('n%d' % n.id, t, {'type': 'Point', 'coordinates': [n.location.lon, n.location.lat]}))

        def way(self, w):
            t = dict(w.tags)
            if t.get('waterway') in WATERWAY_LINES and not is_pool(t):
                try: feats.append(('w%d' % w.id, t, json.loads(gj.create_linestring(w))))
                except Exception: pass

        def area(self, a):
            t = dict(a.tags)
            try: g = json.loads(gj.create_multipolygon(a))
            except Exception: return
            fid = ('w%d' if a.from_way() else 'r%d') % a.orig_id()
            if a.from_way() is False and is_county(t):
                sh = shape(g); c = sh.representative_point()
                if BBOX[0] < c.y < BBOX[1] and BBOX[2] < c.x < BBOX[3]: counties.append(sh)
                return
            if is_pool(t):
                c = shape(g).representative_point(); pools.append((c.y, c.x)); return
            if is_water(t, 'w' if a.from_way() else 'r') and t.get('waterway') not in WATERWAY_LINES:
                feats.append((fid, t, g))

    H().apply_file(src, locations=True, idx='flex_mem')
    if len(counties) != len(COUNTIES):
        sys.exit('expected %d county boundaries, found %d' % (len(COUNTIES), len(counties)))
    region = prep(unary_union(counties).buffer(0.005))   # ~500 m so water on a county line is kept
    nw = 0
    with open(out_seq, 'w') as f:
        for fid, t, g in feats:
            if not region.intersects(shape(g)): continue
            f.write('\x1e' + json.dumps({'type': 'Feature', 'id': fid, 'properties': t, 'geometry': g}) + '\n'); nw += 1
    # Dedupe pools on a ~4 m grid (and its neighbours), then tile.
    from shapely.geometry import Point
    seen, tiles, np_ = set(), collections.defaultdict(list), 0
    for lat, lon in pools:
        if not region.contains(Point(lon, lat)): continue
        gy, gx = round(lat / 0.00004), round(lon / 0.00004)
        if any((gy + dy, gx + dx) in seen for dy in (-1, 0, 1) for dx in (-1, 0, 1)): continue
        seen.add((gy, gx)); np_ += 1
        tiles['%d_%d' % (math.floor(lat * 20), math.floor(lon * 20))].append([round(lat, 5), round(lon, 5), 'osm'])
    os.makedirs(pool_dir, exist_ok=True)
    from shapely.geometry import mapping
    with open(os.path.join(pool_dir, '_region.json'), 'w') as f:   # clip area, used by `merge`; not a tile
        json.dump(mapping(unary_union(counties).buffer(0.005).simplify(0.001)), f)
    for k, v in tiles.items():
        p = os.path.join(pool_dir, k + '.json')
        if os.path.exists(p): sys.exit('pool tile %s already exists (region overlaps another source)' % p)
        with open(p, 'w') as f: json.dump(v, f, separators=(',', ':'))
    print(nw, 'water features,', np_, 'pools (', len(pools), 'before dedupe/clip ),', len(tiles), 'pool tiles')


def do_merge(pool_dir, dest):
    """Merge a fresh `export` pool dir into the committed tiles (dest) without re-downloading county records:
    old OSM points inside this region are replaced; county/assessor points are never touched; a new OSM point within
    ~30 m of a county point in the same or a neighbouring tile is dropped as a duplicate (same rule as the county builds).
    Tiles shared with a neighbouring region (e.g. Clark County NV / San Bernardino CA) keep the other region's points."""
    from shapely.geometry import Point
    with open(os.path.join(pool_dir, '_region.json')) as f: reg = shape(json.load(f))
    region = prep(reg); x0, y0, x1, y1 = reg.bounds
    new = {}
    for fn in os.listdir(pool_dir):
        if fn.endswith('.json') and not fn.startswith('_'):
            with open(os.path.join(pool_dir, fn)) as f: new[fn[:-5]] = json.load(f)
    keys = set(new)
    for fn in os.listdir(dest):   # committed tiles that overlap the region, so stale OSM points there are removed too
        if not fn.endswith('.json'): continue
        a, b = map(int, fn[:-5].split('_'))
        if a / 20 <= y1 and (a + 1) / 20 >= y0 and b / 20 <= x1 and (b + 1) / 20 >= x0: keys.add(fn[:-5])
    old = {}
    for k in keys:
        p = os.path.join(dest, k + '.json')
        if os.path.exists(p):
            with open(p) as f: old[k] = json.load(f)
    cell = 30.0 / 111000.0
    grid = set((math.floor(e[0] / cell), math.floor(e[1] / cell)) for v in old.values() for e in v if len(e) < 3 or e[2] not in ('osm', 'air'))  # aerial estimates never displace an OSM pool
    def near(la, lo):
        gy, gx = math.floor(la / cell), math.floor(lo / cell)
        return any((gy + dy, gx + dx) in grid for dy in (-1, 0, 1) for dx in (-1, 0, 1))
    removed = added = dup = 0
    for k in keys:
        rest = []
        for e in old.get(k, []):
            if len(e) > 2 and e[2] == 'osm' and region.contains(Point(e[1], e[0])): removed += 1
            else: rest.append(e)
        for e in new.get(k, []):
            if near(e[0], e[1]): dup += 1
            else: rest.append(e); added += 1
        p = os.path.join(dest, k + '.json')
        if rest or os.path.exists(p):
            with open(p, 'w') as f: json.dump(rest, f, separators=(',', ':'))
    print('OSM pools merged: %d added, %d dropped as duplicates of county records, %d old OSM points replaced' % (added, dup, removed))


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'filter': COUNTIES, BBOX = REGIONS[sys.argv[4] if len(sys.argv) > 4 else 'socal']; do_filter(sys.argv[2], sys.argv[3])
    elif cmd == 'export': COUNTIES, BBOX = REGIONS[sys.argv[5] if len(sys.argv) > 5 else 'socal']; do_export(sys.argv[2], sys.argv[3], sys.argv[4])
    elif cmd == 'merge': do_merge(sys.argv[2], sys.argv[3])
    else: sys.exit(__doc__)
