"""Check saved FFT fields against independent direct Biot-Savart evaluation."""
from pathlib import Path
import importlib.util
import json
from types import SimpleNamespace

import numpy as np


root = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('demo', root.parents[1]/'pcbqs/tools/nearfield_demo.py')
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)
checks = {}
for case in ['good', 'far', 'slot']:
    folder = root/'full'/case
    args = SimpleNamespace(dmax=1.2, fine=.4, backend='openmp', workers=8)
    q = demo.build_model(case, args, 'peec_slab1')
    with np.load(folder/'solution.npz') as data:
        assert np.array_equal(q.nodes, data['nodes']) and np.array_equal(q.tris, data['tris'])
        r = SimpleNamespace(f=data['frequencies'], i=data['currents'])
    with np.load(folder/'field-planes.npz') as data:
        ix = np.arange(0, len(data['x']), 18)
        iy = np.arange(0, len(data['y']), 13)
        heights = (demo.Z_TOP+data['heights'])*1e-3
        x, y, z = np.meshgrid(data['x'][ix]*1e-3, data['y'][iy]*1e-3, heights, indexing='ij')
        pts = np.stack([x, y, z], -1).reshape(-1, 3)
        fi = [0, len(r.f)-1]
        direct = q.h_field(r, fi, pts).reshape(len(ix), len(iy), len(heights), 3, len(fi))
        direct *= demo.harmonic_amps(r.f[fi]/demo.FSW)
        grid = data['H'][ix][:, iy][..., fi]
    errors = np.max(np.linalg.norm(grid-direct, axis=3), axis=(0, 1))/np.max(np.linalg.norm(direct, axis=3), axis=(0, 1))
    assert np.isfinite(errors).all() and errors.max() < .03, (case, errors)
    from pcbqs.mqs_layout import mesh_stats
    checks[case] = dict(frequencies_Hz=r.f[fi].tolist(), points_per_frequency=len(pts),
                        heights_mm=[1, 3, 10], relative_error_by_height_frequency=errors.tolist(), mesh=mesh_stats(q))
    print(case, 'direct/FFT maximum relative field error', errors.max())
(root/'field-validation.json').write_text(json.dumps(checks, indent=2)+'\n')
