"""python3 psheet.py <workdir> <year> <out.png>: all (<=48, seed 7) unmapped ponds with outline drawn on ~150 m NAIP chips."""
import sys,json,random,numpy as np
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0,'/home/claude/project-hydro-shield/scripts/aerial'); import naip
from PIL import Image,ImageDraw
wd,yr,out=sys.argv[1],int(sys.argv[2]),sys.argv[3]
P=[json.loads(l) for l in open(wd+'/ponds.jsonl')]
random.seed(7); pick=random.sample(P,min(48,len(P)))
def chip(p):
    la,lo=p[0],p[1]; H=max(0.0007,1.4*max(abs(q[0]-la) for q in p[4])); W=H*1.13
    bb=(lo-W,la-H,lo+W,la+H)
    try: a,tr,crs,res=naip.read(naip.items(bb,yr)[0],bb); im=Image.fromarray(np.dstack(a[:3]).astype(np.uint8)).resize((200,200))
    except Exception: return Image.new('RGB',(200,200))
    d=ImageDraw.Draw(im); pts=[((q[1]-lo+W)/(2*W)*200,(la+H-q[0])/(2*H)*200) for q in p[4]]
    d.line(pts+[pts[0]],fill=(255,0,255),width=2); return im
with ThreadPoolExecutor(6) as ex: ims=list(ex.map(chip,pick))
S=Image.new('RGB',(1200,((len(ims)+5)//6)*200)); dr=ImageDraw.Draw(S)
for i,im in enumerate(ims): S.paste(im,((i%6)*200,(i//6)*200)); dr.text(((i%6)*200+3,(i//6)*200+2),f'{i} {pick[i][2]}m2 {pick[i][3]:.2f}',fill=(255,255,0))
S.save(out); print(len(P),'ponds,',len(pick),'shown ->',out)
