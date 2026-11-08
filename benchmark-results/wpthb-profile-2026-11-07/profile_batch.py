"""Four identical eight-cycle full-PCB transients: sequential vs parallel, trace comparison."""
import json,os,subprocess,sys,time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np
p=Path(__file__).resolve().parent
rows={}
for jobs in [1,4]:
 start=time.perf_counter()
 def run(i):
  name=f'batch-j{jobs}-{i}';r=subprocess.run([sys.executable,str(p/'profile.py'),'--name',name],check=True,stdout=subprocess.PIPE,text=True)
  return json.loads(r.stdout)
 with ThreadPoolExecutor(max_workers=jobs) as pool:cases=list(pool.map(run,range(4)))
 rows[str(jobs)]=dict(wall_s=time.perf_counter()-start,cases=cases);(p/'batch.json').write_text(json.dumps(rows,indent=2));print(jobs,rows[str(jobs)]['wall_s'],flush=True)
base=np.loadtxt(p/'batch-j1-0/transient.dat',skiprows=1)
rows['trace_relative_errors']={}
for jobs in [1,4]:
 for i in range(4):
  v=np.loadtxt(p/f'batch-j{jobs}-{i}/transient.dat',skiprows=1);rows['trace_relative_errors'][f'{jobs}-{i}']=float(np.max(abs(v-base))/max(abs(base).max(),1e-30))
rows['speedup']=rows['1']['wall_s']/rows['4']['wall_s'];(p/'batch.json').write_text(json.dumps(rows,indent=2));print('SPEEDUP',rows['speedup'],'max trace difference',max(rows['trace_relative_errors'].values()),flush=True)
