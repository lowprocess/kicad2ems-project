# Simulation and validation records

These directories preserve the scripts, configurations, measured results,
reports and pictures from the QS/MQS, WPT and GUI work. Historical records retain
their original package names and absolute source paths; maintained workflows
now use `pcbqs`.

- [Copper meshing comparison](isotropic-mesh-2026-11-07/README.md)
- [CM5 ground-plane mesh](cm5-mesh-2026-11-07/README.md)
- [GPU and roadmap investigation](roadmap-2026-11-07/README.md)
- [Jetson GUI walkthrough](jetson-gui-walkthrough-2026-11-07/README.md)
- [Layout previews](layout-preview-2026-11-07/README.md)
- [WPT schematic inspection](wpthb-inspection-2026-11-07/README.md)
- [WPT quasistatic analysis](wpthb-qs-2026-11-07/README.md)
- [WPT operational model and fields](wpthb-operational-2026-11-07/README.md)
- [PCB-coupled WPT simulations](wpthb-coupled-2026-11-07/README.md)
- [Fixed receiver-capacitance comparison](wpthb-fixed-100n-2026-11-07/README.md)
- [Circuit runtime profiling](wpthb-profile-2026-11-07/README.md)
- [Independent pcbqs split](pcbqs-split-2026-11-07/README.md)
- [Simulation schematic editor](schematic-editor-2026-11-07/README.md)

Raw ngspice output, field grids, compressed solver arrays/caches, source archive
snapshots and package wheels are retained locally and ignored by Git. Some raw
files exceed GitHub's 100 MiB file limit. Previously committed reference arrays
remain in history. `local-artifacts.json` records filenames, sizes and SHA-256
hashes of the locally retained generated artifacts at publication.

The separate `kicad2ems-palace` checkout is not part of these changes.
