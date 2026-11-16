"""python3 pond_write.py <workdir> [sheet indices to drop...]
Drops the given ponds (indices on psheet.py's sheet: random.seed(7) sample), then writes the rest into
docs/data/ponds/<y>_<x>.json (0.05-degree tiles keyed by the pond centre) as {"i": id, "g": [ring]} with ring
[[lat, lon], ...]. A pond already in a tile (same id) is replaced, so re-running an area doesn't duplicate."""
import sys, os, json, math, random
wd = sys.argv[1]; drop = {int(x) for x in sys.argv[2:]}
P = [json.loads(l) for l in open(wd + '/ponds.jsonl')]
random.seed(7); pick = random.sample(P, min(48, len(P)))
bad = {(pick[i][0], pick[i][1]) for i in drop}
P = [p for p in P if (p[0], p[1]) not in bad]
D = '/home/claude/project-hydro-shield/docs/data/ponds'; os.makedirs(D, exist_ok=True)
by = {}
for p in P:
    k = f'{math.floor(p[0] * 20)}_{math.floor(p[1] * 20)}'
    by.setdefault(k, []).append({'i': f'ap{round(p[0] * 1e5)}_{round(p[1] * 1e5)}', 'g': [p[4]]})
n = 0
for k, fs in by.items():
    f = f'{D}/{k}.json'; old = json.load(open(f)) if os.path.exists(f) else []
    ids = {x['i'] for x in fs}; old = [x for x in old if x['i'] not in ids]
    json.dump(old + fs, open(f, 'w'), separators=(',', ':')); n += len(fs)
open(wd + '/WRITTEN', 'w').write(str(n))
print(f'{wd}: wrote {n} ponds into {len(by)} tiles ({len(bad)} dropped in review)')
