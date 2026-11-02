"""Whole-state water features (and OpenStreetMap pools) for the nationwide layer, from a Geofabrik state extract.

Same water selection as Florida and scripts/build_osm_region.py, but with no county clip: everything in the extract is
kept. Pools become single points (one per pool, deduplicated on a ~4 m grid) so a pool costs ~60 bytes, not an outline.

  python3 scripts/build_osm_state.py filter  state-latest.osm.pbf  state-water.osm.pbf
  python3 scripts/build_osm_state.py export  state-water.osm.pbf  state-water.geojsonseq
then
  python3 scripts/build_water_tiles.py state-water.geojsonseq tiles-dir [--simplify METERS]

Output is the GeoJSON sequence `osmium export` writes, so build_water_tiles.py is unchanged.
"""
import json, sys
import osmium

WATERWAY_LINES = {'canal', 'ditch', 'drain', 'stream', 'river'}


def is_pool(t):
    return t.get('leisure') == 'swimming_pool'


def is_water(t, kind):
    if t.get('natural') == 'water' or t.get('landuse') in ('basin', 'reservoir'): return True
    if kind == 'n': return t.get('amenity') == 'fountain'
    if kind == 'w':
        return (t.get('leisure') == 'water_park' or t.get('waterway') in WATERWAY_LINES | {'riverbank'}
                or t.get('amenity') == 'fountain')
    return False


def do_filter(src, dst):
    with osmium.BackReferenceWriter(dst, ref_src=src, overwrite=True) as w:
        for o in osmium.FileProcessor(src):
            kind = 'n' if o.is_node() else 'w' if o.is_way() else 'r'
            if is_pool(o.tags) or is_water(o.tags, kind): w.add(o)


def do_export(src, out_seq):
    gj = osmium.geom.GeoJSONFactory()
    out = open(out_seq, 'w'); seen = set(); cnt = {'water': 0, 'line': 0, 'pool': 0}

    def emit(fid, t, g):
        out.write('\x1e' + json.dumps({'type': 'Feature', 'id': fid, 'properties': t, 'geometry': g}) + '\n')

    def pool(fid, lat, lon, t):
        gy, gx = round(lat / 0.00004), round(lon / 0.00004)
        if any((gy + dy, gx + dx) in seen for dy in (-1, 0, 1) for dx in (-1, 0, 1)): return
        seen.add((gy, gx)); cnt['pool'] += 1
        emit(fid, {'leisure': 'swimming_pool', **({'access': t['access']} if 'access' in t else {})},
             {'type': 'Point', 'coordinates': [round(lon, 5), round(lat, 5)]})

    class H(osmium.SimpleHandler):
        def node(self, n):
            t = dict(n.tags)
            if is_pool(t): pool('n%d' % n.id, n.location.lat, n.location.lon, t)
            elif t.get('amenity') == 'fountain':
                emit('n%d' % n.id, t, {'type': 'Point', 'coordinates': [n.location.lon, n.location.lat]})

        def way(self, w):
            t = dict(w.tags)
            if t.get('waterway') in WATERWAY_LINES and not is_pool(t):
                try: emit('w%d' % w.id, t, json.loads(gj.create_linestring(w))); cnt['line'] += 1
                except Exception: pass

        def area(self, a):
            t = dict(a.tags)
            fid = ('w%d' if a.from_way() else 'r%d') % a.orig_id()
            if is_pool(t):
                try:
                    from shapely.geometry import shape
                    c = shape(json.loads(gj.create_multipolygon(a))).representative_point()
                except Exception: return
                pool(fid, c.y, c.x, t); return
            if is_water(t, 'w' if a.from_way() else 'r') and t.get('waterway') not in WATERWAY_LINES:
                try: emit(fid, t, json.loads(gj.create_multipolygon(a))); cnt['water'] += 1
                except Exception: pass

    H().apply_file(src, locations=True, idx='flex_mem')
    out.close(); print(cnt)


if __name__ == '__main__':
    if sys.argv[1] == 'filter': do_filter(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == 'export': do_export(sys.argv[2], sys.argv[3])
    else: sys.exit(__doc__)
