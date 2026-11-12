import csv,io
from fastapi.responses import Response
def csv_response(filename,rows,headers):
 output=io.StringIO();writer=csv.writer(output);writer.writerow(headers)
 for values in rows:writer.writerow([("'"+v) if isinstance(v,str) and v.startswith(('=','+','-','@')) else v for v in values])
 return Response('﻿'+output.getvalue(),media_type='text/csv; charset=utf-8',headers={'Content-Disposition':f'attachment; filename="{filename}"'})
