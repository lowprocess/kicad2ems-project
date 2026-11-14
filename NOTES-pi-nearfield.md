> **History (2026-11-07 to 2026-11-10), not the present state.** Much of it is superseded: the power tools moved from mom25d to pcbqs, Palace is an engine through kicad2ems-fem, and the near field, the DC maps and the KiCad path are built. What exists now: pcbqs's docs and CHANGELOG.md; what is left: kicad2ems's ROADMAP.md.

# Power integrity and near field: where it stands, where it could go

Notes from the work of 6–7 November 2026. All of it was merged into main on 7 November: mom25d's `pdn` and
`nearfield`, kicad2ems-gui's `pdn`, and the parent's `pdn`. The plan for the quasi-static solver's speed-up and
integration is in kicad2ems's ROADMAP.md. kicad2ems-palace is a local repo with no remote yet.

## What exists

### Palace (FEM) spike: `kicad2ems-palace/`, committed locally

- A kicad2ems solver plugin, `palace`, left out of `--solvers auto`.
  - `model.py`: a gmsh tetrahedral mesh of the slabs in an air box, copper as PEC sheets, vias as PEC holes,
    lumped ports.
  - `config.py`: a driven run with the adaptive sweep and every port excited.
  - `run.py`: runs Palace natively, or from an unpacked image through rootless podman.
- Palace itself is a community 0.18.1 image unpacked in `~/opt/palace/rootfs`.
- **rf_gcpw:** rms |ΔS| 0.055 from openEMS in 561 s (926k unknowns, 10 GB), against 6–8 s for gfdtd and mom25d.
  S11 converges as the mesh refines at the copper edges; sharper grading made it worse.
- **Verdict: parked.** It's 20–90× slower on planar boards. It's only worth picking up for eigenmodes (cans,
  enclosures, high-Q filters) or truly 3D parts (connectors, wire bonds).

### DC drop and PDN impedance: `mom25d.pdn` (branch `pdn`)

| Module | What it does |
|---|---|
| `mesh.py` | Each net's copper per layer on mom25d's mesher. Pad outlines become mesh edges; finer cells can be asked for around chosen terminals. P1 stiffness and mass matrices. |
| `rail.py` | The rail tree, grown from the rail's net through resistors up to `max_ohms` (default 1 Ω), beads and jumpers; `through=` and `stop=` override. A power inductor ends the tree and is the default source; the parts on its switch node give the return's source. Also finds the decaps and loads. Values come from fields such as `R_0R001_0805`, `600R@100MHz` and `sim.esr`. |
| `dc.py` | `Network`: the copper of a set of nets, with pads as equipotential terminals (1 µΩ ties), via barrels, and series parts as resistors. `solve_rail` solves the rail and its return: each load's voltage, split into supply-side drop and ground rise, plus maps, via currents and loss. |
| `cavity.py` | One plane pair as a 2D cavity (C′ and dielectric loss, plane inductance, skin resistance), with decap, VRM and load ports. `rect_cavity_z` is the analytic double sum for a rectangle. |
| `stack.py` | `RailPDN`: every plane pair of a rail solved together, joined at ground or rail vias through both pairs and at every port. Each part connects through its pad's copper (μ0·h·squares, from a conduction solve of that copper) and its via pair. Rail nets without a plane become lumped nodes behind their series parts (beads use an R_dc + (L ∥ R₁₀₀) model). |
| `cli.py` | `python -m mom25d.pdn board --rail NET --load REF=A …` writes `pdn.json`, `z.csv` and figures. `--describe --json` describes the options for the GUI. |

**Validation**
- A strip's DC resistance matches R = L/(σtW).
- Vias obey Kirchhoff and Rosa's barrel resistance.
- The plane pair is C = εA/d at low frequency, and matches the cavity double sum to 5%. On self terms the
  constant μ0·d/8π port-model difference is allowed for, and the 0.4 mm mesh is within 0.5% at 3.3 GHz.
- A decap's series resonance falls at 1/(2π√(C·ESL)).
- A synthetic 4-layer rail checks the tree, the sense resistor's drop (I·R exactly), via in pad, decap trace
  squares, and two plane pairs in parallel (C₁ + C₂).
- 13 tests.

**Boards it has run on**
- **CM5 Minima, +5V:** 21 s in all. J101 (USB-C) feeds the CM5 module and three loads; two plane pairs
  (In3 between In2 and In4); worst drop about 20 mV with the loads as given.
- **Jetson AGX Thor baseboard, +3V3:** about 4.5 min.
  - Rail tree L2 → `3V3_OUT` → R258 (1 mΩ) → `+3V3`; 51 decaps; 9 lumped nodes; In2 between In1 and In3.
  - The loads were assumed (5 A shared by pad count), giving a worst drop of 20 mV.
  - Ground meshes reach 0.6–1.1M vertices; DC ≈ 45 s, PDN build ≈ 110 s, sweep ≈ 110 s.

**GUI: the Power Integrity page** (kicad2ems-gui `pdn`, `pdntab.py`)
- Settings come from `--describe`; the run is a separate process, followed in the log.
- Results: a summary (tree, loads, series parts, plane pairs, each part's connection and mount), the impedance
  each load sees against the target, and the DC maps. Like the Filter page, it never imports mom25d.

### Near field (branch `nearfield`)

- **Full-wave mom25d near field (`farfield.near_fields`)**
  - Gives E and H at several heights from one spectrum. `--mom-near` now dumps H as well as E.
    `--mom-near-volume H0,H1[,N]` writes `E@volume` and `H@volume`, which the GUI's 3D view reads (checked:
    `volume3d.Volume` loads them).
  - **Fixed: sampling bias.** The currents were sampled at grid points, which put rf_gcpw's 1 mm field 0.15 mm
    off the trace (points land on one edge, where the current crowds, and not the other) and halved it on another
    grid. They're now deposited onto the grid (cloud in cell), which is grid-independent.
  - **Fixed: H.** H is now magnetostatic, using the ground's image. H from E through the stack's spectral
    voltages was 15% low at 3 mm, even at 0.1 GHz. It now matches Biot–Savart to 0.3%.
- **`biot.py`:** Biot–Savart of RWG sheet currents (refined near the point) and of filaments. All frequencies go
  in one pass: the geometry is made once and applied with matrix products.
- **`mqs.py`: the quasi-static solver**
  - Currents on mom25d's RWG basis on every layer. L comes from the 1/R moments between layers at their offset;
    R from the sheets' Gram matrix. Vias are filaments (Grover/Rosa partial inductance); parts are branches
    (current sources, series R L C). It's solved in a loop basis (spanning tree, cotree), so a sweep is one small
    solve per frequency.
  - Outputs: currents, the loop's Z with and without its parts (`z`, `zc`), the dipole moment, and H anywhere
    (sheets, vias and part filaments).
  - **Validated on a trace over a plane:**
    - return current within ±h of the trace: 47% at 10 MHz against 50% from image theory, and 4.8% at 1 kHz
      (resistive spread);
    - L 11.2 nH, against 10.3 nH from Wheeler for the strip alone;
    - H 2 mm above within 3.5% of image theory;
    - via self-inductance equal to Rosa's;
    - spectral H against Biot–Savart. 5 tests.
- **`tools/nearfield_demo.py`:** a buck hot loop three ways (C1 tight, C1 10 mm away, far plus a ground slot) at
  the 500 kHz harmonics for a 3 A trapezoid. It gives L, R, the dipole moment, H at 1, 3 and 10 mm, plane and
  volume dumps for the GUI, and the figures. Results below.

### The buck demo's results

Fundamental 500 kHz; the harmonics are weighted by a 3 A trapezoid (duty 0.33, so every third harmonic is about
zero). Outputs are in `kicad2ems-studies/nearfield_demo/`.

| | good | far | slot |
|---|---|---|---|
| Hot-loop copper L | 0.39 nH | 3.7 nH | 9.8 nH |
| R (0.5 MHz) | 1.2 mΩ | 11.5 mΩ | 15.6 mΩ |
| Dipole moment (0.5 MHz) | 14 A·mm² | 56 A·mm² | 73 A·mm² |
| Peak \|H\| 10 mm above | 1.75 A/m | 4.8 A/m | 6.7 A/m |
| Peak \|H\| 3 mm above | 47 A/m | 54 A/m | 60 A/m |

- **What discriminates the layouts:** the loop's L and dipole moment, and H at 10 mm (2.7× and 3.8× the good
  layout's). H at 1–3 mm is dominated by the parts' own current directly below, and differs little between them.
- **What the maps show:** the plane's return current running under the VIN trace (far), and pulled round the slot's
  end (slot).
- **Run time:** each layout takes 1–1.5 min to solve and 1.6 min for the fields, out of 9 min for the whole demo.

## Known limits

- **PDN**
  - Load currents are typed in, or spread by pad count as a labelled assumption.
  - One rail per run. The VRM is R + L, with no control-loop model.
  - Packages and dies are not modelled.
  - The importer has to be run twice: once to find the rail tree, then to read its nets.
  - The DC maps are images, not an overlay in the GUI's Viewer.
  - ESR and ESL default by package when the part has no fields.
- **Quasi-static solver**
  - R is unreliable above about 30 MHz: about 1% of ωL leaks into the real part through quadrature error. L and
    H are fine.
  - Uniform current through the copper thickness, with no skin depth across it.
  - Parts are straight filaments at a nominal height; their mutual inductance with the copper is ignored.
  - The L matrix is dense, built in O(N²) by Python-driven numpy: about 45–80 s for 4–6k triangles.
  - There's no E field yet (the switch node's dv/dt).
  - The demo's layouts are synthetic; there's no path from a KiCad board yet.
- **Full-wave near field:** vertical (via) currents aren't in the spectral near field; it's above the top of the
  stack only.

## Where it could be extended

1. **`kicad2ems pdn` from the config**
   - A `[pdn."<rail>"]` table (the rail, loads, VRM, target) read by kicad2ems, with several rails per run.
   - The report gets a PDN section.
   - The DC maps become a Viewer overlay. The mesh and voltages are already per-triangle, so the plan view can
     colour them.
2. **Load currents from a schematic or BOM field** (e.g. `pdn.I`), with a check that the total matches the
   regulator's rating.
3. **PDN extraction from the quasi-static solver:** replace the formula for decap and via mounting inductance with
   the solver's loop L for each part's own pads and vias (it already gives `zc`). Partial-element R/L/C to SPICE
   for the whole rail.
4. **Regulator and package models:** a VRM control loop (a target R + L as a function of bandwidth), Touchstone
   models for decaps (Murata/TDK files) and beads, and the package and die capacitance at the load.
5. **Near-field scans from real boards:** pick a DC-DC from its parts (the inductor on the switch node, Cin
   between VIN and PGND) and its copper. Report the hot-loop L and dipole moment, the H map at a probe height, and
   per-harmonic levels with the converter's own frequency, duty and edge rate. Compare against EMC probe scans.
6. **The switch node's E field:** the capacitive kernel (mom25d's static G_q) on the switch-node copper for E
   maps and its capacitance to the chassis/plane, the other near-field source.
7. **Speed**
   - The L matrix: mom25d's coplanar `singular_moments` for same-layer blocks, threads, or its Vulkan GPU path.
   - H-matrix / ACA compression (mom25d has BLR/HODLR) for larger regions.
   - Adaptive sub-meshing around field points.
8. **Higher frequency on the quasi-static mesh:** add the capacitive (G_q) part to make a full partial-element
   (PEEC) model, valid up to where the board is about λ/10, to bridge to mom25d's full-wave solve. At low
   frequency the full-wave solve breaks down numerically.
9. **GUI:** a Near-field page (or a mode of the Power Integrity page) to run `mqs` scans, and show H maps, the
   spectrum and a good/bad comparison, using the Fields and 3D tabs that already read these dumps.
10. **Palace** (only if needed): eigenmodes of a shielded board inside its can.
