import json, math, os
POOLS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'docs', 'data', 'pools')
def load(bbox, kinds=('county',)):
    lon0, lat0, lon1, lat1 = bbox; out = []
    for y in range(math.floor(lat0 * 20), math.floor(lat1 * 20) + 1):
        for x in range(math.floor(lon0 * 20), math.floor(lon1 * 20) + 1):
            p = f'{POOLS}/{y}_{x}.json'
            if not os.path.exists(p): continue
            for e in json.load(open(p)):
                k = e[2] if len(e) > 2 else 'county'
                if k in kinds and lon0 <= e[1] <= lon1 and lat0 <= e[0] <= lat1: out.append((e[0], e[1], k))
    return out
