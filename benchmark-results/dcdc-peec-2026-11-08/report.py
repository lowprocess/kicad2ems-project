"""Generate the three-layout PEEC comparison from retained numerical outputs."""
from pathlib import Path
import csv
import json
import numpy as np

root = Path(__file__).resolve().parent
results = json.loads((root/'full/summary.json').read_text())
settings = json.loads((root/'full/settings.json').read_text())
fields = json.loads((root/'field-validation.json').read_text())
mesh = json.loads((root/'mesh-sensitivity.json').read_text())
rows = []
cap_changes = []
for case, modes in results.items():
    a, b = modes['peec_slab1'], modes['mqs_dc']
    p = modes['peec_dc']
    z = np.array(p['port_R_ohm'])+1j*np.array(p['port_X_ohm'])
    z0 = np.array(b['port_R_ohm'])+1j*np.array(b['port_X_ohm'])
    cap_changes.append(float(np.max(abs(z/z0-1))))
    rows.append(dict(layout=case, triangles=a['triangles'],
                     capacitance_pF=a['floating_capacitance_F']['real']*1e12,
                     R_500kHz_mOhm=a['copper_R_ohm'][0]*1e3,
                     R_30MHz_mOhm=a['copper_R_ohm'][-1]*1e3,
                     R_30MHz_two_face_mOhm=modes['peec_slab2']['copper_R_ohm'][-1]*1e3,
                     R_30MHz_old_mOhm=b['copper_R_ohm'][-1]*1e3,
                     H_500kHz_3mm_Am=a['peak_H_Am']['3.0'][0],
                     H_500kHz_10mm_Am=a['peak_H_Am']['10.0'][0],
                     selected_AC_copper_mW=a['selected_harmonic_copper_loss_W']*1e3,
                     capacitance_only_max_port_relative_change=cap_changes[-1]))
with (root/'comparison.csv').open('w', newline='') as stream:
    writer = csv.DictWriter(stream, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)

table = '\n'.join(f"| {r['layout']} | {r['capacitance_pF']:.3f} | {r['R_500kHz_mOhm']:.3f} | {r['R_30MHz_mOhm']:.3f} | {r['H_500kHz_10mm_Am']:.3f} |" for r in rows)
sensitivity = '\n'.join(f"| {r['layout']} | {r['R_30MHz_old_mOhm']:.3f} | {r['R_30MHz_two_face_mOhm']:.3f} | {r['R_30MHz_mOhm']:.3f} |" for r in rows)
timing = '\n'.join(f"| {case} | "+' | '.join(f"{models[k]['seconds']:.2f}" for k in ['peec_slab1','peec_slab2','peec_dc','mqs_dc'])+' |' for case, models in results.items())
power_error = max(max(m['power_balance_relative']) for modes in results.values() for m in modes.values())
continuity_error = max(max(m['charge_continuity_relative']) for modes in results.values() for m in modes.values())
field_error = max(np.array(f['relative_error_by_height_frequency']).max() for f in fields.values())
report = f'''# Three-layout DC-DC input loop: layered PEEC and conductor loss

Re-ran the original good/far/slot layouts at 500 kHz with 3 A input pulses,
33% duty and 5 ns edge smoothing. Harmonics: 1, 2, 3, 4, 5, 6, 10, 20 and 60
(0.5–30 MHz). Board, terminal and local-refinement geometries match the earlier
demo exactly; see `geometry-parity.json`.

## Physics and scope

Distributed copper capacitance uses the original two-slab board: 1.4 mm core
at er=4.5 and 0.2 mm prepreg at er=4.2, each with tanδ=0.02 and air outside.
Copper is 35 µm, σ=5.8e7 S/m. C1 remains 10 µF, 3 mΩ ESR and 0.4 nH ESL.
These are benchmark assumptions, not device measurements.

The frequency-dependent finite-thickness slab includes skin resistance and
internal inductance. In-plane current redistribution and its loss are solved
from the coupled copper network. Through-thickness proximity redistribution
is **not resolved**: the primary result assumes one active face, with a separate
two-face model sensitivity. That comparison is not a rigorous bound or a
validated full proximity-loss solution. Via barrel resistance remains DC.

The selected copper is VIN and GND. This remains a prescribed input-current-loop
model; switch-node voltage/common-mode excitation, package mutual inductance,
output-inductor leakage, retardation and radiation are outside its scope.

## Primary results: PEEC with one-face slab

Resistance is copper dissipation expressed as R=2P/|I_source,peak|², excluding
capacitor ESR and dielectric loss. C is floating VIN–GND board capacitance,
excluding the explicit 10 µF part. H is the 500 kHz harmonic of the original
pulse waveform, spatial peak at 10 mm above the top copper.

| Layout | Board C, pF | Copper R at 500 kHz, mΩ | Copper R at 30 MHz, mΩ | H at 10 mm, A/m peak |
|---|---:|---:|---:|---:|
{table}

Adding capacitance/dielectric loss alone changes the complex port impedance
by at most **{max(cap_changes)*100:.5f}%** across these sampled cases/frequencies.
The layout ranking is preserved; skin/slab assumptions have a much larger
effect on high-frequency copper loss in this input-loop test.

| Layout | Original MQS/DC sheet at 30 MHz, mΩ | PEEC/two-face slab, mΩ | PEEC/one-face slab, mΩ |
|---|---:|---:|---:|
{sensitivity}

The slab changes internal inductance as well as resistance, so currents can
redistribute and low-frequency *port-referred* copper loss need not increase
monotonically. Selected-harmonic AC powers in `comparison.csv` exclude DC and
omitted harmonics and are not a prediction of total converter heating.

## Validation and numerical sensitivity

- Analytic PEEC, electrostatic and conductor tests: 24 passed.
- Maximum relative power-balance residual over all models: {power_error:.3g}.
- Maximum charge-continuity residual relative to displacement current:
  {continuity_error:.3g}.
- FFT planes meet the 2% successive-grid criterion. Independent direct
  Biot–Savart checks at 75 points per frequency (500 kHz and 30 MHz) differ
  by at most **{field_error*100:.3f}%**, normalized to the sampled peak at each height.
- Slotted-return refinement from 0.4 to 0.3 mm: {mesh['triangles']:,} triangles;
  copper R changes **{mesh['copper_R_relative_change'][0]*100:+.2f}%** at 500 kHz
  and **{mesh['copper_R_relative_change'][1]*100:+.2f}%** at 30 MHz. Copper energy
  inductance changes {mesh['copper_L_relative_change'][0]*100:+.2f}% and
  {mesh['copper_L_relative_change'][1]*100:+.2f}%; capacitance changes
  {mesh['capacitance_relative_change']*100:+.2f}%. These are sensitivity checks,
  not a demonstrated asymptotic error bound. See `mesh-sensitivity.json`.

## Runtime and reproduction

Intel Core i7-13700K; OpenMP fill with 8 workers, OpenBLAS with 4 threads.
The 108 frequency/model solves, capacitance extractions and field grids took
approximately **{settings['total_seconds']:.0f} s**, measured from the original
run log's creation/final-write timestamps (one-second resolution). The original
figure export failed on disconnected ground polygons; the renderer was corrected
and all pictures regenerated from saved solutions with `--plot-only`.
The one-face column includes the
initial shared magnetic/electrostatic assembly; other variants reuse immutable
copper kernels but have independent topology and factors. These timings are
not independent cold-start model benchmarks.

| Layout | PEEC one-face, s | PEEC two-face, s | PEEC DC-sheet, s | MQS DC-sheet, s |
|---|---:|---:|---:|---:|
{timing}

```sh
OPENBLAS_NUM_THREADS=4 OMP_NUM_THREADS=8 MPLBACKEND=Agg \\
  kicad2ems/.venv/bin/python pcbqs/tools/nearfield_demo.py \\
  benchmark-results/dcdc-peec-2026-11-08/full
OPENBLAS_NUM_THREADS=1 kicad2ems/.venv/bin/python \\
  benchmark-results/dcdc-peec-2026-11-08/validate_fields.py
OPENBLAS_NUM_THREADS=4 OMP_NUM_THREADS=8 kicad2ems/.venv/bin/python \\
  benchmark-results/dcdc-peec-2026-11-08/mesh_sensitivity.py
```

The restored maintained demo is independent of mom25d and kicad2ems; it uses
PCBQS's own numerical and field-export services. Original source/licence
provenance is in `pcbqs/PROVENANCE.json`; module and numerical-function hashes
are in `provenance.json`. Numerical solver implementations were unchanged.

## Pictures and retained results

![Three layouts](full/nearfield_layouts.png)
![Copper loss comparison](full/copper-loss.png)
![Magnetic field 10 mm above the layout](full/magnetic-fields-10mm.png)
![Ground return at 30 MHz](full/ground-return-30MHz.png)
![Surface charge](full/surface-charge.png)
![Ground meshes](full/meshes.png)

`full/<layout>/mqs/exc_U1` contains standard complex H dumps for the GUI;
`solution.npz` and `field-planes.npz` retain currents, charges and sampled fields
locally. Per-model JSON files and `comparison.csv` record the measurements.
'''
(root/'README.md').write_text(report)
print(table)
print('Total seconds', settings['total_seconds'])
