# CM5 converter ground-plane mesh check

2026-11-07. Actual KiCad CM5 Minima demo from /usr/share/kicad/demos/cm5_minima/CM5_MINIMA_3.kicad_pcb, SHA-256 recorded in results.json. The source hash differs from the pinned upstream benchmark; the default mesh nevertheless reproduces its 9,736 triangle count. U702/C704/C705/C706 +5V/GND input-loop crop, same 3 mm margin and terminal constraints as tools/benchmark_converter.py.

The MQS mesh_sheet path already uses ncross=1 (no edge grading rings). Current settings use dmax=1.5 mm away from the terminal extent plus 1 mm, and dmax_fine=0.6 mm inside it. The comparison uses 0.6 mm everywhere plus Triangle q30 quality refinement, preserving via, pad, fine-region and copper constraints. This changes both size and shape; it does not isolate either effect. Acute input constraints can limit the angle guarantee. Nominal dmax sets boundary spacing and area limits, not a strict maximum triangle edge length.

The pictures compare F.Cu, In3.Cu and B.Cu. In3.Cu is the largest internal-layer mesh in the default crop and is the layer used for fill timings. Full multilayer solves were not timed.

| Mesh | Full crop triangles | In3.Cu triangles | In3 max edge (mm) | In3 95th-percentile max edge (mm) | In3 95th-percentile aspect ratio | CPU OpenMP 8 fill (s) | GPU fill (s) |
|---|---:|---:|---:|---:|---:|---:|---:|
| current | 9736 | 1650 | 2.078 | 1.505 | 10.54 | 0.098 | 0.344 |
| isotropic-fine | 33442 | 5083 | 0.789 | 0.593 | 1.84 | 0.719 | 3.063 |

Three samples per backend, sequential jobs, median wall time, OPENBLAS_NUM_THREADS=1, i7-13700K and RX 7800 XT, CuPy 14.2.0 ROCm. Timings include static magnetic moment filling/assembly and exclude RWG projection/solve. Both CPU and GPU run on identical meshes. Worst error against same-mesh serial NumPy is below 9e-16. Samples include cold GPU startup; see results.json for each sample.

The finer mesh removes the visibly large plane triangles, but GPU filling still loses to eight-worker OpenMP (4.26x on the fine In3 layer). Full crop triangle count rises 3.43x, implying about 11.8x as many dense triangle pairs/storage if assembled together. No real-board mesh/crop convergence or physical-current accuracy claim follows from these backend checks. The earlier coarse/fine CM5 study's 3.8% L variation remains a reason to run convergence checks, not proof the coarse planes are sufficient or wrong. Prefer local refinement around the converter/return-current path followed by R/L and field convergence checks over adopting uniform fine meshes as a default.

Reproduction: OPENBLAS_NUM_THREADS=1 kicad2ems/.venv/bin/python benchmark-results/cm5-mesh-2026-11-07/check.py with GPU device access. Exact meshes and layer labels are saved in *-mesh.npz. No production mesher or solver settings were changed.
