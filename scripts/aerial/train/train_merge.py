import numpy as np, evalm
def merge(det, probs=None, R=8):
    """collapse detections within R m (pool split in two, pool + attached spa) to the strongest one"""
    if not det: return det
    order = np.argsort(-np.array(probs)) if probs is not None else range(len(det))
    from scipy.spatial import cKDTree
    X = evalm.xy(det, det[0][0]); t = cKDTree(X); used = np.zeros(len(det), bool); out = []
    for i in order:
        if used[i]: continue
        for j in t.query_ball_point(X[i], R): used[j] = True
        out.append(det[i])
    return out
