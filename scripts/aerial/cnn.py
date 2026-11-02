"""Tiny CNN on 40x40 4-band NAIP patches centred on each candidate (scene-normalised), ~25k parameters."""
import numpy as np, torch, torch.nn as nn
torch.set_num_threads(2)
def prep(p, s):
    """p: (n,4,40,40) uint8, s: (n,4) scene BR,GR,NG,bright -> (n,6,40,40) float32"""
    x = p.astype(np.float32); R, G, B, N = x[:, 0], x[:, 1], x[:, 2], x[:, 3]
    br = s[:, 3][:, None, None]
    ch = [(R - br) / 64, (G - br) / 64, (B - br) / 64, (N - br) / 64,
          (B - R - s[:, 0][:, None, None]) / 48, (G - R - s[:, 1][:, None, None]) / 48]
    return np.stack(ch, 1).astype(np.float32)
class Net(nn.Module):
    def __init__(s):
        super().__init__()
        def blk(i, o): return nn.Sequential(nn.Conv2d(i, o, 3, padding=1), nn.BatchNorm2d(o), nn.ReLU(), nn.Conv2d(o, o, 3, padding=1), nn.BatchNorm2d(o), nn.ReLU(), nn.MaxPool2d(2))
        s.f = nn.Sequential(blk(6, 16), blk(16, 32), blk(32, 48))
        s.h = nn.Sequential(nn.Flatten(), nn.Dropout(0.3), nn.Linear(48 * 5 * 5, 64), nn.ReLU(), nn.Linear(64, 1))
    def forward(s, x): return s.h(s.f(x)).squeeze(1)
def aug(x):
    k = np.random.randint(4); x = torch.rot90(x, k, (2, 3))
    if np.random.rand() < 0.5: x = torch.flip(x, (3,))
    return x
def fit(X, y, epochs=14, seed=0):
    torch.manual_seed(seed); np.random.seed(seed)
    m = Net(); opt = torch.optim.AdamW(m.parameters(), 2e-3, weight_decay=1e-3)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, 3e-3, total_steps=epochs * ((len(X) + 63) // 64))
    X = torch.tensor(X); y = torch.tensor(y, dtype=torch.float32); lossf = nn.BCEWithLogitsLoss()
    for ep in range(epochs):
        m.train(); perm = torch.randperm(len(X)); tot = 0
        for i in range(0, len(X), 64):
            b = perm[i:i + 64]; opt.zero_grad(); l = lossf(m(aug(X[b])), y[b]); l.backward(); opt.step(); sched.step(); tot += l.item() * len(b)
        print('epoch', ep, round(tot / len(X), 4), flush=True)
    return m
def predict(m, X):
    m.eval(); out = []
    with torch.no_grad():
        X = torch.tensor(X)
        for i in range(0, len(X), 512):
            xb = X[i:i + 512]
            # test-time augmentation: 4 rotations
            out.append(torch.stack([torch.sigmoid(m(torch.rot90(xb, k, (2, 3)))) for k in range(4)]).mean(0).numpy())
    return np.concatenate(out) if out else np.zeros(0)
