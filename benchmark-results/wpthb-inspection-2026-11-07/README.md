# wpthb H-bridge sample inspection

Inspected the original schematic and PCB in /home/bt/Desktop/wpthb without editing either file. Exported the KiCad schematic netlist and SVG, imported the PCB, and checked the power-stage net sets between schematic and layout. All 17 checked power-stage parts match; MOSFET schematic drain pins 5–8 map to the footprint's consolidated drain pad.

The board is 50 x 50 mm, nominal 1.6 mm, four copper layers. The imported layout has 109 footprints (including DNP) and 411 vias. The top layer carries the bridge/coil routes; the inner/bottom layers contain extensive ground copper. Copper foil is specified as 35 µm. Imported sheet-plane z locations and stack conventions are retained in board.json; they should be reviewed against the physical stack when validating parasitics.

| Role | References | Nets |
|---|---|---|
| Left bridge leg | Q2 high, Q4 low, driver U7 | VHB → /HL_SW → GND |
| Right bridge leg | Q1 high, Q3 low, driver U6 | VHB → /HR_SW → GND |
| Local bridge decoupling | C20–C23 10 µF each; C19/C24 1 µF each | VHB ↔ GND |
| Input filter | L3 5.6 µH | VBUS ↔ VHB |
| Input bulk bank | CA1–CA4 22 µF each | VBUS ↔ GND |
| Input-current shunt | R9 5 mΩ, INA139 U2 | VIN ↔ VBUS |
| Coil series-capacitor bank | C25/C27/C30 33 nF each, nominal parallel sum 99 nF | /HL_SW ↔ /HL_AC |
| External coil pads | TP15 COIL_A; TP14 COIL_B | /HL_AC ↔ /HR_SW |

Population matters: C17 is a DNP extra 33 nF position; CE1–CE4 are DNP alternatives alongside the populated CA bulk capacitors. C37 is a 10 pF sensing connection and must not be lumped into the power series-capacitor bank.

Candidate multi-loop analyses:

1. Diagonal drive Q2/Q3: VHB → Q2 → /HL_SW → series capacitor bank → /HL_AC → external coil → /HR_SW → Q3 → GND → local DC-link capacitors.
2. Opposite diagonal Q1/Q4: the corresponding reverse coil-current path.
3. High-side or low-side freewheel paths, depending on modulation. Do not model both devices in one leg as simultaneously conducting.
4. Each leg's high-frequency commutation loop, including DC-link capacitors and device output capacitances/commutation currents; this is not the same as a both-switches-on conduction state.
5. Input-filter/bulk loop and, separately if needed, gate-drive/bootstrap return loops.

These paths share copper, capacitors and return planes. Their amplitudes and phases must come from consistent operating waveforms rather than independent arbitrary loop currents.

bridge-topology.json records explicit PCB terminal polygons grouped by part/net, the leg mapping, candidate states and nominal capacitors. It is an inspection template, not an executable solver config. The user has now specified the coil and a 70–110 kHz phase-shift-controlled drive target (details below). Exact bus voltage, phase/dead time, receiver loading and mounted coil/lead geometry remain unspecified. The board has coil pads but no external coil geometry, so board files alone cannot predict the complete coil/lead field.

This is a suitable sample for extending the GUI to generic loop/excitation groups. The current converter GUI remains a buck input-loop workflow; a complete H-bridge run needs the planned generic source/passive-branch configuration. No electromagnetic solve or mesh-convergence claim was made here.

Artifacts: bridge-layout.png shows a four-layer power-stage crop with net colors; schematic.png / schematic/wpthb.svg show the schematic; connectivity-check.json records the schematic/layout comparison; board.json is the imported board representation. Original files were left unchanged.

## User-specified coil and drive target

The external coil is Würth 760308101310, 24 µH, with a target drive band of
70–110 kHz and phase-shift control. The [manufacturer datasheet](https://www.we-online.com/components/products/datasheet/760308101310.pdf)
confirms 7.7 MHz is self-resonant frequency, DCR 90 mΩ typical / 110 mΩ maximum,
and typical Q=155 at 125 kHz and 10 mA. Its 7.5 A rating is a DC temperature-rise
rating; the 100 W typical power capability is quoted at a 20 V test supply.
That test condition has not been used as the actual bridge bus voltage.

Calculated from the populated bank and nominal coil:

- C25/C27/C30 in parallel give 99 nF. With 24 µH, the ideal unloaded series
  resonance is 103.25 kHz. Coil inductance tolerance alone gives about
  98.45–108.84 kHz; capacitor tolerance, leads, ferrite environment and receiver
  loading are additional effects.
- If optional C17 were populated, the bank would become 132 nF and the nominal
  resonance 89.42 kHz. C17 remains marked DNP in the inspected layout.
- At 125 kHz, omega*L/Q gives an equivalent total series loss of approximately
  0.122 Ω. This is a small-signal loss anchor, not an additional 0.122 Ω to add
  to DCR, and not a demonstrated constant resistance across frequency/current.

Define phi as the relative phase of two 50%-duty leg-midpoint square waves,
with phi=0 cancelling differential bridge voltage and phi=pi giving full
bipolar drive. In the ideal zero-dead-time model, the odd-harmonic peak voltage
is 4*VHB/(pi*n)*abs(sin(n*phi/2)); even harmonics vanish. The fraction of a
period at nonzero differential voltage is phi/pi. Actual firmware timing may
use a different phase convention, so this convention is explicit in the
parameter template.

The next excitation model should obtain complex tank/bridge currents from
that differential-voltage spectrum and the loaded RLC network, then supply
consistent currents to the copper model. It should account for the applicable
freewheel intervals and eventually nonlinear commutation/dead-time behavior.
The coil rating does not specify operating AC current or delivered power.
Geometry/ferrite and lead placement remain necessary to predict the external
coil field, beyond its lumped terminal impedance.

bridge-topology.json now records these supplied/verified parameters and their
provenance. coil-drive-calculations.json and coil-and-phase-shift.png contain
the nominal calculations and ideal modulation curves. No converter current or
EM field simulation has been claimed from these parameters alone.
