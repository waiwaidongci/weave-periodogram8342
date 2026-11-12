import numpy as np
from src.constants.numerics import QR_RANK_TOL

def build_cache(x,frequencies):
 x=np.asarray(x,dtype=float);f=np.asarray(frequencies,dtype=float)
 if x.ndim!=1 or len(x)<4 or not np.isfinite(x).all() or (np.diff(x)<=0).any() or f.ndim!=1 or not len(f) or not np.isfinite(f).all() or (f<=0).any() or (np.diff(f)<=0).any():raise ValueError('QR需要递增唯一有限位置与正频率')
 origin=float(x[0]);t=x-origin;entries=[];Q=[];valid=[]
 for index,frequency in enumerate(f):
  phase=2*np.pi*frequency*t;c=np.cos(phase);s=np.sin(phase);means=np.array([c.mean(),s.mean()]);A=np.column_stack((c-means[0],s-means[1]));sv=np.linalg.svd(A,compute_uv=False);threshold=QR_RANK_TOL*max(float(sv[0]),np.sqrt(len(x)));window=float(c.mean()**2+s.mean()**2)
  if sv[-1]<=threshold:entries.append({'frequency':float(frequency),'included':False,'reason':'中心化sin/cos秩不足或病态：sigma_min≤1e-10*max(sigma_max,sqrtN)','singular_values':sv.tolist(),'window_power':window});continue
  q,R=np.linalg.qr(A,mode='reduced');entries.append({'frequency':float(frequency),'included':True,'reason':None,'singular_values':sv.tolist(),'window_power':window,'means':means,'R':R,'Q':q,'cos':c,'sin':s});Q.append(q.T);valid.append(index)
 if not Q:raise ValueError('全部频率退化，无可用谱')
 return {'origin':origin,'x':x,'frequencies':f,'entries':entries,'Q':np.stack(Q),'valid_indices':valid,'cache_builds':1}
