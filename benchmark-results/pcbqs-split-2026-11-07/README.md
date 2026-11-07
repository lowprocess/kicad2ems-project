# Independent pcbqs extraction — 7 November 2026

Implemented the package split with privately copied primitives. Published
[pcbqs](https://github.com/lowprocess/pcbqs); coordinated MoM, core and GUI changes
are on `codex/pcbqs-split`. The umbrella branch pins their exact commits and its
installer extras pin matching source revisions. Existing companion default
branches are not merged by this change.

## Ownership

- `pcbqs`: PDN/DC, MQS/PEEC, copper reduction, static fill and GPU kernels,
  electrostatics, magnetic fields, ngspice/WPT workflow, reports and examples.
- Private `_numerics` snapshots replace runtime imports of MoM. Source revisions,
  content hashes and licensing are recorded in `pcbqs/PROVENANCE.json`.
- JSON solving, field/mesh export and reconstruction need neither MoM nor
  kicad2ems. Small dump-format/package-size helpers have local copies as well.
- QS has its own optional native backend (`pcbqs._core`). NumPy/threaded fallback
  works without a native binary. GPU fill remains optional.
- Old QS/PDN/circuit namespaces are removed from MoM, without compatibility shims.
  MoM's shared/mixed-use numerical modules and native core are unchanged.
  All tracked emsdev files are unchanged.
- GUI and installer use pcbqs; `kicad2ems[qs]` is independently selectable,
  including the Triangle source-build fallback for QS-only Python 3.14 installs.

## Validation

| Check | Result |
|---|---|
| PCB/QS suite, including available GPU fill | 131 passed |
| Independent wheel, no MoM or kicad2ems installed | 125 passed, 5 optional checks skipped |
| Isolated field/parity/no-native checks | 4 passed |
| Remaining MoM RF suite | 92 passed |
| GUI/installer integration | 69 passed |
| Final core field/installer checks | 22 passed |

Suites overlap; these counts should not be summed. The five isolated skips are
three optional GPU cases and two frontend interoperability cases. MoM also
imports with its native backend in a separate environment without pcbqs or
kicad2ems. The RF suite's NaN-factor test emitted its expected runtime warning.

## Numerical and runtime parity

The 110 kHz / 30 W bridge generates an identical physical netlist. Its full
52-cycle simulation took **191.23 s** and reproduced every saved
current/voltage trace and timestamp exactly. The original accepted point remains
29.9124 W output and 2.21117 A primary RMS.

The three eight-cycle timing medians were **29.01 s before**
and **28.85 s after** (-0.53%),
within the 10% regression limit. This establishes no material runtime regression;
the split adds no acceleration algorithm or relaxed numerical tolerance.

A fresh full-mesh 110 kHz extraction (13,528 triangles, 8,672 loops, 24 ports)
reproduced impedance and branch-current responses exactly. Field reconstruction
at all 17 retained frequencies, using saved transfer responses, also matched
exactly. The measured relative differences were zero for all these checks.

## Commits

- pcbqs: `f36f3d729d2213a99390a7fdd772294f89cfe063`
- mom25d: `77509a598561e79c292e65369cec10c1816fc25a`
- kicad2ems-gui: `8e218624be24dcf9225473c1c1696d0836a92f86`
- kicad2ems: `d1ed5fa3d4166d31ed44dc48704a198701536c88`

## Local audit artifacts

`validation.json` records the summary. Source snapshots, package wheels/install
checks, protected-file hashes, test logs, raw timings and waveform/field comparisons
are retained locally in this directory. Historical benchmark inputs/results and
the unrelated Palace checkout were preserved. Large snapshots and simulation
outputs are not included in this publication.
