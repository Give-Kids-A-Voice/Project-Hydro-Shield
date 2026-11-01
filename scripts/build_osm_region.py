"""Water features and pool points for a region outside Florida, straight from an OpenStreetMap extract.

Used for Southern California (Los Angeles, Orange, Ventura, Riverside and San Bernardino counties), where
assessors publish no pool flag. Pure Python (pyosmium + shapely), so it runs the same in CI and locally.

  python3 scripts/build_osm_region.py filter  socal-latest.osm.pbf  socal-water.osm.pbf
  python3 scripts/build_osm_region.py export  socal-water.osm.pbf  socal-water.geojsonseq  pools-out-dir

filter: keeps the same water tags as the Florida build (plus pool nodes/relations and county boundaries), with the nodes they need.
export: clips to the five counties and writes
  - a GeoJSON sequence in `osmium export` form for scripts/build_water_tiles.py (pools left out: they become points instead,
    so one pool is never counted twice), and
  - pool points into <pools-out-dir>/<floor(lat*20)>_<floor(lon*20)>.json as [lat, lon, "osm"], deduplicated
    (a pool mapped twice, or as both a node and an outline, within ~4 m is kept once).
"""
import json, math, os, sys, collections
import osmium
from shapely.geometry import shape
from shapely.ops import unary_union
from shapely.prepared import prep

COUNTIES = {'Los Angeles County', 'Orange County', 'Ventura County', 'Riverside County', 'San Bernardino County'}
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
            if a.from_way() is False and is_county(t): counties.append(shape(g)); return
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
    for k, v in tiles.items():
        p = os.path.join(pool_dir, k + '.json')
        if os.path.exists(p): sys.exit('pool tile %s already exists (region overlaps another source)' % p)
        with open(p, 'w') as f: json.dump(v, f, separators=(',', ':'))
    print(nw, 'water features,', np_, 'pools (', len(pools), 'before dedupe/clip ),', len(tiles), 'pool tiles')


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'filter': do_filter(sys.argv[2], sys.argv[3])
    elif cmd == 'export': do_export(sys.argv[2], sys.argv[3], sys.argv[4])
    else: sys.exit(__doc__)
