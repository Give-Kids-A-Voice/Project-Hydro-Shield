"""Place pools for counties whose Property Appraiser publishes a pool list without locations, using the
Florida Department of Revenue statewide parcel centroids (FDOR Cadastral Centroids, via Florida GIO).

  python3 scripts/build_statewide_join.py sarasota RAW_DIR docs/data/pools   # RAW_DIR/SFYI.txt from SCPA_Detailed_Data.zip
  python3 scripts/build_statewide_join.py duval    RAW_DIR docs/data/pools   # RAW_DIR/*.txt pipe-delimited roll (record 00011 = extra features)
  python3 scripts/build_statewide_join.py citrus   RAW_DIR docs/data/pools   # RAW_DIR/VD_PARCELDATA.CSV (POOLFLG = Y)
  python3 scripts/build_statewide_join.py <volusia|seminole|osceola|lake|marion|charlotte|stjohns|alachua|martin|leon> RAW_DIR docs/data/pools
      # RAW_DIR filled by: scripts/fetch_county_raw.sh <county> RAW_DIR
Writes [lat, lon] (pool) or [lat, lon, "spa"] into the shared tiles, deduped. No owner data.
"""
import csv, glob, json, math, os, sys, time, urllib.parse, urllib.request, collections
csv.field_size_limit(10**8)
URL = 'https://services9.arcgis.com/Gh9awoU677aKree0/arcgis/rest/services/Florida_Statewide_Parcel_Centroid_Version/FeatureServer/0/query'
county, raw, out = sys.argv[1], sys.argv[2], sys.argv[3]
kind = {}
key_field = 'PARCEL_ID'

if county == 'sarasota':
    co = 68
    for r in csv.DictReader(open(os.path.join(raw, 'SFYI.txt'), encoding='latin-1')):
        t = r['outbuildingtype'].strip(); pid = r['parcelid'].strip()
        if t in ('POOL', 'POOLCO'): kind[pid] = 'pool'
        elif t == 'SPA' and kind.get(pid) != 'pool': kind[pid] = 'spa'
elif county == 'duval':
    co = int(os.environ.get('DUVAL_CO_NO', '26'))
    for fp in glob.glob(os.path.join(raw, '*.txt')) + glob.glob(os.path.join(raw, '*.TXT')):
        for line in open(fp, encoding='latin-1'):
            if not line.startswith('00011|'): continue
            p = line.split('|')
            if len(p) < 5: continue
            code, desc = p[3].strip().upper(), p[4].upper()
            if code.startswith('POL') or 'POOL' in desc: kind[p[1].strip()] = 'pool'
elif county == 'citrus':
    # VD_PARCELDATA.CSV from the Citrus County Property Appraiser vendor dump (Google Drive folder linked on citruspa.org Downloads).
    co, key_field = 19, 'ALT_KEY'
    for r in csv.DictReader(open(os.path.join(raw, 'VD_PARCELDATA.CSV'), encoding='latin-1')):
        if (r.get('POOLFLG') or '').strip().upper() == 'Y': kind[r['ALTKEY'].strip()] = 'pool'
else:
    # Further counties (raw files from scripts/fetch_county_raw.sh). All join on FDOR PARCEL_ID.
    def mark(pid, k):
        pid = (pid or '').rstrip()
        if not pid.strip(): return
        if k == 'pool': kind[pid] = 'pool'
        elif kind.get(pid) != 'pool': kind[pid] = 'spa'
    if county == 'volusia':
        co = 74   # VOLUSIA_POOLS_EXTRACT.csv: every row is a pool (RSP residential, POL commercial, SPL custom, PLK children's)
        for r in csv.DictReader(open(os.path.join(raw, 'VOLUSIA_POOLS_EXTRACT.csv'), encoding='latin-1')): mark(r['parcelid'], 'pool')
    elif county == 'seminole':
        co = 69   # ExtraFeature.csv Description: "POOL 1/2/3", "POOL COMMERCIAL - SF"; "SPA 1/2/3"
        for r in csv.DictReader(open(os.path.join(raw, 'ExtraFeature.csv'), encoding='utf-8-sig')):
            d = r['Description'].strip().upper()
            if d.startswith('POOL ') and d != 'POOL HSES': mark(r['Parcel'], 'pool')
            elif d.startswith('SPA '): mark(r['Parcel'], 'spa')
    elif county == 'osceola':
        co = 59   # vw_mdxfob.csv (pipe): pool 57xx (excluding wading/deck codes), commercial 575x; spa 55xx
        P = {'5701', '5702', '5705', '5706', '5707', '5711', '5751', '5753', '5754', '5755', '5757'}
        S = {'5501', '5506', '5507', '5551', '5553', '5555'}
        for r in csv.DictReader(open(os.path.join(raw, 'vw_mdxfob.csv'), encoding='latin-1'), delimiter='|'):
            c = r['cd'].strip()
            if c in P: mark(r['strap'], 'pool')
            elif c in S: mark(r['strap'], 'spa')
    elif county == 'lake':
        co = 45   # Xfob file: POL*/CPOL* residential, CCPL*/CPL* commercial, PLV* Villages pools; HTB*/CHTB* spas
        import re
        for r in csv.DictReader(open(os.path.join(raw, 'xfob.txt'), encoding='latin-1')):
            c = r['OXF_CODE'].strip().upper()
            if re.fullmatch(r'C?POL\d|CCPL\d|CPL\d|PLV\d', c): mark(r['REM_ACCT_NUM'], 'pool')
            elif re.fullmatch(r'C?HTB\d', c): mark(r['REM_ACCT_NUM'], 'spa')
    elif county == 'marion':
        co = 52   # TRIM data: POOL = Y
        fp = glob.glob(os.path.join(raw, 'TRIM*MCPA*Data.csv'))[0]
        for r in csv.DictReader(open(fp, encoding='latin-1')):
            if (r.get('POOL') or '').strip().upper() == 'Y': mark(r['PARCEL'], 'pool')
    elif county == 'charlotte':
        co = 18   # cd.txt (pipe): haspool = True
        for r in csv.DictReader(open(os.path.join(raw, 'cd.txt'), encoding='latin-1'), delimiter='|', quoting=csv.QUOTE_NONE):
            if (r.get('haspool') or '').strip().lower() == 'true': mark(r['account'], 'pool')
    elif county == 'stjohns':
        co = 65   # XFOBView: POOLAR/GR/LR/XR residential, POOLC community; SPAM spa (POOLHM pool house excluded)
        for r in csv.DictReader(open(os.path.join(raw, 'xfob.csv'), encoding='latin-1')):
            c = r['cd'].strip().upper()
            if c in ('POOLAR', 'POOLGR', 'POOLLR', 'POOLXR', 'POOLC'): mark(r['strap'], 'pool')
            elif c == 'SPAM': mark(r['strap'], 'spa')
    elif county == 'alachua':
        co = 11   # ImprvDetails.txt (tab): 1760-1764 / 4760-4764 pool, 1300 / 4300 hot tub
        P = {'1760', '1761', '1762', '1763', '1764', '4760', '4761', '4762', '4763', '4764'}
        for r in csv.DictReader(open(os.path.join(raw, 'ImprvDetails.txt'), encoding='latin-1'), delimiter='\t', quoting=csv.QUOTE_NONE):
            c = (r.get('Imprv_Detail_Type') or '').strip()
            if c in P: mark(r['Parcel'], 'pool')
            elif c in ('1300', '4300'): mark(r['Parcel'], 'spa')
    elif county == 'martin':
        co = 53   # real_sfyi.csv SfyiCode POOL / JACUZZI, keyed by PropertyID -> real_master.csv ParcelID
        pid = {r['PropertyID']: r['ParcelID'] for r in csv.DictReader(open(os.path.join(raw, 'real_master.csv'), encoding='latin-1'), delimiter='|', quoting=csv.QUOTE_NONE)}
        for r in csv.DictReader(open(os.path.join(raw, 'real_sfyi.csv'), encoding='latin-1'), delimiter='|', quoting=csv.QUOTE_NONE):
            c = r['SfyiCode'].strip().upper()
            if c == 'POOL': mark(pid.get(r['PropertyID']), 'pool')
            elif c == 'JACUZZI': mark(pid.get(r['PropertyID']), 'spa')
    elif county == 'leon':
        co = 47   # OTHERFEAT.TXT (~): code OOL = pool (description blank or POOL), SPA = spa. Parcel IDs keep inner spaces.
        for line in open(os.path.join(raw, 'OTHERFEAT.TXT'), encoding='latin-1'):
            p = line.split('~')
            if len(p) < 4: continue
            c, d = p[2].strip().upper(), p[3].strip().upper()
            if c == 'OOL' and (not d or 'POOL' in d): mark(p[0], 'pool')
            elif c == 'SPA': mark(p[0], 'spa')
    else:
        sys.exit('unknown county')
print(county, len(kind), 'parcels with a pool or spa', file=sys.stderr)

def q(params):
    for attempt in range(6):
        try:
            data = urllib.parse.urlencode(dict(params, f='json')).encode()
            with urllib.request.urlopen(urllib.request.Request(URL, data=data, headers={'User-Agent': 'ProjectHydroShield/1.0'}), timeout=180) as r: j = json.load(r)
            if 'error' in j: raise RuntimeError(j['error'])
            return j
        except Exception:
            if attempt == 5: raise
            time.sleep(4 * (attempt + 1))

def norm(s): return ''.join(ch for ch in s if ch.isalnum())
want = {norm(k): v for k, v in kind.items()}
# Download every parcel point in the county (paged), then match locally. Much faster than ID lookups.
from concurrent.futures import ThreadPoolExecutor
# Page by OBJECTID ranges (offset paging fails on some large counties)
oids = sorted(q({'where': f'CO_NO={co}', 'returnIdsOnly': 'true'}).get('objectIds') or [])
count = len(oids)
def page(i):
    lo, hi = oids[i], oids[min(i + 1999, count - 1)]
    return q({'where': f'CO_NO={co} AND OBJECTID>={lo} AND OBJECTID<={hi}', 'outFields': key_field, 'outSR': 4326}).get('features', [])
tiles = collections.defaultdict(list); n = collections.Counter(); seen = set()
# Original counties keep one point per FDOR centroid. Counties added later get ONE point per parcel: condo and
# common-area parcels can have hundreds of FDOR centroids (one per unit), so we place the parcel at their mean.
ONE_PER_PARCEL = county not in ('sarasota', 'duval', 'citrus')
byp = collections.defaultdict(list)
def place(lat, lon, k):
    lat, lon = round(lat, 5), round(lon, 5)
    if (lat, lon) in seen: return
    seen.add((lat, lon)); n[k] += 1
    tiles[f'{math.floor(lat*20)}_{math.floor(lon*20)}'].append([lat, lon] + ([] if k == 'pool' else ['spa']))
with ThreadPoolExecutor(4) as ex:
    for feats in ex.map(page, range(0, count, 2000)):
        for f in feats:
            g = f.get('geometry') or {}; pid = norm(str(f['attributes'].get(key_field) or ''))
            if 'x' not in g or pid not in want: continue
            if ONE_PER_PARCEL: byp[pid].append((g['y'], g['x']))
            else: place(g['y'], g['x'], want[pid])
for pid, pts in sorted(byp.items()):
    place(sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts), want[pid])
if ONE_PER_PARCEL: print(county, len(byp), 'of', len(want), 'pool/spa parcels matched an FDOR location', file=sys.stderr)
print(county, count, 'parcels scanned', file=sys.stderr)
os.makedirs(out, exist_ok=True)
for t, pts in tiles.items():
    fp = os.path.join(out, t + '.json')
    old = json.load(open(fp)) if os.path.exists(fp) else []
    have = {(a[0], a[1]) for a in old}
    json.dump(old + [x for x in pts if (x[0], x[1]) not in have and not have.add((x[0], x[1]))], open(fp, 'w'), separators=(',', ':'))
print(county, dict(n), 'placed in', len(tiles), 'tiles', file=sys.stderr)
