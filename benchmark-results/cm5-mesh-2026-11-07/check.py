import json, time, hashlib
from pathlib import Path
import numpy as np
from shapely.geometry import box
from shapely.ops import unary_union
from kicad2ems.board import Board
from kicad2ems.importers.kicad import KiCadBoard
from mom25d.pdn.rail import parts_of
from mom25d.mqs import MQS
import mom25d.geo as geo
from mom25d.static import static_moments
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

out=Path(__file__).resolve().parent
path=Path('/usr/share/kicad/demos/cm5_minima/CM5_MINIMA_3.kicad_pcb')
board=Board(KiCadBoard(str(path)),need_ports=False,log=lambda *_:None).to_dict()
(out/'board.json').write_text(json.dumps(board))
parts={p.ref:p for p in parts_of(board)}
terms={}
for ref in ['U702','C704','C705','C706']:
 for net,suffix in [('+5V','vin'),('GND','gnd')]:
  terms[f'{ref}.{suffix}']=[(layer,p.geom) for p in parts[ref].on({net}) for layer in p.layers]
extent=unary_union([p for pads in terms.values() for _,p in pads])
region=extent.buffer(3).envelope
fine=extent.buffer(1).envelope
report=dict(source=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),region_mm=list(region.bounds),meshes=[])
original=geo.tr.triangulate
fig,axes=plt.subplots(2,3,figsize=(14,10))
chosen=None
for row,(name,dmax,quality) in enumerate([('current',1.5,False),('isotropic-fine',.6,True)]):
 if quality:
  def quality_tri(a,opts):
   # Retain all copper, pad, via and fine-region constraints, add angle refinement.
   return original(a,opts+'q30')
  geo.tr.triangulate=quality_tri
 start=time.perf_counter()
 q=MQS(board,{'+5V','GND'},terminals=terms,region=region,dmax=dmax,fine=fine,dmax_fine=.6,log=lambda *_:None,fill_workers=8)
 geo.tr.triangulate=original
 stats=dict(name=name,total_triangles=len(q.tris),mesh_s=time.perf_counter()-start,layers={})
 for layer,ids in q.layer_tris.items():
  v=q.nodes[q.tris[ids]]*1000
  e=np.linalg.norm(v-np.roll(v,1,axis=1),axis=2)
  stats['layers'][layer]=dict(triangles=len(ids),max_edge_mm=float(e.max()),p95_max_edge_mm=float(np.percentile(e.max(1),95)),p95_aspect=float(np.percentile(e.max(1)/e.min(1),95)))
 if chosen is None:
  # Largest internal ground sheet in the current crop; compare same layer in both meshes.
  chosen=max((l for l in q.layer_tris if l.startswith('In')),key=lambda l:len(q.layer_tris[l]))
 layers=['F.Cu',chosen,'B.Cu']
 for col,layer in enumerate(layers):
  ids=q.layer_tris[layer]; ax=axes[row,col]
  ax.triplot(q.nodes[:,0]*1000,q.nodes[:,1]*1000,q.tris[ids],lw=.35)
  ax.set(title=f'{name}: {layer}, {len(ids)} triangles',xlabel='mm',ylabel='mm',aspect='equal',xlim=(region.bounds[0],region.bounds[2]),ylim=(region.bounds[1],region.bounds[3]))
 np.savez(out/f'{name}-mesh.npz',nodes=q.nodes,tris=q.tris,layer_of=q.layer_of)
 ids=q.layer_tris[chosen]; tris=q.tris[ids]; used=np.unique(tris); remap=np.full(len(q.nodes),-1); remap[used]=np.arange(len(used))
 nd=q.nodes[used]; tr=remap[tris]; z=q.z_of[ids]
 stats['benchmark_layer']=chosen; stats['cases']=[]
 ref=static_moments(nd,tr,z,backend='numpy')
 for backend,workers in [('numpy',1),('openmp',8),('cupy',1)]:
  samples=[]; err=0.
  for _ in range(3):
   start=time.perf_counter()
   result,info=static_moments(nd,tr,z,backend=backend,workers=workers,return_info=True)
   samples.append(time.perf_counter()-start)
   for a,b in zip(ref[1:],result[1:]):err=max(err,float(np.linalg.norm(a-b)/np.linalg.norm(a)))
   del result
  stats['cases'].append(dict(info,samples=samples,median_s=float(np.median(samples)),relative_error=err))
  print(name,backend,len(ids),samples,err,flush=True)
 del ref,q
 report['meshes'].append(stats)
 (out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
fig.tight_layout();fig.savefig(out/'meshes.png',dpi=160)
print(json.dumps(report),flush=True)
