"""Pack one state's water tiles (from build_water_tiles.py --simplify 5) into compact gzip bundles for this site.

  python3 scripts/pack_tiles.py <tiles-dir> <out-dir> [--pools docs/data/pools]

Packed ("v2") feature = {"i": id, "t": tags, "l": 0|1, "d": [[lat0, lon0, dlat1, dlon1, ...], ...]}
  "d" rings are integer 1e-5 degree steps, delta-encoded from the previous point (the first is absolute),
  so 37.12345,-82.54321 -> 3712345,-8254321 and the next point is a small pair like 3,-12.
Bundle = 4x4 tiles (0.2 degrees): <out-dir>/<floor(y/4)>_<floor(x/4)>.json.gz holding gzip({"<y>_<x>": [features]}),
where y_x is the usual 0.05-degree tile key. Bundling keeps the file count low enough for GitHub Pages
(one big state is ~1-2 thousand files instead of ~25 thousand). GitHub Pages serves .gz without Content-Encoding,
so docs/index.html un-gzips it with DecompressionStream.
--pools: OSM pool points within ~30 m of any pool already in docs/data/pools are dropped, so a pool is never listed twice.
"""
import collections, gzip, json, math, os, sys

src, out = sys.argv[1], sys.argv[2]
pools = sys.argv[sys.argv.index('--pools') + 1] if '--pools' in sys.argv else None
CELL = 30.0 / 111000.0
os.makedirs(out, exist_ok=True)
grid_cache = {}


def bundle_of(key):
    y, x = map(int, key.split('_')); return f'{y // 4}_{x // 4}'


def pool_grid(key):
    """Grid cells (~30 m) holding committed pool records in this tile and its neighbours."""
    if key in grid_cache: return grid_cache[key]
    y, x = map(int, key.split('_')); g = set()
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            p = os.path.join(pools, f'{y + dy}_{x + dx}.json') if pools else ''
            if p and os.path.exists(p):
                for e in json.load(open(p)):
                    # aerial estimates ("air") never displace an OpenStreetMap pool; the page drops the estimate instead
                    if len(e) > 2 and e[2] == 'air': continue
                    g.add((math.floor(e[0] / CELL), math.floor(e[1] / CELL)))
    grid_cache[key] = g; return g


def near(g, la, lo):
    gy, gx = math.floor(la / CELL), math.floor(lo / CELL)
    return any((gy + a, gx + b) in g for a in (-1, 0, 1) for b in (-1, 0, 1))


def pack(feats, g):
    res = []; dropped = 0
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
    return res, dropped


groups = collections.defaultdict(list)
for fn in os.listdir(src):
    if fn.endswith('.json') and not fn.startswith('_'): groups[bundle_of(fn[:-5])].append(fn[:-5])
n = dropped = 0
for b, keys in groups.items():
    obj = {}
    for k in sorted(keys):
        res, dr = pack(json.load(open(os.path.join(src, k + '.json'))), pool_grid(k) if pools else set())
        dropped += dr; n += 1
        if res: obj[k] = res
    with open(os.path.join(out, b + '.json.gz'), 'wb') as fo:
        fo.write(gzip.compress(json.dumps(obj, separators=(',', ':')).encode(), 9, mtime=0))
print(n, 'tiles packed into', len(groups), 'bundles,', dropped, 'OSM pools dropped as duplicates of committed pool records')
