"""Train the pond classifier on ds/*.npz. Hold out one area (argv[1], default 'psl') for evaluation.
Labels: 1 = mapped water, 0 = no mapped water nearby (may include unmapped ponds: that's what we want to find).
Saves model/gbm.pkl and model/cnn{0,1,2}.pt and prints held-out precision/recall at several thresholds."""
import sys, glob, os, pickle, numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
import pcnn
hold = sys.argv[1] if len(sys.argv) > 1 else 'psl'
os.makedirs('model', exist_ok=True)
D = {os.path.basename(f)[:-4]: np.load(f) for f in sorted(glob.glob('ds/*.npz'))}
def cat(keys):
    F = np.concatenate([D[k]['F'] for k in keys]); P = np.concatenate([D[k]['P'] for k in keys]); Y = np.concatenate([D[k]['Y'] for k in keys])
    s = Y >= 0; return F[s], P[s], Y[s]
tr = [k for k in D if k != hold]; te = [hold] if hold in D else []
F, P, Y = cat(tr); print('train', len(Y), 'pos', Y.sum(), 'areas', tr)
gbm = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, max_leaf_nodes=31, l2_regularization=1.0).fit(F, Y)
X = pcnn.prep(P); nets = [pcnn.fit(X, Y.astype(np.float32), seed=s) for s in range(3)]
def score(F, P):
    X = pcnn.prep(P); return 0.5 * gbm.predict_proba(F)[:, 1] + 0.5 * np.mean([pcnn.predict(m, X) for m in nets], 0)
if te:
    Ft, Pt, Yt = cat(te); s = score(Ft, Pt)
    for t in (0.5, 0.6, 0.7, 0.8, 0.9):
        k = s >= t; print(f'held-out {hold} thr {t}: kept {k.sum()}, precision(vs map) {Yt[k].mean() if k.any() else 0:.2f}, recall {(k & (Yt == 1)).sum() / max(Yt.sum(), 1):.2f}')
pickle.dump(gbm, open('model/gbm.pkl', 'wb'))
import torch
for i, m in enumerate(nets): torch.save(m.state_dict(), f'model/cnn{i}.pt')
print('saved model/')
