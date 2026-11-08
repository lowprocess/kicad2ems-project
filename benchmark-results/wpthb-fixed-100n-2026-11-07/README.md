# Fixed 100 nF compensation on both windings

The primary and secondary are both 24 µH, with fixed 100 nF series compensation,
k=0.4 and a 24 V bus. The receiver's AC-equivalent resistance is selected ONCE
for maximum sinusoidal link efficiency near the uncoupled resonance, then held
fixed at 6.445151 Ω. Neither the receiver capacitor nor the load is retuned during
these frequency changes.

The hypothetical primary bank is three 33.333 nF parts. The original board's
three 33 nF parts (99 nF total) and all KiCad source files remain unchanged.
The previous generic VDMOS, winding DCR/SRF/core-loss model, capacitor parasitics,
source and input filter remain present. This comparison uses ideal PCB
interconnects; the earlier broadband copper equivalent/field solve is not rerun.
The receiver is an AC resistor, without rectifier or DC regulation.

## Resonance and frequency sweep

The uncoupled resonance is 102.734 kHz. With k=0.4, the lossless identical-tank mode
frequencies are approximately 86.826 and 132.629 kHz (`f0/sqrt(1±k)`). These are not
the loaded maximum-power frequencies. The lossy fundamental-link sweep with
this fixed load has power peaks near 92.30, 123.05 kHz. Input reactance, maximum efficiency
and maximum delivered power are distinct optimization targets.

At full 180-degree bipolar drive, the fundamental estimate predicts about
94.3 W at 90 kHz and 72.4 W at 110 kHz. These continuous curves are linear-link
predictions, not a dense nonlinear SPICE sweep. The discrete cases below use
actual nonlinear ngspice transients and adaptive-step power measurements.

Coupled frequency splitting is also discussed in the primary research paper
[Two-coil Wireless Power Transfer System Configured in Series-Series Topology](https://arxiv.org/abs/2011.14215).

## Frequency-only power control

Bridge phase is held at 180 degrees. Frequency is adjusted on the 70–90 kHz
rising-power branch, with fixed capacitors and fixed load. Every accepted case
meets the 0.5% power target, 0.5% final-cycle repeatability and 0.01% terminal
power-balance thresholds.

| Target W | Frequency kHz | Actual W | Primary RMS A | Electrical efficiency % |
|---:|---:|---:|---:|---:|
| 5 | 73.9053 | 5.0192 | 2.4083 | 78.491 |
| 10 | 77.4500 | 9.9984 | 2.9360 | 82.507 |
| 20 | 80.7661 | 19.9988 | 3.6122 | 86.086 |
| 30 | 82.6751 | 29.9800 | 4.0855 | 87.907 |

## Phase control at fixed operating frequencies

Both capacitors and the same receiver load remain fixed. Only bridge phase
changes to target each delivered power.

| Target W | f kHz | Actual W | Phase ° | Primary RMS A | Electrical efficiency % |
|---:|---:|---:|---:|---:|---:|
| 5 | 90 | 4.9827 | 29.764 | 1.2638 | 90.241 |
| 10 | 90 | 9.9892 | 41.269 | 1.7868 | 91.089 |
| 20 | 90 | 19.9981 | 58.341 | 2.5234 | 91.617 |
| 30 | 90 | 29.9926 | 72.444 | 3.0867 | 91.806 |
| 5 | 110 | 4.9764 | 34.313 | 0.9263 | 91.454 |
| 10 | 110 | 9.9785 | 47.622 | 1.3074 | 92.466 |
| 20 | 110 | 19.9685 | 67.651 | 1.8424 | 93.165 |
| 30 | 110 | 29.9477 | 84.671 | 2.2510 | 93.477 |

With this receiver, the low-frequency, full-drive branch regulates the requested
powers but has larger primary circulating current and lower modeled electrical
efficiency. At 30 W, frequency-only operation needs about 4.09 A RMS, compared
with 2.25 A at 110 kHz with phase regulation. These figures depend on load,
coupling, losses and the uncalibrated transistor model; they are not hardware
measurements or an efficiency guarantee.

The full-drive 90–110 kHz fundamental sweep remains above the requested power
range. Frequency control within that narrow band therefore does not supply the
same 5–30 W span under these assumptions. Phase modulation, a different drive
amplitude, or a different frequency branch changes that result. The low branch
is capacitively loaded; its hard/soft commutation behavior should be evaluated
from device voltage/current during dead time rather than inferred from a power
peak alone.

## Numerical limitations

Some trial settings near 77.52 kHz aborted with ngspice timestep-too-small errors,
including alternative initialization/integration choices. The accepted 10 W
point at 77.45 kHz converged using a supply-ramp startup and 84 periods. Failed
runs were rejected, not treated as physical resonances. The discrete accepted
points are validated; continuous nonlinear solver robustness over the whole
frequency band is not established. A separate resolution check is retained
when available.

## Files and simulator support

- `fixed-cap-frequency-sweep.png`: fundamental power, link efficiency and input reactance; nonlinear control points overlaid.
- `control-comparison.png`: nonlinear primary-current/efficiency comparison.
- `model.json`: complete fixed-capacitor/load configuration.
- `linear-sweep.json`, `circuit-results.json`, `validation.json`: numerical results.
- Per-case folders retain netlists, solver logs, scalar power/current checks and histories.

The reusable simulator now honors `secondary_C_F` and `load_ohm` independently:
omitted values are tuned/matched per frequency; supplied values remain fixed.
The GUI has corresponding receiver capacitance/load controls. The primary bank
values must also be updated in `components`; `primary_C_F` is the link reference.
The fixed example is `mom25d/examples/wpthb/fixed-100n.json` in the project.

Run from the project root:

```sh
OPENBLAS_NUM_THREADS=1 kicad2ems/.venv/bin/python benchmark-results/wpthb-fixed-100n-2026-11-07/compare.py
```

Twenty focused solver/GUI checks passed, including fixed-capacitor/load
preservation across frequencies and both transient integration options.

The explicit half-timestep check at the accepted 10 W frequency-only point also failed ngspice convergence. That point is provisional and is not timestep-converged; validation.json labels the acceptance as selected-resolution only.
