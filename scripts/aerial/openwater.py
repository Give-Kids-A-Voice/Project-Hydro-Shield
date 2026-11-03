"""Drop detections that sit on open water (ocean, bays, lakes, reservoirs, marinas).

Sun glint on waves and ripples on lakes can look like small bright-blue pools. For every chunk that has detections,
read a decimated (~5 m) copy of the NAIP image from the file's overviews, mark water with NDWI, close small gaps
(glint speckle) and drop any detection inside, or within ~15 m of, a water body bigger than MIN_M2. Real pools are far
smaller than that, so they survive.

    python3 openwater.py <workdir> <year>        # rewrites <workdir>/chunks.jsonl, original kept as chunks.raw.jsonl

Use it only for coastal regions (ocean, bays, big marinas). On hazy inland imagery (2022 Texas NAIP) the NDWI test marked
yards and large apartment/community pools as open water and dropped thousands of real pools, so inland regions are
written from the unfiltered detections. Always sample the dropped detections too, not just the kept ones.
"""
import json, math, os, shutil, sys
import numpy as np
from scipy import ndimage as ndi
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import transform_bounds, transform as xform
from rasterio.windows import from_bounds
import naip

MIN_M2 = 6000      # an Olympic pool is ~1250 m2; anything this big and wet is a lake or the sea
PAD = 0.004        # deg of context around a chunk, so a coastline at the chunk edge is seen whole
NEAR_PX = 3        # at ~5 m pixels: within ~15 m of open water counts as on it


def water_map(item, bb):
    href = item["assets"]["image"]["href"] + "?" + naip.token()
    with rasterio.Env(GDAL_HTTP_MAX_RETRY=4, GDAL_HTTP_RETRY_DELAY=3):
        with rasterio.open(href) as ds:
            b = transform_bounds("EPSG:4326", ds.crs, *bb)
            w = from_bounds(*b, ds.transform).round_offsets().round_lengths()
            try: w = w.intersection(rasterio.windows.Window(0, 0, ds.width, ds.height))
            except rasterio.errors.WindowError: return None
            f = max(1, round(5 / ds.res[0]))
            h, wd = max(1, int(w.height // f)), max(1, int(w.width // f))
            a = ds.read(window=w, out_shape=(4, h, wd), resampling=Resampling.average).astype(np.float32)
            tr = ds.window_transform(w) * rasterio.Affine.scale(w.width / wd, w.height / h)
            px_m2 = abs(tr.a * tr.e)
            R, G, B, N = a
            valid = (R + G + B) > 0
            ndwi = (G - N) / (G + N + 1)
            wet = valid & (ndwi > 0.22)
            wet = ndi.binary_closing(wet, iterations=2)
            lab, n = ndi.label(wet)
            if n == 0: return None
            sz = ndi.sum(np.ones_like(lab), lab, range(1, n + 1)) * px_m2
            big = np.isin(lab, np.nonzero(sz >= MIN_M2)[0] + 1)
            if not big.any(): return None
            return ndi.binary_dilation(big, iterations=NEAR_PX), tr, ds.crs


def main(wd, year):
    ck = os.path.join(wd, "chunks.jsonl"); raw = os.path.join(wd, "chunks.raw.jsonl")
    if not os.path.exists(raw): shutil.copy(ck, raw)
    rows = [json.loads(l) for l in open(raw)]
    bb_all = (min(r["bb"][0] for r in rows), min(r["bb"][1] for r in rows), max(r["bb"][2] for r in rows), max(r["bb"][3] for r in rows))
    items = naip.items(bb_all, year)
    kept = dropped = 0
    out = []
    for i, r in enumerate(rows):
        det = r["det"]
        if det:
            b = r["bb"]; big = (b[0] - PAD, b[1] - PAD, b[2] + PAD, b[3] + PAD)
            fs = [f for f in items if f["bbox"][0] < big[2] and f["bbox"][2] > big[0] and f["bbox"][1] < big[3] and f["bbox"][3] > big[1]]
            maps = [m for m in (water_map(f, big) for f in fs) if m]
            if maps:
                keep = []
                for d in det:
                    on = False
                    for m, tr, crs in maps:
                        xs, ys = xform("EPSG:4326", crs, [d[1]], [d[0]])
                        c, rr = ~tr * (xs[0], ys[0]); c, rr = int(c), int(rr)
                        if 0 <= rr < m.shape[0] and 0 <= c < m.shape[1] and m[rr, c]: on = True; break
                    if on: dropped += 1
                    else: keep.append(d)
                det = keep
            kept += len(det)
        out.append({"bb": r["bb"], "det": det})
        if i % 50 == 0: print(f"{i}/{len(rows)} chunks, kept {kept}, dropped {dropped}", flush=True)
    with open(ck + ".tmp", "w") as f:
        for r in out: f.write(json.dumps(r) + "\n")
    os.replace(ck + ".tmp", ck)
    print(f"done: kept {kept}, dropped {dropped} on open water")


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]))
