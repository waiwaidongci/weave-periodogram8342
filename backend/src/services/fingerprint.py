import json,hashlib
from src.constants.numerics import ALGORITHM_VERSION
def fingerprint(study,points,plan):
 payload={'version':ALGORITHM_VERSION,'study':study,'points':sorted(points,key=lambda p:p['position']),'plan':plan}
 return hashlib.sha256(json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
