# Build docs/data/poolcheck: county pool records checked against the aerial detections (aerial-q/<tile>/chunks.jsonl).
#  cx = 3+ county records chained within 6 m with no water seen within 25 m (condo units placed on one roof), shown as one marker.
#  nv = county records with no pool detected within 300 m in 2023 NAIP. On by default (approved by Mark, Nov 24 2026); ?check=0 turns it off.
import json,math,os
from collections import defaultdict
Q='/home/claude/aerial-q'; P='/home/claude/project-hydro-shield/docs/data/pools'; O='/home/claude/permitcheck/out'
def m(a,b): return math.hypot((a[0]-b[0])*110574,(a[1]-b[1])*111320*math.cos(math.radians(a[0])))
ncx=ncxpts=nnv=nt=0; allcx=[]
for f in os.listdir(O): os.remove(os.path.join(O,f))
for line in open(Q+'/queue11.txt'):
    t=line.split()[0]; A,B=t[3:].split('x'); key='%s_-%s'%(A,B)
    pf='%s/%s.json'%(P,key); cf='%s/%s/chunks.jsonl'%(Q,t)
    if not (os.path.exists(pf) and os.path.exists(cf)): continue
    county=[p[:2] for p in json.load(open(pf)) if len(p)==2]
    if not county: continue
    det=[d[:2] for l in open(cf) for d in json.loads(l).get('det',[])]
    # air points already published in this tile also count as water seen
    det+= [p[:2] for p in json.load(open(pf)) if len(p)>2 and p[2]=='air']
    g=defaultdict(list)
    for d in det: g[(int(d[0]*200),int(d[1]*200))].append(d)
    def nearest(p):
        k=(int(p[0]*200),int(p[1]*200)); b=9e9
        for i in (-1,0,1):
            for j in (-1,0,1):
                for d in g.get((k[0]+i,k[1]+j),[]): b=min(b,m(p,d))
        return b
    # tight clusters: county points chained within 6 m (condo units placed on one roof)
    pts=list({(round(p[0],5),round(p[1],5)) for p in county}); par=list(range(len(pts)))
    def fd(i):
        while par[i]!=i: par[i]=par[par[i]]; i=par[i]
        return i
    cell=defaultdict(list)
    for i,p in enumerate(pts): cell[(int(p[0]/0.0001),int(p[1]/0.0001))].append(i)
    for i,p in enumerate(pts):
        k=(int(p[0]/0.0001),int(p[1]/0.0001))
        for a in (-1,0,1):
            for b in (-1,0,1):
                for j in cell.get((k[0]+a,k[1]+b),[]):
                    if j>i and m(p,pts[j])<=6: par[fd(i)]=fd(j)
    grp=defaultdict(list)
    for i in range(len(pts)): grp[fd(i)].append(pts[i])
    cx=[]; stacked=set()
    for mem in grp.values():
        if len(mem)<3: continue
        c=(sum(q[0] for q in mem)/len(mem),sum(q[1] for q in mem)/len(mem))
        if max(m(c,q) for q in mem)>25: continue
        if min(nearest(q) for q in mem)<=25: continue
        cx.append([round(c[0],5),round(c[1],5),len(mem),[[q[0],q[1]] for q in mem]]); stacked.update(mem)
    nv=[]; done=set()
    for p in county:
        k5=(round(p[0],5),round(p[1],5))
        if k5 in stacked or k5 in done: continue
        k=(int(p[0]*200),int(p[1]*200)); ok=False
        for i in (-1,0,1):
            for j in (-1,0,1):
                for d in g.get((k[0]+i,k[1]+j),[]):
                    if m(p,d)<300: ok=True; break
                if ok: break
            if ok: break
        if not ok: nv.append([k5[0],k5[1]]); done.add(k5)
    if cx or nv:
        json.dump({'cx':cx,'nv':nv},open('%s/%s.json'%(O,key),'w'),separators=(',',':')); nt+=1
    ncx+=len(cx); ncxpts+=sum(c[2] for c in cx); nnv+=len(nv); allcx.extend([[key]+c[:3] for c in cx])
print('tiles',nt,'stacks',ncx,'stacked records',ncxpts,'unconfirmed points',nnv)
json.dump(allcx,open('/home/claude/permitcheck/allcx.json','w'))
