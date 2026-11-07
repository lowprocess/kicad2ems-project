"""Discover all eight bucks and preflight crop sizes; pilot one input-loop solve."""
import json,time
from pathlib import Path
from shapely.ops import unary_union
from mom25d.mqs_cli import load_board,discover,select,parser,run
from mom25d.mqs import MQS
out=Path(__file__).resolve().parent
source='/usr/share/kicad/demos/jetson-agx-thor-baseboard/jetson-agx-thor-baseboard.kicad_pcb'
cache=out/'jetson-board.json'
if cache.exists():board=load_board(cache)
else:
 board=load_board(source);cache.write_text(json.dumps(board))
results=[]
for ref in sorted({c['converter'] for c in discover(board)}):
 vin={'U65':'VCC_IN','U69':'+5V','U7':'+5V'}.get(ref,'VCC')
 a=parser().parse_args([str(cache),'--converter',ref,'--vin',vin,'--cap-radius','4','--margin','2','--dmax','2',
                       '--fine','1','--harmonics','1','--heights','3','--scan-points','7','--fill-backend','openmp',
                       '--fill-workers','8','--out',str(out/f'jetson-{ref}')])
 try:
  selected,terms=select(board,a)
  extent=unary_union([p for pp in terms.values() for _,p in pp]);crop=extent.buffer(a.margin).envelope
  q=MQS(board,{selected['vin'],a.ground},terminals=terms,region=crop,dmax=a.dmax,fine=extent.buffer(1).envelope,dmax_fine=a.fine,log=lambda *_:None)
  record=dict(converter=ref,selection=selected,triangles=len(q.tris),edges=q.ne)
  del q
  # Bound these smoke tests; oversized crops need a smaller region or compression.
  if record['triangles']<15000:
   saved=out/f'jetson-{ref}'/'mqs.json'
   r=json.loads(saved.read_text()) if saved.exists() else run(a)
   record['pilot']=dict(copper_R_ohm=r['copper_R_ohm'],copper_L_H=r['copper_L_H'],seconds=r['seconds'])
 except (ValueError,RuntimeError) as exc:record=dict(converter=ref,error=str(exc))
 results.append(record);print(record,flush=True)
 (out/'jetson-preflight.json').write_text(json.dumps(results,indent=2))
