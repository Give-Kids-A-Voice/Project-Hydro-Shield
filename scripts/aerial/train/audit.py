import sys, json, pickle, random, numpy as np, peval, sheet
from train_merge import merge
from areas import AREAS
S = pickle.load(open('scores.pkl', 'rb'))
n, thr, k, which = sys.argv[1], float(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
(g, c), ll = S[n]; p = (g + c) / 2
idx = np.nonzero(p >= thr)[0]; idx = idx[np.argsort(-p[idx])]
r = peval.evaluate(n, merge([ll[i] for i in idx], p[idx]), peval.load(n))
pool = [d for d, o in zip(r['det'], r['ok']) if (not o if which == 'fp' else o)]
random.seed(7); pick = random.sample(pool, min(k, len(pool)))
sheet.crops(pick, AREAS[n][2]).save(f'crops/{which}_{n}.png'); json.dump(pick, open(f'crops/{which}_{n}.json', 'w'))
print(n, which, len(pool), 'of', r['n_det'])
