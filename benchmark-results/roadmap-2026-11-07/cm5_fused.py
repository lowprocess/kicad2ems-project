import json,time
from pathlib import Path
import numpy as np
from mom25d.static import static_moments
out=Path(__file__).resolve().parent
results=[]
for name in ['current','isotropic-fine']:
 mesh=np.load(out.parent/f'cm5-mesh-2026-11-07/{name}-mesh.npz')
 ids=mesh['layer_of']=='In3.Cu';tr=mesh['tris'][ids];used=np.unique(tr)
 remap=np.full(len(mesh['nodes']),-1);remap[used]=np.arange(len(used))
 nd=mesh['nodes'][used];tr=remap[tr];z=np.zeros(len(tr))
 ref=static_moments(nd,tr,z,backend='openmp',workers=8)
 for backend in ['openmp','cupy']:
  samples=[];err=0
  for _ in range(3):
   start=time.perf_counter();result,info=static_moments(nd,tr,z,backend=backend,workers=8,return_info=True)
   samples.append(time.perf_counter()-start)
   err=max(err,max(float(np.linalg.norm(a-b)/np.linalg.norm(a)) for a,b in zip(ref[1:],result[1:])))
   del result
  results.append(dict(mesh=name,backend=backend,samples=samples,median_s=float(np.median(samples)),relative_error=err,info=info))
  print(results[-1],flush=True)
 del ref
(out/'cm5-fused.json').write_text(json.dumps(results,indent=2))
