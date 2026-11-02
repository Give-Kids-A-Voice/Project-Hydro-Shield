import sys, pickle, numpy as np, peval
from train_merge import merge
from areas import AREAS
S = pickle.load(open('scores.pkl', 'rb')); data = {n: peval.load(n) for n in AREAS}
def run(n, mode, thr):
    (g, c), ll = S[n]; p = {'gbm': g, 'cnn': c, 'avg': (g + c) / 2, 'min': np.minimum(g, c)}[mode]
    idx = np.nonzero(p >= thr)[0]; idx = idx[np.argsort(-p[idx])]
    return peval.evaluate(n, merge([ll[i] for i in idx], p[idx]), data[n])
for mode in sys.argv[1].split(','):
    for thr in map(float, sys.argv[2].split(',')):
        tot = [0, 0, 0, 0]; line = []
        for n in AREAS:
            if AREAS[n][3] != 'test': continue
            r = run(n, mode, thr); tot[0] += r['n_det']; tot[1] += r['tp']; tot[2] += r['n_gt']; tot[3] += r['found']
            line.append(f"{n.split('_')[-1][:8]} {r['prec']:.2f}/{r['rec']:.2f}")
        print(f"{mode} {thr}: pooled P {tot[1]/tot[0]:.3f} R {tot[3]/tot[2]:.3f} | " + '  '.join(line), flush=True)
