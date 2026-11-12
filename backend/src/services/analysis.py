from .validation import validate_points,validate_plan
from .qr_cache import build_cache
from .spectrum import observed_spectrum
from .permutation import global_permutation
from .fingerprint import fingerprint

def analyze(study,points,plan):
 points=validate_points(points);f=validate_plan(plan);x=[p['position'] for p in points];y=[p['thickness'] for p in points];cache=build_cache(x,f);result,centered=observed_spectrum(cache,y);test=global_permutation(cache,centered,result['rss0'],result['observed_max_power'],plan['permutations'],plan['seed'])
 return {**result,'global_test':test,'source_study':study,'plan':plan,'n':len(points),'coordinate_origin':cache['origin'],'qr_cache_builds':1,'fingerprint':fingerprint(study,points,plan),'tie_rule':'lowest frequency within absolute power tolerance 1e-12 of maximum; upper-tail null ties use same tolerance','interpretation':'Frozen predeclared frequency grid. Sampling window, aliasing, leakage and grid spacing limit interpretation; the selected period is not a confidence interval or a manufacturing cause. Independent homoscedastic exchangeable errors are required.'}
