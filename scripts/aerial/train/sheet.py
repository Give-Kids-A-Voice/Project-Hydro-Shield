"""Save a contact sheet of NAIP crops (~48 m square) around points: python3 sheet.py out.png year lat,lon lat,lon ..."""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))  # detect, cnn, naip
import sys, numpy as np, naip
from PIL import Image, ImageDraw
def crops(pts, year, half=0.00022, labels=None):
    tiles = []
    for k, (la, lo) in enumerate(pts):
        bb = (lo - half * 1.2, la - half, lo + half * 1.2, la + half)
        fs = naip.items(bb, year)
        if not fs: continue
        a, tr, crs, res = naip.read(fs[0], bb)
        if res < 0.45: a = a[:, ::2, ::2]
        im = Image.fromarray(np.moveaxis(a[:3], 0, -1)).resize((200, 200))
        d = ImageDraw.Draw(im); d.ellipse((94, 94, 106, 106), outline=(255, 0, 0))
        d.text((3, 3), str(labels[k] if labels else k), fill=(255, 255, 0)); tiles.append(im)
    W = 6; S = Image.new('RGB', (200 * W, 200 * ((len(tiles) + W - 1) // W)))
    for i, t in enumerate(tiles): S.paste(t, ((i % W) * 200, (i // W) * 200))
    return S
