# Isotropic copper mesh: CPU/GPU comparison

Measured on 2026-11-07, i7-13700K and Radeon RX 7800 XT (CuPy 14.2.0/ROCm). Same mom25d revision 29d56b6 as the previous benchmark.

Copper: 20 x 10 mm sheet. The graded case uses the existing mesh_polygons defaults with 0.5 mm dmax/w_ref. The isotropic case uses constrained Delaunay Triangle pq30a0.125Q in mm units: no edge rings, minimum angle 30 degrees, maximum triangle area 0.125 mm² (same area cap as the graded case). Meshing is CPU-only for both; this tests GPU matrix filling on the resulting meshes, not GPU meshing.

Three serially executed samples per backend/mode, median wall seconds; OPENBLAS_NUM_THREADS=1, 16,384-pair tiles. Geometry preparation, transfers and host assembly are included; RWG projection and solves are excluded. GPU first-use initialization is included in samples; median usually reflects the warm behavior. Raw samples and counters are in results.json; benchmark.py reproduces the run, and the exact meshes are saved as NPZ files.

## Mesh quality

| Mesh | Triangles | Minimum angle | Median minimum angle | 95th percentile edge aspect ratio | Meshing seconds |
|---|---:|---:|---:|---:|---:|
| graded | 2838 | 3.85° | 43.25° | 12.80 | 0.0025 |
| isotropic | 2501 | 30.04° | 46.01° | 1.76 | 0.0007 |

Both meshes preserve the full 200 mm² copper area. See meshes.png for the triangulations.

## Fill timings

| Mesh | Fill | Backend | Workers | Median seconds | Million pairs/s | Relative error vs same-mesh NumPy |
|---|---|---|---:|---:|---:|---:|
| graded | magnetic | numpy | 1 | 2.4512 | 1.64 | 0.00e+00 |
| graded | magnetic | threaded | 8 | 0.4874 | 8.27 | 0.00e+00 |
| graded | magnetic | openmp | 1 | 0.3981 | 10.12 | 3.21e-16 |
| graded | magnetic | openmp | 8 | 0.2487 | 16.20 | 3.21e-16 |
| graded | magnetic | cupy | 1 | 1.0105 | 3.99 | 1.76e-16 |
| graded | scalar capacitance | numpy | 1 | 1.3205 | 3.05 | 0.00e+00 |
| graded | scalar capacitance | threaded | 8 | 0.2830 | 14.23 | 0.00e+00 |
| graded | scalar capacitance | openmp | 1 | 0.3354 | 12.01 | 3.06e-16 |
| graded | scalar capacitance | openmp | 8 | 0.1966 | 20.49 | 3.06e-16 |
| graded | scalar capacitance | cupy | 1 | 0.5923 | 6.80 | 1.49e-16 |
| isotropic | magnetic | numpy | 1 | 1.7232 | 1.82 | 0.00e+00 |
| isotropic | magnetic | threaded | 8 | 0.3367 | 9.29 | 0.00e+00 |
| isotropic | magnetic | openmp | 1 | 0.3135 | 9.98 | 3.06e-16 |
| isotropic | magnetic | openmp | 8 | 0.2020 | 15.49 | 3.06e-16 |
| isotropic | magnetic | cupy | 1 | 0.7415 | 4.22 | 1.72e-16 |
| isotropic | scalar capacitance | numpy | 1 | 1.0245 | 3.05 | 0.00e+00 |
| isotropic | scalar capacitance | threaded | 8 | 0.2336 | 13.39 | 0.00e+00 |
| isotropic | scalar capacitance | openmp | 1 | 0.2652 | 11.80 | 3.01e-16 |
| isotropic | scalar capacitance | openmp | 8 | 0.1554 | 20.13 | 3.01e-16 |
| isotropic | scalar capacitance | cupy | 1 | 0.4242 | 7.38 | 1.47e-16 |

Magnetic: isotropic GPU 0.741 s, 1.36x faster than graded GPU; 2.32x faster than same-mesh serial NumPy, but 3.67x slower than same-mesh eight-worker OpenMP.

Capacitance: isotropic GPU 0.424 s, 1.40x faster than graded GPU; 2.42x faster than same-mesh serial NumPy, but 2.73x slower than same-mesh eight-worker OpenMP.

Isotropic meshing improves elapsed time for both CPU and GPU, but changes triangle/pair count as well as pair geometry. The pairs/s column helps distinguish throughput from workload reduction; it does not isolate near/far integration cost. This experiment does not establish equal physical accuracy between meshes: removing edge refinement can worsen current/charge resolution at copper boundaries. Cross-backend numerical errors compare each backend against NumPy on the identical mesh, not one mesh against the other. No real-board convergence or end-to-end solve comparison was performed.

The GPU remains slower than OpenMP here. Isotropic triangles alone do not close the gap. No solver or mesher defaults were changed.
