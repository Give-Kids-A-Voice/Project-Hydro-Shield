"""Pool candidate extraction from NAIP (R,G,B,NIR uint8 at ~0.6 m) and per-candidate features."""
import numpy as np
from scipy import ndimage as ndi
PX_M2 = 0.36
FEATS = ['GB', 'RB', 'NB', 'NG', 'GRrel', 'BRc', 'GRc', 'NGc', 'sceneBR', 'sceneBright', 'relBright', 'area_m2', 'R', 'G', 'B', 'N', 'sdB', 'maxB', 'bd', 'gd', 'nwi', 'bright', 'core_frac', 'extent', 'solidity',
         'elong', 'compact', 'ringNDVI', 'ringBright', 'ringBR', 'ringSdBright', 'edgeContrast']
def scene(a):
    """Per-scene colour cast: median B-R, G-R, N-G and brightness over non-vegetated pixels (haze/colour balance differ by
    state, flight date and even within one NAIP year)."""
    R, G, B, N = [x.astype(np.float32) for x in a]
    m = ((N - R) / (N + R + 1) < 0.15) & (R + G + B > 30)
    if m.sum() < 1000: m = np.ones_like(m)
    return dict(BR=float(np.median((B - R)[m])), GR=float(np.median((G - R)[m])), NG=float(np.median((N - G)[m])),
                bright=float(np.median(((R + G + B) / 3)[m])))
def masks(a, sc):
    R, G, B, N = [x.astype(np.int16) for x in a]
    br, gr, ng = B - R - sc['BR'], G - R - sc['GR'], N - G - sc['NG']
    core = (B > 75) & (br > 50) & (gr > 25) & (ng < 0)
    loose = (B > 55) & (br > 33) & (gr > 12) & (ng < 12)
    return core, loose
def add_ratios(f):
    """hue/darkness ratios: pools are cyan (G/B ~0.9) and bright; shadows and solar panels are darker and bluer"""
    f.update(GB=f['G'] / (f['B'] + 1), RB=f['R'] / (f['B'] + 1), NB=f['N'] / (f['B'] + 1), NG=f['N'] / (f['G'] + 1),
             GRrel=f['GRc'] / max(f['bright'], 1))
    return f
def candidates(a, min_m2=6, max_m2=2500):
    sc = scene(a)
    core, loose = masks(a, sc)
    lab, n = ndi.label(loose, structure=np.ones((3, 3)))
    if n == 0: return []
    has_core = ndi.maximum(core, lab, np.arange(1, n + 1)).astype(bool)
    sizes = ndi.sum(loose, lab, np.arange(1, n + 1))
    keep = has_core & (sizes * PX_M2 >= min_m2) & (sizes * PX_M2 <= max_m2)
    objs = ndi.find_objects(lab)
    Rf, Gf, Bf, Nf = [x.astype(np.float32) for x in a]
    PS = 20; ap = np.pad(a, ((0, 0), (PS, PS), (PS, PS)), mode='edge')
    H, W = lab.shape; out = []
    for i in np.nonzero(keep)[0]:
        sl = objs[i]; pad = 12
        r0, r1 = max(sl[0].start - pad, 0), min(sl[0].stop + pad, H); c0, c1 = max(sl[1].start - pad, 0), min(sl[1].stop + pad, W)
        L = lab[r0:r1, c0:c1] == i + 1
        r, g, b, nn = Rf[r0:r1, c0:c1], Gf[r0:r1, c0:c1], Bf[r0:r1, c0:c1], Nf[r0:r1, c0:c1]
        cr = core[r0:r1, c0:c1]
        area = L.sum()
        ys, xs = np.nonzero(L)
        cy, cx = ys.mean() + r0, xs.mean() + c0
        # shape
        bh, bw = np.ptp(ys) + 1, np.ptp(xs) + 1
        cov = np.cov(np.vstack([ys, xs])) if area > 2 else np.eye(2)
        ev = np.sort(np.linalg.eigvalsh(cov))[::-1]; elong = np.sqrt(ev[0] / max(ev[1], 1e-3))
        try:
            from skimage.morphology import convex_hull_image
            hull = convex_hull_image(L).sum()
        except Exception: hull = bh * bw
        er = ndi.binary_erosion(L); perim = (L & ~er).sum()
        ring = ndi.binary_dilation(L, iterations=10) & ~ndi.binary_dilation(L, iterations=2)
        inner = ndi.binary_dilation(L, iterations=2) & ~L
        ndvi = (nn - r) / (nn + r + 1); bright = (r + g + b) / 3
        f = dict(
            area_m2=area * PX_M2, R=r[L].mean(), G=g[L].mean(), B=b[L].mean(), N=nn[L].mean(), sdB=b[L].std(), maxB=b[L].max(),
            bd=((b - r) / (b + r + 1))[L].mean(), gd=((g - r) / (g + r + 1))[L].mean(), nwi=((g - nn) / (g + nn + 1))[L].mean(),
            bright=bright[L].mean(), core_frac=cr[L].mean(), extent=area / (bh * bw), solidity=area / max(hull, 1),
            elong=elong, compact=perim ** 2 / area, ringNDVI=ndvi[ring].mean() if ring.any() else 0,
            ringBright=bright[ring].mean() if ring.any() else 0,
            ringBR=((b - r) / (b + r + 1))[ring].mean() if ring.any() else 0,
            ringSdBright=bright[ring].std() if ring.any() else 0,
            edgeContrast=(bright[inner].mean() - bright[L].mean()) if inner.any() else 0)
        f.update(BRc=f['B'] - f['R'] - sc['BR'], GRc=f['G'] - f['R'] - sc['GR'], NGc=f['N'] - f['G'] - sc['NG'],
                 sceneBR=sc['BR'], sceneBright=sc['bright'], relBright=f['bright'] / max(sc['bright'], 1))
        add_ratios(f)
        iy, ix = int(round(cy)), int(round(cx))
        f['_patch'] = ap[:, iy:iy + 2 * PS, ix:ix + 2 * PS].copy()
        f['_scene'] = (sc['BR'], sc['GR'], sc['NG'], sc['bright'])
        out.append((cy, cx, f))
    return out
