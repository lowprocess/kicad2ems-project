"""Assemble already validated independent cases and adaptive exports; infer fields."""
import json,hashlib
from pathlib import Path
import numpy as np
from mom25d.power_circuit import infer_fields,sweep_link,fingerprint
from mom25d.power_bridge import load_config,make_board_ports,matching
from mom25d.mqs_cli import load_board
from mom25d.power_report import render
p=Path(__file__).resolve().parent;cfg=load_config('mom25d/src/mom25d/data/wpthb-power.json');saved=json.loads((p/'copper-model.json').read_text())
rows=[];results=[]
for f in cfg['frequencies_Hz']:
 for w in cfg['powers_W']:
  folder=p/f'{f/1000:g}kHz_{w:g}W';row=json.loads((folder/'case.json').read_text());rows.append(row)
  with np.load(folder/'transient.npz') as values:result={k:values[k] for k in values.files}
  result['_measures']=json.loads((folder/'measurements.json').read_text());results.append(result)
  assert (folder/'port-spectrum.npz').exists()
b=load_board('benchmark-results/wpthb-inspection-2026-11-07/board.json');q,ports,crop=make_board_ports(b,cfg);key=fingerprint(b,cfg);assert key==saved['fingerprint']
infer_fields(q,ports,saved['model'],cfg,rows,results,crop,p,key,harmonics=16)
summary=dict(format=1,complete=True,name=cfg['name'],cases=rows,copper=saved['model'],ports=ports,
 frequency_sweeps=[sweep_link(cfg,f,matching(cfg,f)) for f in cfg['frequencies_Hz']],assumptions=cfg['assumptions'],
 matching_definition='Secondary series tuned per frequency; AC resistance maximizes sinusoidal link efficiency; primary 99 nF fixed; phase targets actual load power.',
 field_inference='Periodic copper/via fields from adaptive-step terminal-current quadrature. External coil/lead/package fields and upstream input-filter geometry excluded.',
 artifact_note='Electrical netlists were replayed unchanged to export adaptive currents after the exporter was added. The 110kHz/30W replay halves integration/output max step; scalar power/current deltas are recorded. Main electrical results retain their original accepted resolution.',
 validation=dict(copper_harmonics=json.loads((p/'copper-harmonic-validation.json').read_text()),
 numerical_refinement=json.loads((p/'110kHz_30W/adaptive-replay-validation.json').read_text())))
(p/'power-circuit.json').write_text(json.dumps(summary,indent=2));render(p)
print('Finished all eight circuit and field cases',flush=True)
