"""Pool-flagged parcel polygons inside a bbox, from the same public ArcGIS layers the repo's builders use."""
import json, sys, time, urllib.parse, urllib.request, pickle, os
from shapely.geometry import Polygon
from shapely.ops import unary_union
SRC = {
 'sandiego': dict(url='https://geo.sandag.org/server/rest/services/Hosted/Parcels/FeatureServer/0', where="pool='Y'"),
 'pasadena': dict(url='https://services1.arcgis.com/SPm6TOk52QjLKxth/arcgis/rest/services/Land_Base/FeatureServer/95', where="Pool='Y'"),
 'contracosta': dict(url='https://services6.arcgis.com/CmHj285GYxHhHnTo/arcgis/rest/services/Assessor_Parcels/FeatureServer/0', where="POOL='Y'"),
 'sanjoaquin': dict(url='https://services2.arcgis.com/GQhSReJEO6f7tsvy/arcgis/rest/services/Parcels/FeatureServer/0', where="POOL_SPA IS NOT NULL AND POOL_SPA NOT IN ('N','')"),
 'solano': dict(url='https://services2.arcgis.com/SCn6czzcqKAFwdGU/arcgis/rest/services/Parcels_Public_Aumentum/FeatureServer/0', where="pool='YS'"),
 'maricopa': dict(url='https://services.arcgis.com/ykpntM6e3tHvzKRJ/arcgis/rest/services/Parcel_Data_View/FeatureServer/0', where="Pool='YES'"),
 'collin': dict(url='https://services2.arcgis.com/uXyoacYrZTPTKD3R/arcgis/rest/services/CCAD_Parcel_Feature_Set/FeatureServer/4', where="imprvPoolFlag='T'"),
 'riverside': dict(url='https://gis.countyofriverside.us/arcgis_mapping/rest/services/OpenData/Assessor/MapServer/50', key='APN',
                   table='https://gis.countyofriverside.us/arcgis_mapping/rest/services/OpenData/Assessor/MapServer/80', tkey='PIN', twhere="HAS_POOL='1'"),
}
UA = {'User-Agent': 'ProjectHydroShield/1.0 (givekidsavoice.org)'}
def q(url, p):
    for i in range(5):
        try:
            r = urllib.request.Request(url + '/query', urllib.parse.urlencode(dict(p, f='json')).encode(), UA)
            j = json.load(urllib.request.urlopen(r, timeout=180))
            if 'error' in j: raise RuntimeError(j['error'])
            return j
        except Exception as e:
            if i == 4: raise
            time.sleep(4 * (i + 1))
def polys(f):
    rings = [r for r in (f.get('geometry') or {}).get('rings') or [] if len(r) >= 4]
    ps = [Polygon(r) for r in rings]; ps = [p if p.is_valid else p.buffer(0) for p in ps]
    return unary_union(ps) if ps else None
def env(bb, where, url, fields='*'):
    out, off = [], 0
    while True:
        j = q(url, {'where': where, 'geometry': '%f,%f,%f,%f' % bb, 'geometryType': 'esriGeometryEnvelope', 'inSR': 4326,
                    'spatialRel': 'esriSpatialRelIntersects', 'outFields': fields or '', 'returnIdsOnly': 'false', 'returnGeometry': 'true', 'outSR': 4326,
                    'resultOffset': off, 'resultRecordCount': 1000})
        fs = j.get('features', []); out += fs; off += len(fs)
        if not fs or not j.get('exceededTransferLimit'): break
        time.sleep(0.3)
    return out
def get(src, bb):
    cache = f'parcels/{src}_{"_".join("%.4f" % v for v in bb)}.pkl'
    if os.path.exists(cache): return pickle.load(open(cache, 'rb'))
    c = SRC[src]
    if 'table' in c:
        fs = env(bb, '1=1', c['url'], c['key']); by = {}
        for f in fs:
            k = (f['attributes'].get(c['key']) or '').strip()
            if k: by.setdefault(k, []).append(f)
        keys = sorted(by); pool = set()
        for i in range(0, len(keys), 200):
            w = "%s AND %s IN (%s)" % (c['twhere'], c['tkey'], ','.join("'%s'" % k for k in keys[i:i + 200]))
            j = q(c['table'], {'where': w, 'outFields': c['tkey'], 'returnGeometry': 'false'})
            pool |= {(f['attributes'].get(c['tkey']) or '').strip() for f in j.get('features', [])}
        res = [polys(f) for k in pool for f in by.get(k, [])]
    else:
        res = [polys(f) for f in env(bb, c['where'], c['url'], '')]
    res = [p for p in res if p is not None and not p.is_empty]
    os.makedirs('parcels', exist_ok=True); pickle.dump(res, open(cache, 'wb'))
    return res
if __name__ == '__main__':
    bb = tuple(map(float, sys.argv[2:6])); r = get(sys.argv[1], bb); print(sys.argv[1], len(r), 'pool parcels')
