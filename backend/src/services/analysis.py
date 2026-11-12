from .validation import validate_points,validate_plan
from .qr_cache import build_cache
from .spectrum import observed_spectrum
from .permutation import global_permutation,new_checkpoint,run_permutations
from .fingerprint import fingerprint

def prepare(study,points,plan):
 """冻结快照 -> 校验、QR缓存与观测谱；置换阶段之外的全部确定性前处理。"""
 points=validate_points(points);f=validate_plan(plan)
 x=[p['position'] for p in points];y=[p['thickness'] for p in points]
 cache=build_cache(x,f)
 result,centered=observed_spectrum(cache,y)
 return cache,result,centered,points

def analyze(study,points,plan):
 cache,result,centered,points=prepare(study,points,plan)
 test=global_permutation(cache,centered,result['rss0'],result['observed_max_power'],plan['permutations'],plan['seed'])
 return {**result,'global_test':test,'source_study':study,'plan':plan,'n':len(points),'coordinate_origin':cache['origin'],'qr_cache_builds':1,'fingerprint':fingerprint(study,points,plan),'tie_rule':'lowest frequency within absolute power tolerance 1e-12 of maximum; upper-tail null ties use same tolerance','interpretation':'Frozen predeclared frequency grid. Sampling window, aliasing, leakage and grid spacing limit interpretation; the selected period is not a confidence interval or a manufacturing cause. Independent homoscedastic exchangeable errors are required.'}

def analyze_with_progress(study,points,plan,resumed_checkpoint,on_progress):
 """可断点续跑版本：沿用排队快照与确定性置换顺序，完成后返回与analyze一致的结果。"""
 cache,result,centered,points=prepare(study,points,plan)
 checkpoint=resumed_checkpoint or new_checkpoint(plan,len(points),result['observed_max_power'],result['rss0'])
 test=run_permutations(cache,centered,result['rss0'],result['observed_max_power'],plan,checkpoint,on_progress)
 return {**result,'global_test':test,'source_study':study,'plan':plan,'n':len(points),'coordinate_origin':cache['origin'],'qr_cache_builds':1,'fingerprint':fingerprint(study,points,plan),'tie_rule':'lowest frequency within absolute power tolerance 1e-12 of maximum; upper-tail null ties use same tolerance','interpretation':'Frozen predeclared frequency grid. Sampling window, aliasing, leakage and grid spacing limit interpretation; the selected period is not a confidence interval or a manufacturing cause. Independent homoscedastic exchangeable errors are required.'}
