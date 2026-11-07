# Quasi-static roadmap implementation and validation — 2026-11-07

## GPU finding and optimization

The original CuPy implementation used many Python-dispatched indexing, reduction, einsum and transcendental operations per bounded tile. A diagnostic profile on the 5,083-triangle CM5 In3.Cu mesh recorded 820 evaluations, 3,160 far-integrator calls, 9,480 einsums and 26,735 sums. Backend evaluate time was 2.98 s out of 3.72 s instrumented total; explicit download time 0.081 s and final queued-device waits 0.016 s. These are host profiling/synchronization measurements, not a GPU hardware utilization trace: implicit synchronization and work overlap prevent interpreting them as pure device compute time. They show that bulk PCIe download bandwidth is not the dominant explanation.

A new fused float64 CUDA/HIP kernel integrates each triangle pair in one thread with local quadrature reductions. One launch handles each complete tile; geometry stays uploaded and dense assembly stays on the host. All near/far formulas and pair ownership remain unchanged. The portable host-array analytic formula remains as an independent reference. This avoids intermediate device quadrature arrays and thousands of small operation chains.

Controlled, sequential CM5 In3.Cu results (three samples, median, OPENBLAS_NUM_THREADS=1; projection and solve excluded):

| Mesh | Previous CuPy seconds | Fused CuPy seconds | OpenMP 8 seconds |
|---|---:|---:|---:|
| current | 0.344 | 0.199 | 0.103 |
| isotropic-fine | 3.063 | 1.553 | 0.752 |

The fused GPU is about twice as fast on the fine ground mesh, but still about twice as slow as eight-worker OpenMP. Original and new timings come from separate runs, so the speedup has host-load uncertainty. Raw results are cm5-fused.json; prior measurements are in ../cm5-mesh-2026-11-07/results.json. Synthetic magnetic/scalar samples are also retained, though those runs overlapped correctness tests and should not be treated as controlled speed measurements. Both GPU and CPU use float64. Classification, reciprocal host writes, projection and solves remain CPU work; no complete GPU solve speedup is claimed. Further work would measure device occupancy and tune host scheduling, tile size and device-resident assembly rather than just changing mesh shape.

The post-fusion diagnostic profile is gpu-profile-fused.json/.txt: total 1.61 s, including 0.91 s inside backend evaluation, 0.76 s in final queued-device waits and 0.072 s in downloads. About 0.70 s remains outside backend evaluation for host classification/assembly and other fill work. Fusion shifts the remaining device work into an explicit asynchronous wait; these wait totals are not directly comparable to the old operation-chain profile's implicit synchronization. This explains why the faster kernel alone still does not beat OpenMP end to end.

## Roadmap delivered locally

- MQS command: `python -m mom25d.mqs`, KiCad or exported JSON input, `--describe --json`, part/net/operating-point/mesh/backend/scan controls.
- Converter discovery: inductor/IC connectivity plus input-to-ground capacitors, unique automatic selection, explicit overrides for ambiguity. Discovery is a buck input-loop heuristic and does not infer IC pin functions or arbitrary converter topologies.
- Outputs: mqs.json with copper R/L, complex dipole moments, peak H per frequency/height, settings, selection, assumptions, fill metadata and FFT convergence; standard plane/volume H dumps, figures, spectrum and exact mesh NPZ.
- GUI: Near field page with options supplied by the CLI, separate-process run/stop/log, summary, spectrum, H maps and Open fields in Viewer. A headless render is near-field-gui.png. The actual CM5 CLI output was loaded successfully into the GUI Fields view (three sources).
- Documentation: companion solver guide, backend guide, GUI README, kicad2ems roadmap and changelog updated. Implementation is tracked in the companion repositories; the parent repository pins their commits.

The source is an assumed buck input-current pulse, not an extracted switching device model. Selected capacitors' values come from the board; ESR, ESL, pulse spectrum and filament heights are explicit assumptions. Output-inductor leakage, switch-node E and inductive E are not modeled by this command.

## Correctness and real boards

- Final combined CLI/core-physics/GUI checks: 93 passed.
- Final real-GPU backend tests: 48 passed, covering magnetic/scalar fills at all three observation-refinement levels, plus identical results across different GPU tile sizes.
- GPU-driven MQS/PEEC/electrostatic regressions: 27 passed.
- Full six-layer CM5 CLI: 9,736 triangles, 85 via segments, two harmonics (500 kHz / 1 MHz), planes at 1 / 3 mm above top copper and the intervening volume. CPU and fused GPU copper R/L differ by less than 4.3e-15 peak-relative; all complex64 field dumps are identical. All summary metrics agree below 4.2e-14 peak-relative. See cm5-cpu-gpu-errors.json. CLI timings are diagnostics, not controlled performance comparisons.
- CM5 local mesh sensitivity: fine spacing 0.8 to 0.6 mm changes copper R/L by about 2%. Crop margin 3 to 4 mm changes them by at most 0.52%. These tests do not establish convergence. Full source and settings are in the output folders and previous CM5 mesh report; the installed CM5 source differs in hash from the upstream pinned benchmark despite reproducing its triangle count.
- Jetson AGX Thor: all eight expected regulator/inductor pairs discovered. Each cropped input-loop model completed at 500 kHz with a 3 mm-high converged FFT plane. Settings: dmax 2 mm, local 1 mm, crop margin 2 mm, input capacitors within 4 mm, seven scan points/axis, default assumed waveform and part parasitics. Explicit input supplies resolve bias/enable ambiguity. These are coarse execution smoke tests, not a converged physical validation.

| Jetson converter | Input supply | Triangles | Copper R at 500 kHz, mΩ | Copper L at 500 kHz, nH |
|---|---|---:|---:|---:|
| U11 | VCC | 8663 | 0.6290 | 0.1522 |
| U12 | VCC | 9312 | 0.6503 | 0.1572 |
| U13 | VCC | 10045 | 1.2585 | 0.4002 |
| U65 | VCC_IN | 7362 | 0.5953 | 0.1391 |
| U69 | +5V | 4251 | 1.4438 | 0.3981 |
| U7 | +5V | 3720 | 2.9641 | 0.6181 |
| U75 | VCC | 7755 | 1.2386 | 0.3847 |
| U8 | VCC | 6457 | 1.1721 | 0.3747 |

## Remaining roadmap work

Real-board crop/mesh convergence, broader waveform/package models and physical probe/hardware validation remain. The 10x overall real-board speed target is not demonstrated. Whole-board compression and iterative static solves remain conditional research work: these cropped converter models run without them. The other roadmap areas (line-section solver and full-wave multilayer improvements) were not part of this quasi-static pass. Later backlog items such as config-driven multi-rail PDN, load fields and extracted mounting inductance remain unchanged.

Reproduce GPU profiling with profile_gpu.py, controlled CM5 layer timing with cm5_fused.py, and the eight Jetson checks with jetson_check.py. Scripts use the installed KiCad demos and the existing editable Python environment; host GPU access is required for CuPy. manifest.json records base revisions and source hashes; the source hashes identify the implementation tested before committing. Regenerated board JSON caches are excluded from version control; the scripts recreate them from the installed KiCad demos.
