import pickle,numpy as np,torch,pcnn
gbm=pickle.load(open('model/gbm.pkl','rb')); nets=[]
for k in range(3):
    m=pcnn.Net(); m.load_state_dict(torch.load(f'model/cnn{k}.pt')); m.eval(); nets.append(m)
def score(F,P):
    X=pcnn.prep(P); return 0.5*gbm.predict_proba(F)[:,1]+0.5*np.mean([pcnn.predict(m,X) for m in nets],0)
