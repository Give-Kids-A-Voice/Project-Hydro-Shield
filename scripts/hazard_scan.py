"""Hydro-Shield water hazard scan (Module B) using OpenStreetMap, no API key needed.

Finds ponds, retention basins, canals, ditches, pools and fountains around a home and
ranks them by distance to the nearest water edge. Output is GeoJSON the hub and the web
map can both read.

    python3 scripts/hazard_scan.py "123 Main St, Land O Lakes, FL" --radius 500 > hazards.geojson
    python3 scripts/hazard_scan.py --lat 28.2189 --lon -82.4573

Data: (c) OpenStreetMap contributors (ODbL), via Overpass and Nominatim. Be polite:
cache results; the map around a home rarely changes.
"""
import argparse, json, math, sys, urllib.parse, urllib.request

UA = "ProjectHydroShield/0.1 (+https://github.com/Give-Kids-A-Voice/Project-Hydro-Shield)"
OVERPASS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]
KIND = {"retention": ("Retention / stormwater pond", 3), "pond": ("Pond", 3), "lake": ("Lake", 3), "reservoir": ("Reservoir", 3),
        "canal": ("Canal", 3), "ditch": ("Drainage ditch", 2), "drain": ("Drainage channel", 2), "stream": ("Stream / creek", 2),
        "river": ("River", 3), "pool": ("Swimming pool", 3), "waterpark": ("Water park", 2), "fountain": ("Fountain", 1),
        "water": ("Open water", 3), "wetland": ("Wetland", 2)}


def http(url, data=None):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.load(r)


def geocode(address):
    q = urllib.parse.urlencode({"format": "json", "limit": 1, "countrycodes": "us", "q": address})
    res = http("https://nominatim.openstreetmap.org/search?" + q)
    if not res:
        raise SystemExit("Address not found. Add the city and state.")
    return float(res[0]["lat"]), float(res[0]["lon"])


def query(lat, lon, rad):
    a = f"(around:{int(rad)},{lat:.6f},{lon:.6f})"
    parts = ['way["natural"="water"]', 'relation["natural"="water"]', 'way["landuse"~"^(basin|reservoir)$"]',
             'relation["landuse"~"^(basin|reservoir)$"]', 'way["leisure"="swimming_pool"]', 'way["leisure"="water_park"]',
             'way["waterway"~"^(canal|ditch|drain|stream|river)$"]', 'way["waterway"="riverbank"]',
             'node["amenity"="fountain"]', 'way["amenity"="fountain"]']
    return "[out:json][timeout:25];(" + "".join(p + a + ";" for p in parts) + ");out geom;"


def classify(t):
    if t.get("leisure") == "swimming_pool": return "pool"
    if t.get("leisure") == "water_park": return "waterpark"
    if t.get("amenity") == "fountain": return "fountain"
    w = t.get("waterway")
    if w in KIND: return w
    if w == "riverbank": return "river"
    if t.get("landuse") == "basin" or "basin" in t or t.get("water") in ("basin", "stormwater", "retention", "detention"): return "retention"
    if t.get("landuse") == "reservoir" or t.get("water") == "reservoir": return "reservoir"
    if t.get("water") in KIND: return t["water"]
    if t.get("water") in ("lagoon", "oxbow"): return "pond"
    return "water"


def hazards(osm, lat0, lon0, rad):
    ky, kx = 110574.0, 111320.0 * math.cos(math.radians(lat0))
    to = lambda la, lo: ((lo - lon0) * kx, (la - lat0) * ky)

    def seg(ax, ay, bx, by):
        dx, dy = bx - ax, by - ay
        l = dx * dx + dy * dy
        t = max(0.0, min(1.0, ((-ax) * dx + (-ay) * dy) / l)) if l else 0.0
        x, y = ax + t * dx, ay + t * dy
        return math.hypot(x, y), x, y

    def inside(ring):
        c, j = False, len(ring) - 1
        for i in range(len(ring)):
            (xi, yi), (xj, yj) = ring[i], ring[j]
            if (yi > 0) != (yj > 0) and 0 < (xj - xi) * (0 - yi) / (yj - yi) + xi:
                c = not c
            j = i
        return c

    out, seen = [], set()
    for el in osm.get("elements", []):
        t = el.get("tags", {})
        cls = classify(t)
        if el["type"] == "node":
            lines = [[(el["lat"], el["lon"])]]
        elif el["type"] == "way" and el.get("geometry"):
            lines = [[(g["lat"], g["lon"]) for g in el["geometry"]]]
        elif el["type"] == "relation":
            lines = [[(g["lat"], g["lon"]) for g in m["geometry"]] for m in el.get("members", []) if m.get("geometry") and m.get("role") != "inner"]
        else:
            continue
        is_line = bool(t.get("waterway")) and t.get("waterway") != "riverbank"
        best = (math.inf, 0.0, 0.0)
        for line in lines:
            pts = [to(*p) for p in line]
            if len(pts) == 1:
                best = min(best, (math.hypot(*pts[0]), *pts[0]))
                continue
            for i in range(1, len(pts)):
                best = min(best, seg(*pts[i - 1], *pts[i]))
            if not is_line and len(pts) > 2 and inside(pts):
                best = (0.0, 0.0, 0.0)
        key = f'{el["type"]}/{el["id"]}'
        if best[0] > rad or key in seen:
            continue
        seen.add(key)
        label, risk = KIND.get(cls, KIND["water"])
        dist = best[0]
        sev = 3 if dist <= 150 else (2 if risk >= 3 and dist <= 300 else min(risk, 2))
        name = t.get("name") or ("Private pool" if cls == "pool" and t.get("access") == "private" else label)
        geom = {"type": "Point", "coordinates": [lines[0][0][1], lines[0][0][0]]} if el["type"] == "node" else (
            {"type": "LineString", "coordinates": [[lo, la] for la, lo in lines[0]]} if is_line else
            {"type": "MultiPolygon", "coordinates": [[[[lo, la] for la, lo in l]] for l in lines]})
        out.append({"type": "Feature", "id": key, "geometry": geom,
                    "properties": {"name": name, "class": cls, "kind": label, "severity": sev, "distance_m": round(dist, 1),
                                   "nearest_edge": [round(lat0 + best[2] / ky, 7), round(lon0 + best[1] / kx, 7)]}})
    out.sort(key=lambda f: f["properties"]["distance_m"])
    return {"type": "FeatureCollection", "home": [lat0, lon0], "radius_m": rad, "features": out}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("address", nargs="?")
    ap.add_argument("--lat", type=float); ap.add_argument("--lon", type=float)
    ap.add_argument("--radius", type=float, default=500)
    a = ap.parse_args()
    if a.lat is not None and a.lon is not None:
        lat, lon = a.lat, a.lon
    elif a.address:
        lat, lon = geocode(a.address)
    else:
        ap.error("give an address or --lat/--lon")
    body = urllib.parse.urlencode({"data": query(lat, lon, a.radius)}).encode()
    err = None
    for url in OVERPASS:
        try:
            fc = hazards(http(url, body), lat, lon, a.radius)
            break
        except Exception as e:  # try the next mirror
            err = e
    else:
        raise SystemExit(f"Could not reach OpenStreetMap data servers: {err}")
    for f in fc["features"]:
        p = f["properties"]
        print(f'{p["distance_m"]:7.0f} m  sev{p["severity"]}  {p["kind"]:<28} {p["name"]}', file=sys.stderr)
    json.dump(fc, sys.stdout, indent=1)


if __name__ == "__main__":
    main()
