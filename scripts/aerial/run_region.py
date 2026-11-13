"""Aerial pool estimates for one region from USDA NAIP imagery -> [lat, lon, "air"] points in docs/data/pools tiles.

Run (from the repo root; needs numpy scipy scikit-image scikit-learn rasterio pyproj torch(cpu)):
  python3 scripts/aerial/run_region.py <name> <lon0> <lat0> <lon1> <lat1> <naip-year> [--write docs/data/pools]
      [--threshold 0.7] [--workdir /tmp/aerial-<name>]

What it does, per 0.01-degree chunk (about 1 x 1.1 km, read with a 40 m margin):
  1. Reads only that window of the NAIP 4-band COGs from Microsoft Planetary Computer (public, SAS-signed, no
     account), in memory. 0.3 m imagery (e.g. Arizona 2023) is averaged to 0.6 m. No imagery is written to disk.
  2. detect.candidates(): scene-relative spectral mask (bright, blue and green well above red relative to the scene's
     own colour cast, NIR below green), connected components, 6-2500 m2, 32 shape/colour/context features and a
     40 x 40 px patch around each one.
  3. Scores each candidate with a gradient-boosting model on the features and a 3-seed tiny CNN on the patch
     (model/), and keeps the average >= threshold (0.7, chosen on held-out areas: see README.md).
  Chunk results are checkpointed in <workdir>/chunks.jsonl, so a stopped run resumes where it left off.
At the end: detections within 8 m are merged, and with --write each tile in the region gets its "air" points replaced.
Air points within 30 m of a county or OpenStreetMap pool point already in the tile are not written (the page also
drops any within 30 m of an OpenStreetMap pool it loads). Tiles with county pool records are never given air points:
aerial estimates are only for places without county records.
"""
import argparse, json, math, os, pickle, sys, time
from collections import Counter
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import naip, detect, cnn  # noqa: E402
from pyproj import Transformer  # noqa: E402
from affine import Affine  # noqa: E402
import torch  # noqa: E402

CHUNK, MARGIN = 0.01, 0.0004


def load_models():
    gbm = pickle.load(open(os.path.join(HERE, 'model', 'gbm.pkl'), 'rb'))
    nets = []
    for k in range(3):
        m = cnn.Net(); m.load_state_dict(torch.load(os.path.join(HERE, 'model', f'cnn{k}.pt'))); m.eval(); nets.append(m)
    return gbm, nets


def proj(f):
    """An item's projection: 'proj:epsg' in older NAIP records, 'proj:code' ("EPSG:26916") in newer ones such as 2025."""
    p = f['properties']
    return p['proj:epsg'] if 'proj:epsg' in p else int(str(p['proj:code']).split(':')[-1])


def mosaic(bb, year, items):
    """Windows of every NAIP item (of the most common projection) that overlaps bb."""
    fs = [f for f in items if f['bbox'][0] < bb[2] and f['bbox'][2] > bb[0] and f['bbox'][1] < bb[3] and f['bbox'][3] > bb[1]]
    if not fs: return []
    epsg = Counter(proj(f) for f in fs).most_common(1)[0][0]
    out = []
    for f in fs:
        if proj(f) != epsg: continue
        a, tr, crs, res = naip.read(f, bb)
        if a.size == 0 or a.shape[1] < 50 or a.shape[2] < 50: continue
        if res < 0.45:
            h, w = a.shape[1] // 2 * 2, a.shape[2] // 2 * 2
            a = a[:, :h, :w].reshape(a.shape[0], h // 2, 2, w // 2, 2).mean((2, 4)).astype(np.uint8); tr = tr * Affine.scale(2)
        out.append((a, tr, crs))
    return out


def score_chunk(bb, year, items, gbm, nets, thr):
    big = (bb[0] - MARGIN, bb[1] - MARGIN, bb[2] + MARGIN, bb[3] + MARGIN); res = []
    for a, tr, crs in mosaic(big, year, items):
        if (a[:3].max(0) == 0).mean() > 0.5: continue  # mostly outside the image footprint
        C = detect.candidates(a)
        if not C: continue
        X = np.array([[f[k] for k in detect.FEATS] for _, _, f in C])
        P = cnn.prep(np.array([f['_patch'] for _, _, f in C], np.uint8), np.array([f['_scene'] for _, _, f in C], np.float32))
        p = (gbm.predict_proba(X)[:, 1] + np.mean([cnn.predict(m, P) for m in nets], 0)) / 2
        T = Transformer.from_crs(crs, 'EPSG:4326', always_xy=True)
        for (cy, cx, f), s in zip(C, p):
            if s < thr: continue
            x, y = tr * (cx + 0.5, cy + 0.5); lon, lat = T.transform(x, y)
            if bb[0] <= lon < bb[2] and bb[1] <= lat < bb[3]: res.append([round(lat, 6), round(lon, 6), round(float(s), 3)])
        del a
    return res


def merge(det, R=8.0):
    """Strongest first; drop anything within R m of a kept detection (pool split in two, pool plus attached spa,
    the same pool seen in two overlapping NAIP quarter-quads)."""
    det = sorted(det, key=lambda d: -d[2]); kept, grid = [], {}
    if not det: return kept
    kx = 111320 * math.cos(math.radians(det[0][0])); c = 0.0002
    for d in det:
        y, x = int(d[0] // c), int(d[1] // c)
        if any(math.hypot((q[0] - d[0]) * 110574, (q[1] - d[1]) * kx) < R
               for i in (-1, 0, 1) for j in (-1, 0, 1) for q in grid.get((y + i, x + j), [])): continue
        grid.setdefault((y, x), []).append(d); kept.append(d)
    return kept


def write_tiles(pools_dir, bbox, det):
    """Replace "air" points inside bbox, tile by tile. Returns (written, skipped_dup, skipped_county_tile)."""
    by = {}
    for d in det: by.setdefault('%d_%d' % (math.floor(d[0] * 20), math.floor(d[1] * 20)), []).append(d)
    keys = set(by)
    for y in range(math.floor(bbox[1] * 20), math.floor(bbox[3] * 20) + 1):
        for x in range(math.floor(bbox[0] * 20), math.floor(bbox[2] * 20) + 1): keys.add('%d_%d' % (y, x))
    n = dup = cty = 0
    for k in sorted(keys):
        p = os.path.join(pools_dir, k + '.json'); old = json.load(open(p)) if os.path.exists(p) else []
        inside = lambda e: bbox[0] <= e[1] < bbox[2] and bbox[1] <= e[0] < bbox[3]
        keep = [e for e in old if not (len(e) > 2 and e[2] == 'air' and inside(e))]
        known = [e for e in keep if not (len(e) > 2 and e[2] == 'air')]
        if any(len(e) < 3 or e[2] not in ('osm', 'air') for e in known):  # county records here: no estimates
            cty += len(by.get(k, [])); new = []
        else:
            kx = 111320 * math.cos(math.radians(int(k.split('_')[0]) / 20))
            new = []
            for d in by.get(k, []):
                if any(math.hypot((e[0] - d[0]) * 110574, (e[1] - d[1]) * kx) < 30 for e in known): dup += 1; continue
                new.append([round(d[0], 5), round(d[1], 5), 'air'])
        out = keep + new
        if out != old:
            if out:
                with open(p, 'w') as f: json.dump(out, f, separators=(',', ':'))
            elif os.path.exists(p): os.remove(p)
        n += len(new)
    return n, dup, cty


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('name'); ap.add_argument('bbox', nargs=4, type=float); ap.add_argument('year', type=int)
    ap.add_argument('--write'); ap.add_argument('--threshold', type=float, default=0.7); ap.add_argument('--workdir')
    a = ap.parse_args(); bbox = tuple(a.bbox)
    wd = a.workdir or os.path.join('/tmp', 'aerial-' + a.name); os.makedirs(wd, exist_ok=True)
    ck = os.path.join(wd, 'chunks.jsonl'); done = {}
    if os.path.exists(ck):
        for line in open(ck): j = json.loads(line); done[tuple(j['bb'])] = j['det']
    gbm, nets = load_models()
    items = naip.items(bbox, a.year)
    print(a.name, len(items), 'NAIP items for', a.year, file=sys.stderr)
    chunks = [(round(float(lo), 4), round(float(la), 4), round(float(min(lo + CHUNK, bbox[2])), 4), round(float(min(la + CHUNK, bbox[3])), 4))
              for la in np.arange(bbox[1], bbox[3] - 1e-9, CHUNK) for lo in np.arange(bbox[0], bbox[2] - 1e-9, CHUNK)]
    t0 = time.time(); todo = [c for c in chunks if c not in done]
    for i, bb in enumerate(todo):
        for attempt in range(3):
            try: det = score_chunk(bb, a.year, items, gbm, nets, a.threshold); break
            except Exception as e:
                print('chunk', bb, 'failed:', e, file=sys.stderr); time.sleep(20 * (attempt + 1)); det = None
        if det is None: continue  # left for a re-run
        done[bb] = det
        with open(ck, 'a') as f: f.write(json.dumps({'bb': bb, 'det': det}) + '\n')
        if i % 20 == 0:
            el = time.time() - t0
            print(f'{len(done)}/{len(chunks)} chunks, {sum(map(len, done.values()))} raw detections, '
                  f'{el / (i + 1):.1f} s/chunk, ~{el / (i + 1) * (len(todo) - i - 1) / 60:.0f} min left', file=sys.stderr, flush=True)
    det = merge([d for v in done.values() for d in v])
    print(a.name, len(done), 'of', len(chunks), 'chunks,', len(det), 'pools after merging', file=sys.stderr)
    if len(done) < len(chunks): sys.exit('some chunks failed; re-run to finish them before writing')
    if a.write:
        n, dup, cty = write_tiles(a.write, bbox, det)
        print(f'wrote {n} air points; {dup} skipped as duplicates of county/OSM points; {cty} skipped in county-record tiles', file=sys.stderr)


if __name__ == '__main__':
    main()
