import numpy as np
from .spectrum import powers
from src.constants.numerics import POWER_TIE_TOL

def global_permutation(cache,centered,rss0,observed_max,B,seed,permutation_indices=None):
 rng=np.random.default_rng(seed);null=[]
 iterable=permutation_indices if permutation_indices is not None else (rng.permutation(len(centered)) for _ in range(B))
 for indices in iterable:null.append(float(powers(cache,centered[np.asarray(indices,dtype=int)],rss0).max()))
 count=sum(v>=observed_max-POWER_TIE_TOL for v in null);p=(count+1)/(len(null)+1);hist,edges=np.histogram(null,bins=np.linspace(0,1,21))
 return {'permutations':len(null),'seed':seed,'null_maxima':null,'exceedances_with_ties':count,'global_p':p,'minimum_monte_carlo_p':1/(len(null)+1),'power_tie_tolerance':POWER_TIE_TOL,'histogram':{'counts':hist.tolist(),'edges':edges.tolist()},'definition':'Fixed x, permute y labels; refit every included frequency using one cached QR basis, then take full-grid maximum. p=(1+#nullmax>=observedmax-tol)/(B+1).','assumptions':'iid exchangeable, homoscedastic errors under no spatial periodic signal; not single-frequency p, period CI, process cause, or online diagnosis.'}
