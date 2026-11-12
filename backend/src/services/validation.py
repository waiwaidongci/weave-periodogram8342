import numpy as np

def validate_points(points):
 if not 4<=len(points)<=240 or len({p['reference'] for p in points})!=len(points):raise ValueError('需要4..240个唯一测点编号')
 if any(type(p['position']) is bool or type(p['thickness']) is bool for p in points):raise ValueError('数值不能是bool')
 x=np.asarray([p['position'] for p in points],dtype=float);y=np.asarray([p['thickness'] for p in points],dtype=float)
 if not np.isfinite(x).all() or not np.isfinite(y).all() or (x<0).any() or (x>1e12).any() or (y<0).any() or (y>1e6).any():raise ValueError('位置/厚度须有限且在允许范围')
 if len(set(x))!=len(x) or np.ptp(x)>10000:raise ValueError('位置不能重复，测线跨度≤10000mm')
 return sorted(points,key=lambda p:p['position'])

def validate_plan(plan):
 f=np.asarray(plan['frequencies'],dtype=float)
 if f.ndim!=1 or not 3<=len(f)<=401 or not np.isfinite(f).all() or (f<=0).any() or (f>1).any() or (np.diff(f)<=0).any():raise ValueError('频率须3..401个有限严格递增正值且≤1周期/mm')
 if type(plan['permutations']) is not int or not 199<=plan['permutations']<=499 or type(plan['seed']) is not int or not 0<=plan['seed']<=1000000000:raise ValueError('置换次数199..499与seed须合法整数')
 return f
