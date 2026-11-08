# wpthb quasi-static circuit/path run — 2026-11-07

Completed actual mom25d MQS solves on the imported H-bridge PCB at 70, 80, 90, 100, 103.252 and 110 kHz, for both diagonal and both freewheel conduction states. VHB is recorded as approximately 24 V, as supplied by the user. Sources are normalized to a 1 A **peak** coil-port current from TP15 (coil A, /HL_AC) to TP14 (coil B, /HR_SW) in each topology. All four topologies use the same current reference; reverse the phasor to reverse current. This is a fixed-conduction-state characterization, not a phase-shift steady-state switching simulation.

## Model and scope

The first preflight including upstream input filter/bulk circuitry produced 39,858 triangles and an estimated 126 GB dense working set. That run was stopped before matrix filling. The completed model crops around the bridge, series capacitors and local VHB capacitors, excluding L3/VBUS and upstream bulk capacitors. The input-boundary approximation has not been quantified. The run has 13,490 triangles, 18,188 RWG edges, 267 via segments, four layers and 8,618 loop unknowns; all retained geometry comes from the actual PCB. Mesh spacing is nominal 3 mm, locally 1.6 mm, with real pads/via constraints. See preflight.json.

Included: explicit copper returns, copper/via coupling, nominal C19–C24 local bus decoupling, nominal C25/C27/C30 series bank, two-face slab copper loss and DC via loss. Conducting MOSFET channels are ideal zero-ohm branches; other channels are open. Capacitor ESR/ESL are zero because values were not supplied. No diode conduction, Coss, dead time or nonlinear commutation is modeled. Local lumped-part fields are straight in-plane filaments; part/copper mutuals are omitted by the solver.

The external coil is represented electrically in the reported total series impedance by 24 µH plus a constant 0.12161 Ω small-signal loss anchor from Q=155 at 125 kHz. This is not a measured broadband/current-dependent coil model. Receiver-reflected loading is absent. The external source branch is explicitly zeroed **only for field evaluation** so the solver does not invent a straight wire between the coil pads as the physical external coil. Solved circuit currents are retained unchanged for KCL and impedance. Exported fields include PCB sheets, vias and local lumped filaments; they exclude the external coil and leads. No dipole moment is inferred for this open, partial field-source region.

## Results at 100 kHz

Copper contributions exclude the coil's 24 µH and its loss, capacitor losses and MOSFET channel loss. They are source-referred contributions for each test topology, not complete measured commutation-loop parasitics.

| Conduction state | Copper R (mΩ) | Copper L (nH) | Peak H at 1 mm (A/m per A) | Peak H at 3 mm (A/m per A) |
|---|---:|---:|---:|---:|
| diagonal_Q2_Q3 | 3.911 | 4.837 | 111.55 | 25.89 |
| diagonal_Q1_Q4 | 3.367 | 3.309 | 109.88 | 22.46 |
| freewheel_low_Q3_Q4 | 3.067 | 3.651 | 104.03 | 22.02 |
| freewheel_high_Q1_Q2 | 3.423 | 3.310 | 112.25 | 22.64 |

The 24 V ideal bridge has a fundamental peak-voltage range of 0–30.56 V as leg-to-leg phase shift goes from 0 to 180 degrees (50% leg duty before dead time). This specifies available drive voltage, not operating coil current. Phase shift, reflected receiver impedance and nonlinear commutation are still unspecified; the tabulated normalized fields should not be scaled directly by 24 V. The nominal 24 µH / 99 nF tank resonance is about 103.25 kHz before board/load corrections.

## Numerical checks

- Maximum KCL residual over all states: 5e-16 A for the 1 A excitation.
- FFT deposition converged to the 2% per-height/per-frequency target in every state. Maximum sampled direct-Biot–Savart comparison: 0.54% of peak at 100 kHz.
- Q2/Q3 refinement from 1.6 to 1.4 mm local spacing increases mesh size to 14,169 triangles. Copper R changes 1.02%, L 1.23%, and peak H across heights at most 0.52%. Maximum complex field change over the fixed grid is 4.12% of peak. These two meshes do not establish convergence, and the other states/crop have not been refined.

## Outputs and reproduction

- state-field-overlays.png: four normalized state maps at 100 kHz, 1 mm above copper, common colour range.
- impedance-sweep.png: source-referred copper R/L and board-plus-coil reactance.
- summary.json: all frequencies, branch currents, assumptions, normalized H peaks and numerical checks.
- Each state folder has the layout, standard layer mesh, current arrays and standard H plane/volume dumps, readable through the GUI Viewer. The volume uses height samples 1/3/5 mm. Fields are complex phasors, with the complete frequency axis retained.
- fine-check/ and mesh-comparison.json retain the single-state refinement comparison.

Run from the project root:

    OPENBLAS_NUM_THREADS=8 MOM25D_FILL_THREADS=8 kicad2ems/.venv/bin/python benchmark-results/wpthb-qs-2026-11-07/run_qs.py
    QS_OUT=fine-check QS_FINE=1.4 QS_FREQS=100000 QS_CASES=diagonal_Q2_Q3 OPENBLAS_NUM_THREADS=8 kicad2ems/.venv/bin/python benchmark-results/wpthb-qs-2026-11-07/run_qs.py
    kicad2ems/.venv/bin/python benchmark-results/wpthb-qs-2026-11-07/plot_results.py

The original schematic and PCB remain unchanged. These outputs and scripts are local, uncommitted work. Model fidelity remains limited by mesh/crop, imported stack conventions, package approximations, ideal device/capacitor models, unknown receiver load and absent mounted coil geometry.
