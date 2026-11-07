# Quasistatic PEEC local validation — 2026-11-07

Updated checkouts:
- mom25d: `improve-quasistatic-peec`, `29d56b6d0436dd47d96178c8790d78444d138e94`
- kicad2ems: `update-quasistatic-roadmap`, `57ae2d78be9bd332d1262db1b0a0bd4daa779a40` (roadmap-only update)

Hardware: Intel Core i7-13700K, 24 logical CPUs; AMD Radeon RX 7800 XT, 16 GiB, CuPy 14.2.0 ROCm, gfx1101. Rebuilt the native core with GCC, -O3 -march=native -fopenmp. Used the existing kicad2ems/.venv editable installations. GPU runs require host device access outside the sandbox.

## Fill performance

Repository benchmark_static_fill.py, dmax=0.5 mm, 2,838 triangles, 4,028,541 unordered pairs (167,294 analytic), 16,384-pair tiles, float64. Three samples per case, median wall time including preparation and assembly, excluding projection and solves. OPENBLAS_NUM_THREADS=1. Final CPU and GPU benchmarks ran sequentially without concurrent test jobs. Speedups compare with serial NumPy on the same updated code, not the previous release. GPU samples include first-use initialization; inspect JSON for cold versus subsequent samples.

| Fill | Backend | Workers | Median seconds | Speedup vs NumPy | Max relative moment error |
|---|---|---:|---:|---:|---:|
| magnetic | numpy | 1 | 2.4349 | 1.00x | 0.00e+00 |
| magnetic | threaded | 1 | 2.4277 | 1.00x | 0.00e+00 |
| magnetic | threaded | 2 | 1.3517 | 1.80x | 0.00e+00 |
| magnetic | threaded | 4 | 0.7713 | 3.16x | 0.00e+00 |
| magnetic | threaded | 8 | 0.4900 | 4.97x | 0.00e+00 |
| magnetic | threaded | 16 | 0.4411 | 5.52x | 0.00e+00 |
| magnetic | threaded | 24 | 0.4565 | 5.33x | 0.00e+00 |
| magnetic | openmp | 1 | 0.3943 | 6.18x | 3.21e-16 |
| magnetic | openmp | 2 | 0.3090 | 7.88x | 3.21e-16 |
| magnetic | openmp | 4 | 0.2670 | 9.12x | 3.21e-16 |
| magnetic | openmp | 8 | 0.2389 | 10.19x | 3.21e-16 |
| magnetic | openmp | 16 | 0.2340 | 10.41x | 3.21e-16 |
| magnetic | openmp | 24 | 0.2346 | 10.38x | 3.21e-16 |
| magnetic | cupy | 1 | 1.0414 | 2.34x | 1.76e-16 |
| scalar | numpy | 1 | 1.5004 | 1.00x | 0.00e+00 |
| scalar | threaded | 1 | 1.5027 | 1.00x | 0.00e+00 |
| scalar | threaded | 2 | 0.8541 | 1.76x | 0.00e+00 |
| scalar | threaded | 4 | 0.5194 | 2.89x | 0.00e+00 |
| scalar | threaded | 8 | 0.3596 | 4.17x | 0.00e+00 |
| scalar | openmp | 1 | 0.3367 | 4.46x | 3.06e-16 |
| scalar | openmp | 2 | 0.2593 | 5.79x | 3.06e-16 |
| scalar | openmp | 4 | 0.2275 | 6.60x | 3.06e-16 |
| scalar | openmp | 8 | 0.2018 | 7.44x | 3.06e-16 |
| scalar | cupy | 1 | 0.5864 | 2.56x | 1.49e-16 |

OpenMP with 8 workers is a useful default here. Magnetic OpenMP thread scaling alone (1 to 8 workers) is 1.65x; most of the 10.19x gain over NumPy comes from compiled integration. Sixteen workers add only ~2% over eight; 24 add no further gain. GPU is 4.36x slower than eight-worker OpenMP for magnetic fills and 2.91x slower for scalar fills on this workload. The GPU path still performs projection and solves on the CPU; these are fill timings only. Larger geometries and tile tuning were not measured.

## Correctness and solver checks

- Targeted static, backend, MQS, PEEC, electrostatic and conductor tests: 78 passed, 1 GPU skip inside the sandbox.
- Backend tests with real host GPU access: 46 passed, including real CuPy magnetic/scalar agreement.
- MQS, PEEC and electrostatic solver tests with MOM25D_FILL_BACKEND=cupy: 27 passed in 39.99 s; see gpu-solver-tests.log.
- End-to-end CPU MQS benchmark (974 triangles): inductance relative Frobenius error 4.97e-5 against all-analytic integration; FFT field maximum relative error 0.00377 against direct Biot–Savart. See mqs.json; these individual timings overlapped another benchmark and are diagnostic, not controlled speed measurements.
- PEEC two-plate benchmark (432 triangles): capacitance-only did not build magnetic matrices; repeated excitation required zero additional factorizations, excitation-linearity error zero. See peec.json. Its individual timings overlapped another benchmark.

Raw timing samples, backend/team metadata and relative errors are in magnetic-cpu.json, magnetic-gpu.json, scalar-cpu.json and scalar-gpu.json. No source edits, commits or parent submodule-pointer commits were made. The pre-existing untracked kicad2ems-palace directory was left alone.
