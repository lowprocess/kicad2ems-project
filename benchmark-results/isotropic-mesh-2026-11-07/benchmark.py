"""Run from project root with kicad2ems/.venv/bin/python; GPU device access required."""
import json
import time
from pathlib import Path
import numpy as np
import triangle
from shapely.geometry import box
from mom25d.geo import mesh_polygons
from mom25d.static import static_moments
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

out = Path(__file__).resolve().parent
report = {'geometry_mm': [20, 10], 'repeat': 3, 'chunk': 16384, 'meshes': []}
fig, axes = plt.subplots(1, 2, figsize=(12, 4))
for ax, name in zip(axes, ['graded', 'isotropic']):
    start = time.perf_counter()
    if name == 'graded':
        nodes, tris, _ = mesh_polygons(box(0, 0, .02, .01), .0005, .0005)
    else:
        # mm units keep Triangle's area switch free of exponent notation.
        t = triangle.triangulate({'vertices': np.array([[0.,0.],[20.,0.],[20.,10.],[0.,10.]]),
                                  'segments': np.array([[0,1],[1,2],[2,3],[3,0]])}, 'pq30a0.125Q')
        nodes, tris = t['vertices']*.001, t['triangles']
    elapsed = time.perf_counter()-start
    v = nodes[tris]
    cross = np.cross(np.pad(v[:,1]-v[:,0], ((0,0),(0,1))), np.pad(v[:,2]-v[:,0], ((0,0),(0,1))))[:,2]
    tris[cross < 0] = tris[cross < 0][:,[0,2,1]]
    lengths = np.linalg.norm(v-np.roll(v,1,axis=1),axis=2)
    area = abs(cross)/2
    angles = []
    for i in range(3):
        a, b = v[:,(i+1)%3]-v[:,i], v[:,(i+2)%3]-v[:,i]
        angles.append(np.degrees(np.arccos(np.clip((a*b).sum(1)/(np.linalg.norm(a,axis=1)*np.linalg.norm(b,axis=1)),-1,1))))
    stats = dict(name=name, triangles=len(tris), meshing_s=elapsed,
                 area_mm2=float(area.sum()*1e6), min_angle_deg=float(np.min(angles)),
                 median_min_angle_deg=float(np.median(np.min(angles,axis=0))),
                 edge_aspect_ratio_p95=float(np.percentile(lengths.max(1)/lengths.min(1),95)),
                 cases=[])
    np.savez(out/f'{name}-mesh.npz', nodes=nodes, tris=tris)
    ax.triplot(nodes[:,0]*1000,nodes[:,1]*1000,tris,lw=.25)
    ax.set(title=f'{name}: {len(tris)} triangles',xlabel='mm',ylabel='mm',aspect='equal')
    for scalar in [False, True]:
        ref = static_moments(nodes,tris,np.zeros(len(tris)),backend='numpy',scalar_only=scalar)
        for backend, workers in [('numpy',1),('threaded',8),('openmp',1),('openmp',8),('cupy',1)]:
            samples, error = [], 0.
            for _ in range(3):
                start = time.perf_counter()
                result, info = static_moments(nodes,tris,np.zeros(len(tris)),backend=backend,workers=workers,
                    chunk=16384,scalar_only=scalar,return_info=True)
                samples.append(time.perf_counter()-start)
                for a,b in zip(ref[1:],result[1:]):
                    error=max(error,float(np.linalg.norm(a-b)/np.linalg.norm(a)))
                del result
            case=dict(info,seconds_samples=samples,seconds_median=float(np.median(samples)),max_relative_moment_error=error)
            stats['cases'].append(case)
            print(name,scalar,backend,workers,case['seconds_median'],error,flush=True)
        del ref
    report['meshes'].append(stats)
    (out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
fig.tight_layout()
fig.savefig(out/'meshes.png',dpi=180)
