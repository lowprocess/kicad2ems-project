"""Regenerate the accepted PCB-coupled circuit through pcbqs and compare traces."""
import json,os,time
from pathlib import Path
import numpy as np
from pcbqs.power_bridge import load_config,build
root=Path(__file__).resolve().parents[2];out=Path(__file__).resolve().parent;old=root/'benchmark-results/wpthb-coupled-2026-11-07';results=[]
# Avoid contaminating timings with the separately running RF regression suite.
pid=34306
while Path(f'/proc/{pid}/cmdline').exists():
 try:
  if b'pytest' not in Path(f'/proc/{pid}/cmdline').read_bytes():break
 except FileNotFoundError:break
 time.sleep(2)
os.sched_setaffinity(0,{2})
cfg=load_config(out/'regression-model.json');case=json.loads((old/'110kHz_30W/case.json').read_text());cu=json.loads((old/'copper-model.json').read_text())
for i,cycles in enumerate([8,8,8,52]):
 folder=out/f'after-{i}-{cycles}cycles';c=build(cfg,110000,case['phase_deg'],case['matching'],cu['model'],cu['ports'])
 result=c.run(folder,110000,cycles=cycles,samples_per_cycle=256)
 stats=json.loads((folder/'performance.json').read_text());results.append(dict(cycles=cycles,**stats));print(cycles,stats['ngspice_wall_s'],flush=True)
 if cycles==52:
  with np.load(old/'110kHz_30W/transient.npz') as reference:
   errors={k:float(np.max(abs(result[k]-reference[k]))/max(np.max(abs(reference[k])),1e-30)) for k in reference.files if k!='time_s'}
   errors['time_max_abs_s']=float(np.max(abs(result['time_s']-reference['time_s'])))
  (out/'waveform-parity.json').write_text(json.dumps(errors,indent=2));assert max(errors.values())<1e-8,max(errors.values())
 (out/'after-timing.json').write_text(json.dumps(results,indent=2))
before=[json.loads((root/f'benchmark-results/wpthb-profile-2026-11-07/split-before-{i}/timing.json').read_text())['wall_s'] for i in range(3)]
median_before=float(np.median(before));median_after=float(np.median([r['ngspice_wall_s'] for r in results[:3]]));summary=dict(before_s=before,after_s=[r['ngspice_wall_s'] for r in results[:3]],median_before_s=median_before,median_after_s=median_after,relative_change=median_after/median_before-1,full52_s=results[-1]['ngspice_wall_s'])
(out/'timing-comparison.json').write_text(json.dumps(summary,indent=2));assert summary['relative_change']<=.1,summary;print(json.dumps(summary),flush=True)
