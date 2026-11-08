"""Refine the slotted return; compare the same source and field sample points."""
from pathlib import Path
import importlib.util
import json
import time
from types import SimpleNamespace

import numpy as np

root = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('demo', root.parents[1]/'pcbqs/tools/nearfield_demo.py')
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)
args = SimpleNamespace(dmax=1.2, fine=.3, backend='openmp', workers=8)
started = time.perf_counter()
q = demo.build_model('slot', args, 'peec_slab1')
r = q.solve([demo.FSW, 60*demo.FSW])
metrics = demo.electrical_metrics(q, r)
assert max(metrics['power_balance_relative']) < 1e-6
assert max(metrics['charge_continuity_relative']) < 1e-5
C, _, labels = q.capacitance_matrix()
e = np.zeros(len(C)); e[labels['U1.VIN']] = 1; e[labels['U1.PGND']] = -1
cap = 1/(e@np.linalg.solve(C, e))
with np.load(root/'full/slot/field-planes.npz') as data:
    x, y = data['x'][::2], data['y'][::2]
    baseline_H = data['H'][::2, ::2, 1, :, :][..., [0, -1]]
H, info = q.h_grid(r, [0, 1], x*1e-3, y*1e-3, [.0046], rtol=.02, return_info=True)
H = H[:, :, 0]*demo.harmonic_amps([1, 60])
base = json.loads((root/'full/slot/peec_slab1.json').read_text())
base_R = np.array(base['copper_R_ohm'])[[0, -1]]
new_R = np.array(metrics['copper_R_ohm'])
base_L = (np.array(base['copper_magnetic_L_H'])+base['copper_internal_L_H'])[[0, -1]]
new_L = np.array(metrics['copper_magnetic_L_H'])+metrics['copper_internal_L_H']
from pcbqs.mqs_layout import mesh_stats
record = dict(case='slot', coarse_fine_mm=.4, refined_fine_mm=args.fine,
              frequencies_Hz=r.f.tolist(), triangles=len(q.tris), edges=q.ne, mesh=mesh_stats(q),
              copper_R_ohm=new_R.tolist(), copper_R_relative_change=(new_R/base_R-1).tolist(),
              copper_energy_L_H=new_L.tolist(), copper_L_relative_change=(new_L/base_L-1).tolist(),
              floating_capacitance_F=float(cap.real),
              capacitance_relative_change=float(cap.real/base['floating_capacitance_F']['real']-1),
              H3mm_peak_relative_change=(np.max(np.linalg.norm(H, axis=2), axis=(0, 1))/np.max(np.linalg.norm(baseline_H, axis=2), axis=(0, 1))-1).tolist(),
              H3mm_complex_relative_max_change=(np.max(np.linalg.norm(H-baseline_H, axis=2), axis=(0, 1))/np.max(np.linalg.norm(baseline_H, axis=2), axis=(0, 1))).tolist(),
              field_change_note='Fixed output sample points, with independently converged FFT deposition grids; H changes include mesh and deposition differences.',
              field_grid_convergence=info, power_balance_relative=metrics['power_balance_relative'],
              charge_continuity_relative=metrics['charge_continuity_relative'], seconds=time.perf_counter()-started)
(root/'mesh-sensitivity.json').write_text(json.dumps(record, indent=2)+'\n')
print(json.dumps(record, indent=2))
