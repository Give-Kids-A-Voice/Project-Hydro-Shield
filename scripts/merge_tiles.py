"""Copy tile files (JSON arrays) from each source dir into a destination dir; when two regions both have a tile
(e.g. on the California / Nevada line), their arrays are concatenated, dropping exact duplicates, instead of one
overwriting the other.

  python3 scripts/merge_tiles.py <dest-dir> <src-dir> [src-dir ...]
"""
import json, os, sys

dest = sys.argv[1]; os.makedirs(dest, exist_ok=True); merged = 0
for src in sys.argv[2:]:
    if not os.path.isdir(src): print('missing', src); continue
    for fn in os.listdir(src):
        if not fn.endswith('.json') or fn.startswith('_'): continue
        with open(os.path.join(src, fn)) as f: new = json.load(f)
        p = os.path.join(dest, fn)
        if os.path.exists(p):
            with open(p) as f: old = json.load(f)
            seen = set(json.dumps(e, sort_keys=True) for e in old)
            new = old + [e for e in new if json.dumps(e, sort_keys=True) not in seen]; merged += 1
        with open(p, 'w') as f: json.dump(new, f, separators=(',', ':'))
print(len(os.listdir(dest)), 'tiles,', merged, 'shared between regions and merged')
