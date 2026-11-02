"""Train GBM (features) + CNN (patches) on training areas; evaluate held-out areas with the combined score."""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..'))  # detect, cnn, naip
import sys, json, pickle, numpy as np, torch
from sklearn.ensemble import HistGradientBoostingClassifier
from shapely.strtree import STRtree
import peval, detect, evalm, cnn
from train_merge import merge
from areas import AREAS
FE = detect.FEATS
data = {n: peval.load(n) for n in AREAS}
def labels(n):
    P, C, osm, inner = data[n]; tree = STRtree(P)
    X = np.array([[f[k] for k in FE] for f in C]); ll = [(f['lat'], f['lon']) for f in C]
    z = np.load(f'cand/{n}_patches.npz'); PX = cnn.prep(z['p'], z['s'])
    w = [peval.which_pool(P, tree, la, lo) for la, lo in ll]
    nosm = evalm.near(ll, osm, 15) if osm else np.zeros(len(C), bool)
    strength = X[:, FE.index('core_frac')] * X[:, FE.index('area_m2')]; best = {}
    for i, q in enumerate(w):
        if q is not None and (q not in best or strength[i] > strength[best[q]]): best[q] = i
    y = np.zeros(len(C), int); use = np.ones(len(C), bool)
    for i, q in enumerate(w):
        if q is not None: y[i] = int(best[q] == i); use[i] = best[q] == i
    y[nosm] = 1; use[nosm] = True
    return X, PX, y, ll, use
L = {n: labels(n) for n in AREAS}
train = [n for n in AREAS if AREAS[n][3] == 'train']
cat = lambda k: np.concatenate([L[n][k][L[n][4]] for n in train])
Xtr, Ptr, ytr = cat(0), cat(1), cat(2)
print('train', len(ytr), 'pos', ytr.sum(), flush=True)
gbm = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, max_leaf_nodes=15, min_samples_leaf=20, l2_regularization=1.0, random_state=0).fit(Xtr, ytr)
nets = [cnn.fit(Ptr, ytr, seed=sd) for sd in (0, 1, 2)]
pickle.dump(gbm, open('model.pkl', 'wb'))
for k, net in enumerate(nets): torch.save(net.state_dict(), f'cnn{k}.pt')
S = {}
for n in AREAS:
    X, PX, y, ll, use = L[n]; S[n] = (gbm.predict_proba(X)[:, 1], np.mean([cnn.predict(net, PX) for net in nets], 0))
pickle.dump({n: (S[n], L[n][3]) for n in AREAS}, open('scores.pkl', 'wb'))
