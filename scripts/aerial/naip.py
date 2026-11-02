"""NAIP windowed reads from Microsoft Planetary Computer STAC (collection "naip"; public, SAS-signed COGs, no account).
Only the window needed is range-read from each cloud-optimised GeoTIFF; nothing is saved to disk."""
import json, os, time, urllib.request, numpy as np
os.environ.setdefault("CURL_CA_BUNDLE", "/root/.ccr/ca-bundle.crt")
os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
os.environ.setdefault("GDAL_HTTP_MULTIRANGE", "YES")
os.environ.setdefault("GDAL_HTTP_MERGE_CONSECUTIVE_RANGES", "YES")
os.environ.setdefault("VSI_CACHE", "TRUE")
import rasterio
from rasterio.windows import from_bounds
from rasterio.warp import transform_bounds
STAC = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
_tok = {"t": None, "exp": 0}
def token():
    """Anonymous SAS token for the NAIP container. The API hands out a cached token whose expiry can be minutes away,
    so refresh whenever fewer than 10 minutes are left."""
    if not _tok["t"] or time.time() > _tok["exp"] - 600:
        for i in range(4):
            try: j = json.load(urllib.request.urlopen("https://planetarycomputer.microsoft.com/api/sas/v1/token/naip", timeout=60)); break
            except Exception as e: time.sleep(5 * (i + 1)); err = e
        else: raise err
        _tok["t"] = j["token"]
        try:
            from datetime import datetime
            _tok["exp"] = datetime.fromisoformat(j["msft:expiry"].replace("Z", "+00:00")).timestamp()
        except Exception: _tok["exp"] = time.time() + 900
        if _tok["exp"] - time.time() < 660: _tok["exp"] = time.time() + 660  # avoid refetching in a loop near rollover
    return _tok["t"]
def items(bbox, year=None, state=None):
    """All NAIP STAC items intersecting a lon/lat bbox (follows paging), optionally one year / state."""
    q = {"collections": ["naip"], "bbox": list(bbox), "limit": 250}
    if year: q["datetime"] = f"{year}-01-01T00:00:00Z/{year}-12-31T23:59:59Z"
    url, body, fs = STAC, q, []
    while url:
        r = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json"})
        for i in range(4):
            try: j = json.load(urllib.request.urlopen(r, timeout=90)); break
            except Exception as e: time.sleep(5 * (i + 1)); err = e
        else: raise err
        fs += j["features"]
        nxt = [l for l in j.get("links", []) if l.get("rel") == "next"]
        url, body = (nxt[0]["href"], nxt[0].get("body") or body) if nxt and j["features"] else (None, None)
    if state: fs = [f for f in fs if f["properties"].get("naip:state") == state]
    return fs
def read(item, bbox):
    """Read the part of one NAIP item inside lon/lat bbox. Returns (array[4,h,w] uint8, transform, crs)."""
    href = item["assets"]["image"]["href"] + "?" + token()
    with rasterio.Env(GDAL_HTTP_MAX_RETRY=4, GDAL_HTTP_RETRY_DELAY=3):
        with rasterio.open(href) as ds:
            b = transform_bounds("EPSG:4326", ds.crs, *bbox)
            w = from_bounds(*b, ds.transform).round_offsets().round_lengths()
            try: w = w.intersection(rasterio.windows.Window(0, 0, ds.width, ds.height))
            except rasterio.errors.WindowError:  # STAC footprint overlaps, raster does not
                return np.zeros((4, 0, 0), np.uint8), ds.transform, ds.crs, ds.res[0]
            a = ds.read(window=w)
            return a, ds.window_transform(w), ds.crs, ds.res[0]
