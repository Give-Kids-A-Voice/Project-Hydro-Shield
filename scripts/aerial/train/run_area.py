"""Fetch NAIP for a bbox, extract candidates, return list of dicts with lat/lon + features; deletes imagery after."""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))  # detect, cnn, naip
import sys, json, numpy as np, time
from pyproj import Transformer
import fetch, detect
def process(bbox, year, chunk=0.01):
    lon0, lat0, lon1, lat1 = bbox; res = []
    lats = np.arange(lat0, lat1 - 1e-9, chunk); lons = np.arange(lon0, lon1 - 1e-9, chunk)
    for la in lats:
        for lo in lons:
            bb = (lo, la, min(lo + chunk, lon1), min(la + chunk, lat1))
            M = 0.0004  # read a ~40 m margin so pools on the chunk edge are whole
            for a, tr, crs, iid in fetch.mosaic((bb[0] - M, bb[1] - M, bb[2] + M, bb[3] + M), year):
                T = Transformer.from_crs(crs, 'EPSG:4326', always_xy=True)
                for cy, cx, f in detect.candidates(a):
                    x, y = tr * (cx + 0.5, cy + 0.5); lon, lat = T.transform(x, y)
                    # one mosaic piece per item; keep only centroids inside this chunk (items overlap at seams)
                    if bb[0] <= lon < bb[2] and bb[1] <= lat < bb[3]:
                        f.update(lat=lat, lon=lon, item=iid); res.append(f)
                del a
    # items overlap: drop near-duplicate centroids (< 3 m)
    res.sort(key=lambda f: (round(f['lat'], 4), round(f['lon'], 4))); out = []
    seen = {}
    for f in res:
        k = (round(f['lat'] * 3600), round(f['lon'] * 3600))
        dup = any(abs(g['lat'] - f['lat']) < 3e-5 and abs(g['lon'] - f['lon']) < 3e-5 for kk in [(k[0]+i, k[1]+j) for i in (-1,0,1) for j in (-1,0,1)] for g in seen.get(kk, []))
        if not dup: seen.setdefault(k, []).append(f); out.append(f)
    return out
if __name__ == '__main__':
    name = sys.argv[1]; bbox = tuple(map(float, sys.argv[2:6])); year = int(sys.argv[6])
    t = time.time(); c = process(bbox, year)
    np.savez_compressed(f'cand/{name}_patches.npz', p=np.array([f.pop('_patch') for f in c], np.uint8).reshape(-1, 4, 40, 40),
                        s=np.array([f.pop('_scene') for f in c], np.float32).reshape(-1, 4))
    json.dump({'bbox': bbox, 'year': year, 'cands': [{k: (float(v) if isinstance(v, (np.floating, float, np.integer)) else v) for k, v in f.items()} for f in c]}, open(f'cand/{name}.json', 'w'))
    print(name, len(c), 'candidates', round(time.time() - t), 's')
