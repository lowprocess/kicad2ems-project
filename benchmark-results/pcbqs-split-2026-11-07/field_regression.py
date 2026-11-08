"""Full-mesh extraction and inferred-field parity against the saved WPT case."""
import json,time,gc
from pathlib import Path
import numpy as np
from threadpoolctl import threadpool_limits
from pcbqs.power_bridge import load_config,make_board_ports
from pcbqs.mqs_ports import CopperPorts,PortResponse
root=Path(__file__).resolve().parents[2];out=Path(__file__).resolve().parent;old=root/'benchmark-results/wpthb-coupled-2026-11-07'
started=time.monotonic()
while not (out/'timing-comparison.json').exists():
 if time.monotonic()-started>1200:raise RuntimeError('timing regression did not finish')
 time.sleep(2)
cfg=load_config(old/'model.json');board=json.loads((root/'benchmark-results/wpthb-inspection-2026-11-07/board.json').read_text());saved=json.loads((old/'copper-model.json').read_text());key=saved['fingerprint']
def cache(f):return old/'copper-response'/f'{key[:16]}_{f:.9g}.npz'
with threadpool_limits(limits=8,user_api='blas'):
 q,ports,crop=make_board_ports(board,cfg,log=lambda s:print(s,flush=True));start=time.monotonic();actual=CopperPorts(q).extract([110000])
 with np.load(cache(110000)) as data:
  zerr=float(np.linalg.norm(actual.impedance[0]-data['impedance'])/np.linalg.norm(data['impedance']));ierr=float(np.linalg.norm(actual.currents[0]-data['currents'])/np.linalg.norm(data['currents']))
 assert zerr<1e-9 and ierr<1e-9,(zerr,ierr)
 result=dict(extraction_s=time.monotonic()-start,relative_Z_error=zerr,relative_current_error=ierr,triangles=len(q.tris),ports=len(ports))
 q._mats=None;q._copper=None;gc.collect()
 with np.load(old/'110kHz_30W/time_fields.npz') as oldfield:
  frequencies=oldfield['frequencies_Hz'];x,y,z=[oldfield[k] for k in ['x','y','z']];coef=oldfield['port_current_coefficients_A'];expected=oldfield['H_coefficients'].copy()
 currents=[];impedances=[]
 for f in frequencies:
  with np.load(cache(f)) as data:currents.append(data['currents']);impedances.append(data['impedance'])
 response=PortResponse(frequencies,[p['name'] for p in ports],np.asarray(impedances),np.asarray(currents));driven=response.drive(coef)
 H,info=q.h_grid(driven,list(range(len(frequencies))),x*.001,y*.001,z*.001,rtol=.02,return_info=True)
 error=float(np.linalg.norm(H-expected)/np.linalg.norm(expected));assert error<1e-10,error
 result.update(relative_field_error=error,field_grid=info)
(out/'field-parity.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
