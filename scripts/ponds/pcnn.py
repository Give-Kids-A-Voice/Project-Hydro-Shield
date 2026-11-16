"""Tiny CNN for pond candidates: 48x48 4-band patches (~58 m at 1.2 m/px), patch-normalised, ~40k parameters."""
import numpy as np, torch, torch.nn as nn
torch.set_num_threads(4)
def prep(p):
    x = p.astype(np.float32); R, G, B, N = x[:, 0], x[:, 1], x[:, 2], x[:, 3]
    mu = x.reshape(len(x), -1).mean(1)[:, None, None]
    ndwi = (G - N) / (G + N + 1); ndvi = (N - R) / (N + R + 1)
    return np.stack([(R - mu) / 64, (G - mu) / 64, (B - mu) / 64, (N - mu) / 64, ndwi * 2, ndvi * 2], 1).astype(np.float32)
class Net(nn.Module):
    def __init__(s):
        super().__init__()
        def blk(i, o): return nn.Sequential(nn.Conv2d(i, o, 3, padding=1), nn.BatchNorm2d(o), nn.ReLU(), nn.Conv2d(o, o, 3, padding=1), nn.BatchNorm2d(o), nn.ReLU(), nn.MaxPool2d(2))
        s.f = nn.Sequential(blk(6, 16), blk(16, 32), blk(32, 48), blk(48, 64))
        s.h = nn.Sequential(nn.Flatten(), nn.Dropout(0.3), nn.Linear(64 * 3 * 3, 64), nn.ReLU(), nn.Linear(64, 1))
    def forward(s, x): return s.h(s.f(x)).squeeze(1)
def aug(x):
    k = np.random.randint(4); x = torch.rot90(x, k, (2, 3))
    if np.random.rand() < 0.5: x = torch.flip(x, (3,))
    return x
def fit(X, y, w=None, epochs=12, seed=0):
    torch.manual_seed(seed); np.random.seed(seed)
    m = Net(); opt = torch.optim.AdamW(m.parameters(), 2e-3, weight_decay=1e-3)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, 3e-3, total_steps=epochs * ((len(X) + 63) // 64))
    X = torch.tensor(X); y = torch.tensor(y, dtype=torch.float32)
    w = torch.ones(len(y)) if w is None else torch.tensor(w, dtype=torch.float32)
    for ep in range(epochs):
        m.train(); perm = torch.randperm(len(X)); tot = 0
        for i in range(0, len(X), 64):
            b = perm[i:i + 64]; opt.zero_grad()
            l = (nn.functional.binary_cross_entropy_with_logits(m(aug(X[b])), y[b], reduction='none') * w[b]).mean()
            l.backward(); opt.step(); sched.step(); tot += l.item() * len(b)
        print('epoch', ep, round(tot / len(X), 4), flush=True)
    return m
def predict(m, X):
    m.eval(); out = []
    with torch.no_grad():
        X = torch.tensor(X)
        for i in range(0, len(X), 512):
            xb = X[i:i + 512]
            out.append(torch.stack([torch.sigmoid(m(torch.rot90(xb, k, (2, 3)))) for k in range(4)]).mean(0).numpy())
    return np.concatenate(out) if out else np.zeros(0)
