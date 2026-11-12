import numpy as np
from src.constants.numerics import POWER_TIE_TOL

def centered_response(y):
 y=np.asarray(y,dtype=float)
 if y.ndim!=1 or not np.isfinite(y).all():raise ValueError('厚度须有限一维')
 origin=y[0];offset=y-origin;mean_offset=offset.mean();centered=offset-mean_offset;rss0=float(centered@centered)
 if rss0<=0:raise ValueError('恒定厚度RSS0=0，无可定义的谱功率')
 return centered,float(origin+mean_offset),rss0

def powers(cache,centered,rss0):
 coefficients=np.einsum('fkn,n->fk',cache['Q'],centered);return np.clip(np.sum(coefficients*coefficients,axis=1)/rss0,0,1)

def observed_spectrum(cache,y):
 centered,mean,rss0=centered_response(y);scores=powers(cache,centered,rss0);maximum=float(scores.max());choice=int(np.flatnonzero(scores>=maximum-POWER_TIE_TOL)[0]);grid_index=cache['valid_indices'][choice];entry=cache['entries'][grid_index];a,b=np.linalg.solve(entry['R'],entry['Q'].T@centered);intercept=mean-a*entry['means'][0]-b*entry['means'][1];fitted=intercept+a*entry['cos']+b*entry['sin'];rss=float(np.sum((np.asarray(y)-fitted)**2));amplitude=float(np.hypot(a,b));phase=float(np.arctan2(b,a));frequency=entry['frequency'];scoremap={idx:float(scores[i]) for i,idx in enumerate(cache['valid_indices'])}
 spectrum=[{'frequency':e['frequency'],'period':1/e['frequency'],'included':e['included'],'reason':e['reason'],'singular_values':e['singular_values'],'power':scoremap.get(i),'rss':rss0*(1-scoremap[i]) if i in scoremap else None,'window_power':e['window_power']} for i,e in enumerate(cache['entries'])]
 return {'rss0':rss0,'observed_max_power':maximum,'spectrum':spectrum,'included_frequencies':len(scores),'excluded_frequencies':len(spectrum)-len(scores),'best':{'frequency':frequency,'period':1/frequency,'power':float(scores[choice]),'intercept':float(intercept),'cos_coefficient':float(a),'sin_coefficient':float(b),'amplitude':amplitude,'phase_rad':phase,'phase_origin':cache['origin'],'phase_definition':'c + A*cos(2*pi*f*(x-x0)-phi), phi=atan2(sin_coefficient,cos_coefficient)','rss':rss},'fit':[{'position':float(x),'observed':float(v),'fitted':float(pred),'residual':float(v-pred)} for x,v,pred in zip(cache['x'],y,fitted)]},centered
