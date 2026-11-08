# Coupled wpthb driver: operational circuit and field inference

Implemented in the companion mom25d and GUI worktrees. The new **Circuit** page and
`python -m mom25d.power_circuit` support editable R/C/L component types and per-part
parasitics, ideal/smooth-switch/NMOS/VDMOS/vendor-subcircuit alternatives, electrical
startup, and periodic PCB magnetic-field inference from adaptive-step terminal
currents. See ../../mom25d/docs/power-circuit.md for the schema and modeling limits.

## Selected comparison

User-selected assumptions: 24 V source; existing primary 24 µH / 99 nF; secondary
assumed to be another identical 24 µH coil, k=0.4. The secondary series capacitor is
tuned independently at 90 and 110 kHz. An AC-equivalent resistor maximizes
sinusoidal **link efficiency**; bridge phase then targets actual transient load
power. No rectifier or fixed DC output voltage is modeled.

The primary and secondary include 110 mΩ DCR and 17.801 pF SRF capacitance. An
additional parallel core conductance is fitted to Q=155 at 125 kHz, approximately
30.77 kΩ per winding; holding this conductance constant is an explicit passive
extrapolation from one small-signal datum. Default transistor/parasitic parameters
are illustrative, not a calibrated model of the installed MOSFET.

The input includes source R/L, R9=5 mΩ, CA1–CA4=22 µF each, L3=5.6 µH with assumed
30 mΩ DCR, and the local 42 µF DC link, with per-capacitor ESR/ESL. All selected
parameters are in `model.json`. CE alternatives and C17 remain omitted/DNP.

| Target W | f kHz | Actual AC W | Phase ° | Primary RMS A | Secondary RMS A | Electrical efficiency % |
|---:|---:|---:|---:|---:|---:|---:|
| 5 | 90 | 4.995 | 39.554 | 1.0215 | 0.9405 | 92.302 |
| 10 | 90 | 9.998 | 55.788 | 1.4353 | 1.3307 | 92.894 |
| 20 | 90 | 20.081 | 81.328 | 2.0180 | 1.8859 | 93.278 |
| 30 | 90 | 29.994 | 103.905 | 2.4566 | 2.3048 | 93.438 |
| 5 | 110 | 4.977 | 36.236 | 0.9119 | 0.8498 | 91.997 |
| 10 | 110 | 9.973 | 50.463 | 1.2858 | 1.2029 | 92.969 |
| 20 | 110 | 19.950 | 72.093 | 1.8104 | 1.7013 | 93.634 |
| 30 | 110 | 29.912 | 90.817 | 2.2112 | 2.0832 | 93.924 |

Efficiency includes the modeled electrical source and net ideal gate-source power;
it excludes practical driver IC/logic consumption and receiver rectifier/DC losses.
Input-filter stored-energy drift is controlled by the final-cycle repeatability
check. Individual component terminal powers can be negative because of transferred
power or changing stored energy; they must not all be interpreted as dissipation.

## Frequency behavior

- Receiver tuned at 90 kHz: C₂=130.279 nF, Rload=5.6499 Ω. Linear link-efficiency estimate 95.435%. With this receiver capacitor/load held fixed, the loaded power-transfer peaks are at 120.33 kHz; input reactance crosses zero at 118.34 kHz.
- Receiver tuned at 110 kHz: C₂=87.205 nF, Rload=6.8986 Ω. Linear link-efficiency estimate 96.150%. With this receiver capacitor/load held fixed, the loaded power-transfer peaks are at 93.81, 126.05 kHz; input reactance crosses zero at 96.34 kHz.

These are fundamental linear-link frequency sweeps, not complete nonlinear
ngspice sweeps at every frequency. Operating frequency remains the commanded
90 or 110 kHz. The circuit's resonances move when the receiver is retuned; a
frequency change alone does not alter an otherwise fixed linear circuit's poles.
Power-transfer peaks and zero input reactance are different conditions.

## Validation

- All eight delivered powers are within 0.5% of target.
- Final-cycle waveform repeatability is below 0.5%; slow input-filter current was
  the limiting settling check, rather than the winding currents.
- Worst terminal power-balance error is 0.000660%.
- The PCB has 13,528 triangles on four layers and 24 independent terminal ports.
  A PSD-constrained Foster fit is pruned within a 3% sampled impedance-error
  budget, preserving passivity. Independent harmonic checks reach 3.083%.
- At 110 kHz / 30 W, halving the maximum timestep changes load power by 0.00535%
  and primary RMS current by 0.00136%.
- Real-vector/DC reconstruction, FFT field-grid convergence and the 64-frame VTK
  round-trip passed for all cases. See `validation.json` and
  `copper-harmonic-validation.json`.

The original accepted electrical netlists were replayed with only an added
adaptive-current export. Seven replayed electrical results are numerically
identical. The 110 kHz/30 W replay also halves the timestep and provides the
sensitivity check. Each case retains its replay netlist/log/validation.

Fourier coefficients are integrated directly from adaptive-step, piecewise-linear
terminal currents with four-point quadrature. Display samples alone produce
2–23% differences in retained coefficient-vector norm in these cases, due to
narrow switching pulses. They are therefore used only for display. The field band
retains 16 harmonics: 1.44 MHz at 90 kHz and 1.76 MHz at 110 kHz. Approximately
4.6–13.6% of total port AC-current mean-square lies outside this field band.
That fraction is not an EMC error bound; high-frequency emissions can depend
strongly on the omitted spectrum.

The numerical checks do not establish spatial mesh/crop convergence, device-model
accuracy, large-signal coil/core loss, thermal behavior, or EMC compliance.

## Field scope and startup

Field maps include local PCB copper and vias. Artificial terminal connectors are
excluded. The input filter is present electrically; upstream filter copper,
external primary/secondary coils, leads, packages, gate circuitry, ferrite leakage
and environment/common-mode coupling are not field-modeled. k alone does not
supply the missing geometric information.

`electrical-startup.png` shows a separate 24 V / 100 µs ramp at the accepted
110 kHz / 10 W phase setting, using ideal interconnects but the same electrical
filter and part parasitics. It is an electrical startup demonstration, not a
closed-loop startup control simulation or a startup field calculation.

## Files

- `coupled-comparison.png`: currents, phase and electrical efficiency.
- `frequency-response.png`: linear loaded transfer and input reactance.
- `electrical-waveforms.png`: settled bridge, winding and bus waveforms.
- `coupled-fields.gif` / `.png`: 30 W comparisons at both frequencies.
- `gui-circuit.png` / `gui-fields.png`: the working native GUI.
- `power-circuit.json`, `model.json`, `validation.json`: complete results/settings.
- Each `<frequency>kHz_<power>W` folder contains a netlist, logs, waveform NPZ,
  adaptive raw current export, port spectrum, metrics, field-inference checks,
  mesh/layout and standard time-domain VTK frames.

## Reproduction

From the project root, with ngspice on PATH:

```sh
OPENBLAS_NUM_THREADS=8 kicad2ems/.venv/bin/python -m mom25d.power_circuit \
    benchmark-results/wpthb-coupled-2026-11-07/model.json \
    --board benchmark-results/wpthb-inspection-2026-11-07/board.json \
    --out /tmp/wpthb-coupled-reproduction --copper --fields
```

The benchmark helpers split independent electrical cases, copper transfer
extraction and adaptive export while developing the workflow. The public CLI
now performs the export/inference/report sequence itself. Model changes invalidate
its case caches; original KiCad files remain unchanged.

Software checks: 34 relevant backend tests and 50 GUI/near-field tests passed. A public CLI electrical smoke run at 110 kHz / 5 W completed and generated its comparison report. Full eight-case validation is recorded separately in validation.json.
