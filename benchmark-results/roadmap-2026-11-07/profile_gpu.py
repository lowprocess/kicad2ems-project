"""Profile warm CuPy fill; synchronization split is diagnostic and adds overhead."""
import json,time,cProfile,pstats
from pathlib import Path
import numpy as np
import cupy as cp
from mom25d.static import static_moments
from mom25d.static_cupy import CupyBackend
p=Path(__file__).resolve().parent
mesh=np.load(p.parent/'cm5-mesh-2026-11-07/isotropic-fine-mesh.npz')
ids=mesh['layer_of']=='In3.Cu';tr=mesh['tris'][ids];used=np.unique(tr)
remap=np.full(len(mesh['nodes']),-1);remap[used]=np.arange(len(used));nd=mesh['nodes'][used];tr=remap[tr];z=np.zeros(len(tr))
# Warm device/kernel caches before measuring.
static_moments(nd[:],tr[:8],z[:8],backend='cupy')
metrics=dict(evaluations=0,evaluate_s=0.,queued_device_wait_s=0.,download_s=0.,downloads=0)
real_download=cp.asnumpy;real_evaluate=CupyBackend.evaluate

def download(*a,**kw):
 t=time.perf_counter();cp.cuda.get_current_stream().synchronize();metrics['queued_device_wait_s']+=time.perf_counter()-t
 t=time.perf_counter();r=real_download(*a,**kw);metrics['download_s']+=time.perf_counter()-t;metrics['downloads']+=1;return r

def evaluate(self,*a,**kw):
 t=time.perf_counter();r=real_evaluate(self,*a,**kw);metrics['evaluate_s']+=time.perf_counter()-t;metrics['evaluations']+=1;return r
cp.asnumpy=download;CupyBackend.evaluate=evaluate
prof=cProfile.Profile();t=time.perf_counter();prof.enable()
_,info=static_moments(nd,tr,z,backend='cupy',return_info=True)
prof.disable();metrics['total_s']=time.perf_counter()-t
cp.asnumpy=real_download;CupyBackend.evaluate=real_evaluate
metrics['fill_info']=info
(p/'gpu-profile-fused.json').write_text(json.dumps(metrics,indent=2))
with (p/'gpu-profile-fused.txt').open('w') as f:pstats.Stats(prof,stream=f).sort_stats('cumulative').print_stats(40)
print(json.dumps(metrics))
