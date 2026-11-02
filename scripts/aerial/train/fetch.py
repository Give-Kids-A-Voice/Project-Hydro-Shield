"""Fetch a NAIP mosaic for a lon/lat bbox into an npz (deleted after use). Resamples 0.3 m imagery to 0.6 m."""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))  # detect, cnn, naip
import sys, numpy as np, naip
from rasterio.warp import transform_bounds
def mosaic(bbox, year, state=None):
    fs = naip.items(bbox, year, state)
    if not fs: raise SystemExit('no items')
    # one CRS: pick the item covering the bbox center's zone (most common epsg)
    from collections import Counter
    epsg = Counter(f['properties']['proj:epsg'] for f in fs).most_common(1)[0][0]
    fs = [f for f in fs if f['properties']['proj:epsg'] == epsg]
    out = []
    for f in fs:
        a, tr, crs, res = naip.read(f, bbox)
        if a.size == 0: continue
        if res < 0.45:  # 0.3 m -> 0.6 m by 2x2 mean
            h, w = a.shape[1] // 2 * 2, a.shape[2] // 2 * 2
            a = a[:, :h, :w].reshape(a.shape[0], h // 2, 2, w // 2, 2).mean((2, 4)).astype(np.uint8)
            from affine import Affine
            tr = tr * Affine.scale(2)
        out.append((a, tr, crs, f['id']))
    return out
