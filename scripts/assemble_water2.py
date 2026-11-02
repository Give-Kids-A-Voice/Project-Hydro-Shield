"""Merge each state's packed water bundles (scripts/pack_tiles.py) into the site's data/water2 folder.

  python3 scripts/assemble_water2.py <dest: _site/data/water2> <v1 tiles: _site/data/water> <state-dir> [<state-dir> ...]

- Two states can share a bundle (and a tile) along their border: their features are joined, each OSM id kept once per tile.
- A tile that already exists in the older per-region tiles (data/water: Florida, the six Southern California counties,
  Maricopa, Clark and the four Texas counties) is left out here, so those areas keep exactly the data they have today.
"""
import gzip, json, os, sys

dest, v1, states = sys.argv[1], sys.argv[2], sys.argv[3:]
os.makedirs(dest, exist_ok=True)
old = {fn[:-5] for fn in os.listdir(v1) if fn.endswith('.json')} if os.path.isdir(v1) else set()
names = {}
for s in states:
    if not os.path.isdir(s): print('missing', s); continue
    for fn in os.listdir(s):
        if fn.endswith('.json.gz'): names.setdefault(fn, []).append(os.path.join(s, fn))
shared = skipped = tiles = 0
for fn, paths in names.items():
    merged = {}
    for p in paths:
        for k, feats in json.loads(gzip.decompress(open(p, 'rb').read())).items():
            if k in old: skipped += 1; continue
            if k not in merged: merged[k] = feats; continue
            ids = {f['i'] for f in merged[k]}; merged[k] += [f for f in feats if f['i'] not in ids]; shared += 1
    tiles += len(merged)
    with open(os.path.join(dest, fn), 'wb') as fo:
        fo.write(gzip.compress(json.dumps(merged, separators=(',', ':')).encode(), 9, mtime=0))
print(len(names), 'bundles,', tiles, 'tiles,', shared, 'tiles shared by two states,', skipped, 'tiles left to data/water')
