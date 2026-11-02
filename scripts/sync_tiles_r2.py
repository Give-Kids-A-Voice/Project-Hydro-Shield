"""Upload one state's packed water tiles to the nationwide tile bucket (Cloudflare R2, S3 API) and rebuild the
public tiles they touch.

  python3 scripts/sync_tiles_r2.py <STATE> <packed-dir> <state.poly>

Env: R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET   (GitHub secrets; never in the repo)

Bucket layout
  src/<ST>/<key>.json         this state's own tile (gzip), as built
  manifests/<ST>.json         {"built": date, "tiles": {key: md5}, "cells": [1-degree cells the state polygon touches]}
  v2/<key>.json               PUBLIC tile = all states' src tiles for that key merged (features deduped by id + shape)
  v2/coverage.json            PUBLIC {"cells": [1-degree cells "lat_lon" where every state touching the cell is built]}
A tile on a state line (e.g. GA/FL) is built by both states; each keeps its own src copy and the public tile is
their union, so rebuilding one state never deletes its neighbour's features.
Safety: nothing is written unless the build looks sane (tile count >= 80% of last month's), so a failed or
truncated Geofabrik download keeps last month's tiles. Only changed tiles are uploaded (md5 of gzip bytes).
"""
import gzip, hashlib, json, math, os, sys, datetime
import boto3
from botocore.config import Config

ST, packed, poly = sys.argv[1].upper(), sys.argv[2], sys.argv[3]
B = os.environ['R2_BUCKET']
s3 = boto3.client('s3', endpoint_url=f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
                  aws_access_key_id=os.environ['R2_ACCESS_KEY_ID'], aws_secret_access_key=os.environ['R2_SECRET_ACCESS_KEY'],
                  region_name='auto', config=Config(retries={'max_attempts': 8, 'mode': 'adaptive'}, max_pool_connections=32))
PUB = dict(ContentType='application/json', ContentEncoding='gzip',
           CacheControl='public, max-age=86400, stale-while-revalidate=604800')


def get(key, default=None):
    try: return s3.get_object(Bucket=B, Key=key)['Body'].read()
    except s3.exceptions.NoSuchKey: return default


def get_json(key, default):
    b = get(key)
    if b is None: return default
    try: return json.loads(gzip.decompress(b))
    except OSError: return json.loads(b)


def poly_cells(path):
    """1-degree cells touched by a Geofabrik .poly (outer rings only), padded one cell for the extract's buffer."""
    from shapely.geometry import Polygon, box
    from shapely.ops import unary_union
    rings, cur, hole = [], None, False
    for line in list(open(path))[1:]:            # line 1 is the file's name
        s = line.split()
        if not s: continue
        if s[0] == 'END':
            if cur is not None and not hole: rings.append(cur)
            cur = None; continue
        if cur is None: cur, hole = [], s[0].startswith('!')   # section header; '!' marks a hole
        else: cur.append((float(s[0]), float(s[1])))
    shp = unary_union([Polygon(r) for r in rings if len(r) > 2])
    x0, y0, x1, y1 = shp.bounds; out = []
    for y in range(math.floor(y0), math.floor(y1) + 1):
        for x in range(math.floor(x0), math.floor(x1) + 1):
            if shp.intersects(box(x, y, x + 1, y + 1)): out.append(f'{y}_{x}')
    return out


def md5(b): return hashlib.md5(b).hexdigest()


new = {fn[:-5]: open(os.path.join(packed, fn), 'rb').read() for fn in os.listdir(packed) if fn.endswith('.json')}
old = get_json(f'manifests/{ST}.json', {'tiles': {}})
if old['tiles'] and len(new) < 0.8 * len(old['tiles']):
    sys.exit(f'{ST}: only {len(new)} tiles vs {len(old["tiles"])} last time; keeping the old tiles')

others = {}   # key -> states (other than ST) that have a src tile there
for o in s3.list_objects_v2(Bucket=B, Prefix='manifests/').get('Contents', []):
    st = o['Key'].split('/')[1][:-5]
    if st == ST: continue
    m = get_json(o['Key'], {'tiles': {}})
    for k in m['tiles']: others.setdefault(k, []).append(st)

hashes = {k: md5(b) for k, b in new.items()}
changed = [k for k in new if old['tiles'].get(k) != hashes[k]]
gone = [k for k in old['tiles'] if k not in new]


def publish(k):
    feats, seen = [], set()
    parts = [new[k]] if k in new else []
    for st in others.get(k, []):
        b = get(f'src/{st}/{k}.json')
        if b: parts.append(b)
    for b in parts:
        for f in json.loads(gzip.decompress(b)):
            sig = (f['i'], md5(json.dumps(f['d']).encode()))
            if sig not in seen: seen.add(sig); feats.append(f)
    if feats:
        s3.put_object(Bucket=B, Key=f'v2/{k}.json', Body=gzip.compress(json.dumps(feats, separators=(',', ':')).encode(), 9, mtime=0), **PUB)
    else:
        s3.delete_object(Bucket=B, Key=f'v2/{k}.json')


from concurrent.futures import ThreadPoolExecutor
def up(k):
    s3.put_object(Bucket=B, Key=f'src/{ST}/{k}.json', Body=new[k], ContentType='application/json', ContentEncoding='gzip')
    if k in others: publish(k)          # shared border tile: merge with the neighbour's copy
    else: s3.put_object(Bucket=B, Key=f'v2/{k}.json', Body=new[k], **PUB)
def rm(k):
    s3.delete_object(Bucket=B, Key=f'src/{ST}/{k}.json'); publish(k)
with ThreadPoolExecutor(24) as ex:
    list(ex.map(up, changed)); list(ex.map(rm, gone))

cells = poly_cells(poly)
s3.put_object(Bucket=B, Key=f'manifests/{ST}.json', ContentType='application/json',
              Body=json.dumps({'built': datetime.date.today().isoformat(), 'tiles': hashes, 'cells': cells}).encode())

# coverage: a 1-degree cell is covered when every state touching it has been built
touch, built = {}, set()
for o in s3.list_objects_v2(Bucket=B, Prefix='manifests/').get('Contents', []):
    m = get_json(o['Key'], {}); st = o['Key'].split('/')[1][:-5]; built.add(st)
    for c in m.get('cells', []): touch.setdefault(c, set()).add(st)
# cell_states (optional, in scripts/us_states.json): every state touching each cell, precomputed from all .poly files,
# so a cell is not marked covered while a neighbouring state has never been built. Without it, only built states count.
_cfg = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'us_states.json')
need = json.load(open(_cfg)).get('cell_states', {}) if os.path.exists(_cfg) else {}
cov = sorted(c for c, sts in touch.items() if set(need.get(c, sts)) <= built)
s3.put_object(Bucket=B, Key='v2/coverage.json', Body=gzip.compress(json.dumps({'cells': cov}).encode(), 9, mtime=0),
              ContentType='application/json', ContentEncoding='gzip', CacheControl='public, max-age=3600')
print(f'{ST}: {len(new)} tiles, {len(changed)} uploaded, {len(gone)} removed, {sum(1 for k in new if k in others)} shared with neighbours; '
      f'coverage {len(cov)} one-degree cells')
