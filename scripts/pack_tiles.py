"""Pack water tiles from build_water_tiles.py for the nationwide host (format v2), gzip-compressed.

  python3 scripts/pack_tiles.py <tiles-dir> <out-dir> [--pools docs/data/pools]

v2 tile = JSON list of {"i": id, "t": tags, "l": 0|1, "d": [[dlat0, dlon0, dlat1, dlon1, ...], ...]}
  "d" rings are integer 1e-5 degree steps, delta-encoded from the previous point (the first is absolute),
  so 37.12345,-82.54321 -> 3712345,-8254321 and the next point is a small pair like 3,-12.
  This is about 2x smaller raw and ~30% smaller gzipped than the 5-decimal "g" lists (measured on Michigan).
--pools: OSM pool points (tags leisure=swimming_pool, single point) within ~30 m of a county pool record in
  docs/data/pools are dropped, so a pool already in the county records is not listed twice.
Writes <out-dir>/<key>.json as gzip bytes (uploaded with Content-Encoding: gzip).
"""
import gzip, json, math, os, sys

src, out = sys.argv[1], sys.argv[2]
pools = sys.argv[sys.argv.index('--pools') + 1] if '--pools' in sys.argv else None
CELL = 30.0 / 111000.0
os.makedirs(out, exist_ok=True)
grid_cache = {}


def county_grid(key):
    """Grid cells (~30 m) holding county pool records in this tile and its neighbours."""
    if key in grid_cache: return grid_cache[key]
    y, x = map(int, key.split('_')); g = set()
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            p = os.path.join(pools, f'{y + dy}_{x + dx}.json') if pools else ''
            if p and os.path.exists(p):
                for e in json.load(open(p)):
                    if len(e) < 3 or e[2] != 'osm': g.add((math.floor(e[0] / CELL), math.floor(e[1] / CELL)))
    grid_cache[key] = g; return g


def near(g, la, lo):
    gy, gx = math.floor(la / CELL), math.floor(lo / CELL)
    return any((gy + a, gx + b) in g for a in (-1, 0, 1) for b in (-1, 0, 1))


n = dropped = 0
for fn in sorted(os.listdir(src)):
    if not fn.endswith('.json'): continue
    key = fn[:-5]; feats = json.load(open(os.path.join(src, fn))); res = []
    g = county_grid(key) if pools else set()
    for f in feats:
        if g and f['t'].get('leisure') == 'swimming_pool' and len(f['g']) == 1 and len(f['g'][0]) == 1 \
                and near(g, *f['g'][0][0]):
            dropped += 1; continue
        d = []
        for r in f['g']:
            py = px = 0; o = []
            for la, lo in r:
                iy, ix = round(la * 1e5), round(lo * 1e5); o += [iy - py, ix - px]; py, px = iy, ix
            d.append(o)
        res.append({'i': f['i'], 't': f['t'], 'l': f.get('l', 0), 'd': d})
    with open(os.path.join(out, fn), 'wb') as fo:
        fo.write(gzip.compress(json.dumps(res, separators=(',', ':')).encode(), 9, mtime=0))
    n += 1
print(n, 'tiles packed,', dropped, 'OSM pools dropped as county duplicates')
