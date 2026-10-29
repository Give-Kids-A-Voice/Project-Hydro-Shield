/* Hydro-Shield hazard geometry. Pure functions, no network. Works in the browser (window.HydroShield) and Node (module.exports). */
(function (root) {
  // OpenStreetMap tags that describe water a child can reach on foot.
  function overpassQuery(lat, lon, rad) {
    var a = '(around:' + Math.round(rad) + ',' + lat.toFixed(6) + ',' + lon.toFixed(6) + ')';
    return '[out:json][timeout:25];(' +
      'way["natural"="water"]' + a + ';relation["natural"="water"]' + a + ';' +
      'way["landuse"~"^(basin|reservoir)$"]' + a + ';relation["landuse"~"^(basin|reservoir)$"]' + a + ';' +
      'way["leisure"="swimming_pool"]' + a + ';way["leisure"="water_park"]' + a + ';' +
      'way["waterway"~"^(canal|ditch|drain|stream|river)$"]' + a + ';' +
      'way["waterway"="riverbank"]' + a + ';' +
      'node["amenity"="fountain"]' + a + ';way["amenity"="fountain"]' + a + ';' +
      ');out geom;';
  }

  var KIND = {
    retention: ['Retention / stormwater pond', 3], pond: ['Pond', 3], lake: ['Lake', 3], reservoir: ['Reservoir', 3],
    canal: ['Canal', 3], ditch: ['Drainage ditch', 2], drain: ['Drainage channel', 2], stream: ['Stream / creek', 2], river: ['River', 3],
    pool: ['Swimming pool', 3], waterpark: ['Water park', 2], fountain: ['Fountain', 1], water: ['Open water', 3], wetland: ['Wetland', 2]
  };
  function classify(t) {
    t = t || {};
    if (t.leisure === 'swimming_pool') return 'pool';
    if (t.leisure === 'water_park') return 'waterpark';
    if (t.amenity === 'fountain') return 'fountain';
    if (t.waterway && KIND[t.waterway]) return t.waterway;
    if (t.waterway === 'riverbank') return 'river';
    if (t.landuse === 'basin' || t.basin || t.water === 'basin' || t.water === 'stormwater' || t.water === 'retention' || t.water === 'detention') return 'retention';
    if (t.landuse === 'reservoir' || t.water === 'reservoir') return 'reservoir';
    if (t.water && KIND[t.water]) return t.water;
    if (t.water === 'lagoon' || t.water === 'oxbow') return 'pond';
    if (t.water === 'canal') return 'canal';
    return 'water';
  }

  // Local flat projection in meters around the home point (accurate to well under 1% inside a few km).
  function projector(lat0, lon0) {
    var ky = 110574, kx = 111320 * Math.cos(lat0 * Math.PI / 180);
    return { to: function (lat, lon) { return [(lon - lon0) * kx, (lat - lat0) * ky]; },
             from: function (x, y) { return [lat0 + y / ky, lon0 + x / kx]; } };
  }
  function segDist(px, py, ax, ay, bx, by) {
    var dx = bx - ax, dy = by - ay, l = dx * dx + dy * dy, t = l ? ((px - ax) * dx + (py - ay) * dy) / l : 0;
    t = Math.max(0, Math.min(1, t)); var x = ax + t * dx, y = ay + t * dy;
    return [Math.hypot(px - x, py - y), x, y];
  }
  function inside(px, py, ring) {
    var c = false;
    for (var i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      var a = ring[i], b = ring[j];
      if ((a[1] > py) !== (b[1] > py) && px < (b[0] - a[0]) * (py - a[1]) / (b[1] - a[1]) + a[0]) c = !c;
    }
    return c;
  }

  // Returns hazards sorted by distance from home to the nearest water edge (meters).
  function hazards(osm, lat0, lon0, rad) {
    var P = projector(lat0, lon0), out = [], seen = {};
    (osm.elements || []).forEach(function (el) {
      var t = el.tags || {}, cls = classify(t), lines = [];
      if (el.type === 'node') lines = [[[el.lat, el.lon]]];
      else if (el.type === 'way' && el.geometry) lines = [el.geometry.map(function (g) { return [g.lat, g.lon]; })];
      else if (el.type === 'relation' && el.members) lines = el.members.filter(function (m) { return m.geometry && m.role !== 'inner'; }).map(function (m) { return m.geometry.map(function (g) { return [g.lat, g.lon]; }); });
      lines = lines.filter(function (l) { return l.length; });
      if (!lines.length) return;
      var isLine = !!t.waterway && t.waterway !== 'riverbank';
      var best = [Infinity, 0, 0];
      lines.forEach(function (l) {
        var pts = l.map(function (p) { return P.to(p[0], p[1]); });
        if (pts.length === 1) { var d0 = Math.hypot(pts[0][0], pts[0][1]); if (d0 < best[0]) best = [d0, pts[0][0], pts[0][1]]; return; }
        for (var i = 1; i < pts.length; i++) { var d = segDist(0, 0, pts[i - 1][0], pts[i - 1][1], pts[i][0], pts[i][1]); if (d[0] < best[0]) best = d; }
        if (!isLine && pts.length > 2 && inside(0, 0, pts)) best = [0, 0, 0];
      });
      if (best[0] > rad) return;
      var id = el.type + '/' + el.id; if (seen[id]) return; seen[id] = 1;
      var k = KIND[cls] || KIND.water;
      var name = t.name || (cls === 'pool' ? (t.access === 'private' ? 'Private pool' : 'Pool') : k[0]);
      var coords = lines.length === 1 ? lines[0] : lines;
      if (el.type === 'node') { var o = P.to(el.lat, el.lon), r = 0.00004; coords = [[el.lat - r, el.lon - r], [el.lat - r, el.lon + r], [el.lat + r, el.lon + r], [el.lat + r, el.lon - r]]; }
      out.push({ id: id, name: name, cls: cls, kind: k[0], sev: best[0] <= 150 ? 3 : (k[1] >= 3 && best[0] <= 300 ? 2 : Math.min(k[1], 2)), dist: best[0],
        nearest: P.from(best[1], best[2]), coords: coords, line: isLine });
    });
    return out.sort(function (a, b) { return a.dist - b.dist; });
  }

  var api = { overpassQuery: overpassQuery, hazards: hazards, classify: classify };
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.HydroShield = api;
})(this);
