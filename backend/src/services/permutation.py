import hashlib
import json
import math
import numpy as np
from .spectrum import powers
from src.constants.numerics import POWER_TIE_TOL

CHECKPOINT_VERSION=1
# 每完成一批置换就落一次盘；崩溃最多丢失这一批的进度，重复批次不重复累计
BATCH_SIZE=25


def permutation_sequence(n,B,seed):
 """与排队时完全一致的确定性置换序列：rng=default_rng(seed)，顺序产出B个长度n的标签排列。"""
 rng=np.random.default_rng(seed)
 return [rng.permutation(n).astype(int,copy=True) for _ in range(B)]


def checkpoint_fingerprint(plan,n_points,observed_max,rss0):
 """进度快照绑定的输入指纹：计划(测点/频率/B/seed)与观测统计，任一变化都拒绝续跑。"""
 payload={
  'version':CHECKPOINT_VERSION,
  'n_points':int(n_points),
  'rss0':float(rss0),
  'observed_max_power':float(observed_max),
  'plan':plan,
 }
 return hashlib.sha256(json.dumps(payload,ensure_ascii=False,sort_keys=True,
        separators=(',',':'),allow_nan=False).encode()).hexdigest()


def new_checkpoint(plan,n_points,observed_max,rss0):
 return {
  'version':CHECKPOINT_VERSION,
  'fingerprint':checkpoint_fingerprint(plan,n_points,observed_max,rss0),
  'total':int(plan['permutations']),
  'seed':int(plan['seed']),
  'completed':0,
  'null_maxima':[],
 }


def _is_int(value):
 return isinstance(value,int) and not isinstance(value,bool) and value>=0


def _is_finite_float(value):
 return isinstance(value,float) and math.isfinite(value)


def validate_checkpoint(checkpoint,plan,n_points,observed_max,rss0):
 """严格校验落盘进度；任何损坏、截断或与当前输入不匹配都明确拒绝，绝不拼出成功结果。"""
 if not isinstance(checkpoint,dict):
  raise ValueError('进度快照不是有效对象，拒绝续跑')
 required={'version','fingerprint','total','seed','completed','null_maxima'}
 if set(checkpoint.keys())!=required:
  raise ValueError('进度快照字段缺失或被篡改，拒绝续跑')
 if checkpoint['version']!=CHECKPOINT_VERSION:
  raise ValueError('进度快照版本不匹配，拒绝续跑')
 if not _is_int(checkpoint['total']) or not _is_int(checkpoint['seed']) \
    or not _is_int(checkpoint['completed']):
  raise ValueError('进度快照计数不是合法非负整数，拒绝续跑')
 if not isinstance(checkpoint['fingerprint'],str) or len(checkpoint['fingerprint'])!=64:
  raise ValueError('进度快照指纹损坏，拒绝续跑')
 if not isinstance(checkpoint['null_maxima'],list):
  raise ValueError('进度快照null分布损坏，拒绝续跑')
 if checkpoint['total']!=int(plan['permutations']) or checkpoint['seed']!=int(plan['seed']):
  raise ValueError('进度快照与排队时的频率计划不匹配，拒绝续跑')
 if not 0<=checkpoint['completed']<=checkpoint['total']:
  raise ValueError('进度快照完成数越界，拒绝续跑')
 if len(checkpoint['null_maxima'])!=checkpoint['completed']:
  raise ValueError('进度快照完成数与null最大值数量不一致，拒绝续跑')
 if any(not _is_finite_float(v) or not 0.0<=v<=1.0 for v in checkpoint['null_maxima']):
  raise ValueError('进度快照含非法null最大值，拒绝续跑')
 expected=checkpoint_fingerprint(plan,n_points,observed_max,rss0)
 try:
  int(checkpoint['fingerprint'],16)
 except ValueError:
  raise ValueError('进度快照指纹损坏，拒绝续跑')
 if checkpoint['fingerprint']!=expected:
  raise ValueError('进度快照指纹与当前测点/频率计划/观测统计不匹配，拒绝续跑')


def run_permutations(cache,centered,rss0,observed_max,plan,checkpoint,on_progress):
 """按确定性顺序从completed处续跑剩余置换；已完成的批次不重算、不重复累计。"""
 n=len(centered);B=int(plan['permutations'])
 validate_checkpoint(checkpoint,plan,n,observed_max,rss0)
 sequence=permutation_sequence(n,B,plan['seed'])
 null_maxima=list(checkpoint['null_maxima'])
 start=checkpoint['completed']
 batch=[]
 for index in range(start,B):
  value=float(powers(cache,centered[sequence[index]],rss0).max())
  if not math.isfinite(value) or not 0.0<=value<=1.0:
   raise ValueError(f'第{index+1}次置换产生非法功率，拒绝写入进度')
  batch.append(value)
  if len(batch)>=BATCH_SIZE or index==B-1:
   null_maxima.extend(batch);batch=[]
   saved=dict(checkpoint)
   saved['completed']=len(null_maxima)
   saved['null_maxima']=null_maxima
   on_progress(saved)
   checkpoint=saved
 if len(null_maxima)!=B:
  raise ValueError('置换计数异常，拒绝产出结果')
 return summarize(null_maxima,observed_max,plan['seed'])


def summarize(null,observed_max,seed):
 count=sum(v>=observed_max-POWER_TIE_TOL for v in null)
 hist,edges=np.histogram(np.asarray(null,dtype=float),bins=np.linspace(0,1,21))
 return {'permutations':len(null),'seed':seed,'null_maxima':list(null),
  'exceedances_with_ties':count,'global_p':(count+1)/(len(null)+1),
  'minimum_monte_carlo_p':1/(len(null)+1),'power_tie_tolerance':POWER_TIE_TOL,
  'histogram':{'counts':hist.tolist(),'edges':edges.tolist()},
  'definition':'Fixed x, permute y labels; refit every included frequency using one cached QR basis, then take full-grid maximum. p=(1+#nullmax>=observedmax-tol)/(B+1).',
  'assumptions':'iid exchangeable, homoscedastic errors under no spatial periodic signal; not single-frequency p, period CI, process cause, or online diagnosis.'}


def global_permutation(cache,centered,rss0,observed_max,B,seed,permutation_indices=None):
 """一次性直通实现（兼容seed_demo等同步调用方），数值口径与分段续跑完全一致。"""
 if permutation_indices is None:
  permutation_indices=permutation_sequence(len(centered),B,seed)
 null=[float(powers(cache,centered[np.asarray(indices,dtype=int)],rss0).max())
       for indices in permutation_indices]
 return summarize(null,observed_max,seed)
