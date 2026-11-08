# wpthb periodic driver simulation

This is a computed periodic steady-state demonstration, using the sample H-bridge PCB and an unloaded coil model. It does not simulate startup, a receiver, or measured gate waveforms.

## Coil and operating point

The coil is a 24 µH inductor with 110 mΩ series DCR, shunted by a capacitance derived from the 7.7 MHz self-resonant frequency:

`Cp = 1 / ((2π × 7.7 MHz)² × 24 µH) = 17.8011 pF`.

Equivalently, `Zcoil = (R + jωL) / (1 + jωCp(R + jωL))`. This is a first-order lumped fit; self-resonance alone cannot identify the real distributed capacitance or loss spectrum. DCR uses the stated maximum rather than the datasheet typical 90 mΩ. No extra AC/core loss is added: the typical Q=155 at 125 kHz corresponds to about 121.6 mΩ total equivalent series loss, not another 121.6 mΩ on top of DCR.

Reference: [Würth 760308101310 datasheet](https://www.we-online.com/components/products/datasheet/760308101310.pdf).

- VHB: 24 V, ideal stiff local supply at the VHB side of L3.
- Demonstration frequency: 110 kHz, chosen within the supplied 70–110 kHz range.
- Demonstration phase: 90°, with both legs at 50% duty. The actual phase command was not supplied.
- C25/C27/C30: 33 nF each, 99 nF combined series tank bank. C17 is DNP.
- Local DC link: C19/C24 1 µF and C20–C23 10 µF each.
- Ideal switches, zero dead time, no MOSFET Coss, body diode dynamics, or gate-driver timing.
- Capacitors have ideal values without ESR/ESL. Copper and via losses remain in the PCB model.

Finite resistance bounds the unloaded series resonance but does not guarantee a small current. The 24 µH / 99 nF tank resonates around 103.25 kHz; a receiver, component tolerances, phase control, and additional losses would materially alter the operating point. The coil's 100 W application rating is not a dissipative 100 W load.

## Method

The reduced four-layer copper mesh is the actual bridge/DC-link/tank-bank region. Five voltage ports represent four MOSFET channels and the bus feed. The passive coil impedance is included while extracting the frequency-dependent PCB port admittance. DC is solved separately with capacitors open. A periodic linear harmonic-balance system imposes zero channel voltage when each MOSFET is on and zero channel current when off. It solves every branch's harmonic currents jointly, including changes in the conduction path and PCB impedance, rather than scaling a single fixed-state field picture.

The field is reconstructed as a real vector waveform from DC and all retained complex harmonics, with a real-projected Nyquist collocation bin. The exported VTK frames are actual time samples, usable by the existing GUI's time-domain player.

`summary.json` records the operating current, loss/power balance, port reciprocity, switching boundary residual, harmonic sensitivity, and FFT field-grid refinement. A second harmonic resolution is solved for comparison; ideal switching edges are bandwidth-sensitive, so the animation is not a prediction of commutation spikes. Spatial mesh/crop convergence is not established by these checks.

## Field scope

Fields include PCB copper, vias, and local component-current filaments. **External coil and supply-feed fields are omitted**, since their three-dimensional positions and lead routing are not specified. The coil participates electrically; its artificial straight connector is explicitly excluded from the field sum. The upstream input filter and bulk capacitor network are excluded. Components are approximate visual silhouettes, not electromagnetic solids. Local part-to-copper mutual coupling, distributed electric fields, and ferrite leakage fields are not modeled.

## Outputs and reproduction

- `operating-fields.gif` / `.mp4`: time-domain PCB field magnitudes at 1 mm and 3 mm, gate state highlighting, bridge command and current traces.
- `signed-field-phases.png`: signed Hz snapshots at 1 mm, showing reversals.
- `operating-fields.png`: one animation frame.
- `phase-sweep.png`: 0° through 180° unloaded tank current.
- `time_fields.npz`: real vector fields/current waveforms and complex harmonic coefficients.
- `mqs/exc_bridge/`: 64 time-domain VTK frames plus GUI metadata.
- `port_responses_R110m_Cp17p8.npz`: cached damped-coil port responses; the old lossless cache is not used.

From the project root:

```sh
OPENBLAS_NUM_THREADS=8 kicad2ems/.venv/bin/python benchmark-results/wpthb-operational-2026-11-07/simulate.py
MPLCONFIGDIR=/tmp/mqs-mpl kicad2ems/.venv/bin/python benchmark-results/wpthb-operational-2026-11-07/render.py
```

`OP_SAMPLES` selects an even collocation sample count (default 128); changing the electrical model requires invalidating its cached port responses. Original KiCad design files are unchanged.

## Results for the demonstration

| Quantity | Result |
|---|---:|
| Coil winding peak current | 10.7245 A |
| Coil winding RMS current | 7.7123 A |
| Supply input power | 6.7538 W |
| Winding DCR loss | 6.5427 W |
| PCB copper/via loss | 0.2077 W |
| Power imbalance | 0.0502 % |
| Fundamental versus independent lumped tank | 0.2185 % difference |
| PCB peak H on the sampled 1/3 mm planes | 1217.94 A/m |

The 64-versus-128 collocation comparison gives 2.56% maximum winding-current difference, normalized by the fine peak current. The corresponding vector-field difference is 8.76% of the global component peak away from switching edges, and 41.44% including edges. Therefore the animation illustrates the periodic field distribution and commutation paths; its edge peaks are not converged predictions. The FFT field-grid tolerance passed, but that is distinct from temporal bandwidth and spatial mesh convergence.

See `validation.json` for the numerical checks. The winding loss estimate uses DCR alone and omits extra AC/core loss. No useful receiver power is delivered in this unloaded model.

## EMC screening of the saved solution

`emc_screening.py` produces `emc-screening.png` and `.json`. Each harmonic's reported magnitude is the maximum over phase of its real vector field, then the maximum over the sampled top+1 mm plane. Different harmonics can peak at different positions. These are magnetic near-field estimates, not receiver spectra or limits comparisons.

Approximate spatial peaks are 779 A/m at 110 kHz, 441 A/m at 220 kHz, and 169 A/m at 440 kHz. The fundamental is strongest along the upper output-return region; the even harmonics concentrate around the MOSFET area. A nearly sinusoidal coil current therefore does not imply a nearly sinusoidal local PCB field: individual switching branches carry commutated currents. Higher-frequency amplitudes remain sensitive to the ideal switching approximation and finite bandwidth.

The useful inference is to investigate magnetic pickup into nearby gate/sense loops and compare changes to the local DC-link/half-bridge return paths. Common-mode and overall conducted/radiated performance are not resolved. The 17.8 pF coil capacitance is across its terminals, not a model of coil-to-chassis/earth coupling. At 90 degrees, ideal bridge switch-node common-mode voltage steps between 0, 12 and 24 V; reducing differential output with phase shift does not eliminate switch-node slew.

Next modeling steps for EMC: realistic commutation including finite edge times/deadtime/Coss; capacitor ESR/ESL and package inductance; coil/receiver/lead positions; parasitic capacitances to chassis/earth; the upstream filter and supply harness with a defined LISN/measurement impedance. Then compare spectra and induced voltage in specified victim loops, and validate using near-field/current probes. A formal pass/fail assessment additionally needs the applicable product standard, measurement geometry, detector and bandwidth.

References: [TI on hot loops, switching nodes and sensitive traces](https://www.ti.com/document-viewer/lit/html/SSZTAE5/GUID-1402DA8B-73DB-44B4-B203-A3AF307A6C45), [TI on common-mode current from parasitic capacitance and switch-node slew](https://www.ti.com/document-viewer/lit/html/SSZTDB0/GUID-F2BFFA80-CD93-4715-95EB-FD96657DE0DE), [Rohde & Schwarz on near-field EMI debugging](https://www.rohde-schwarz.com/us/products/test-and-measurement/essentials-test-equipment/rs-essentials-digital-oscilloscopes/understanding-emi-debugging_254516.html).
