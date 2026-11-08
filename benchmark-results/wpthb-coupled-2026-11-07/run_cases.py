"""Independent ngspice cases share the already extracted passive copper model."""
import json,time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
from mom25d.power_bridge import load_config
from mom25d.power_circuit import run_case
p=Path(__file__).resolve().parent
cfg=load_config('mom25d/src/mom25d/data/wpthb-power.json');saved=json.loads((p/'copper-model.json').read_text())
(p/'model.json').write_text(json.dumps(cfg,indent=2))
def case(f,w):
 folder=p/f'{f/1000:g}kHz_{w:g}W';folder.mkdir(exist_ok=True)
 def log(s):print(f'[{f/1000:g}k/{w:g}W] {s}',flush=True)
 start=time.monotonic();r,_=run_case(cfg,f,w,folder,saved['model'],saved['ports'],log)
 log(f'DONE {time.monotonic()-start:.1f}s; P={r["load_power_W"]:.4f} W; phase={r["phase_deg"]:.3f}; primary={r["primary_rms_A"]:.4f} A RMS')
 return r
rows=[]
with ThreadPoolExecutor(max_workers=4) as pool:
 jobs=[pool.submit(case,f,w) for f in cfg['frequencies_Hz'] for w in cfg['powers_W']]
 for job in as_completed(jobs):
  try:rows.append(job.result())
  except Exception as e:print('CASE FAILED:',repr(e),flush=True);raise
  (p/'cases-completed.json').write_text(json.dumps(rows,indent=2))
print('All cases completed.',flush=True)
