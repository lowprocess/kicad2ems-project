"""Extract all field transfer frequencies once, independently of load-case currents."""
import json
from pathlib import Path
from mom25d.power_bridge import load_config,make_board_ports
from mom25d.power_circuit import extract_cached,fingerprint
from mom25d.mqs_cli import load_board
p=Path(__file__).resolve().parent;c=load_config('mom25d/src/mom25d/data/wpthb-power.json')
b=load_board('benchmark-results/wpthb-inspection-2026-11-07/board.json');key=fingerprint(b,c)
saved=json.loads((p/'copper-model.json').read_text());assert key==saved['fingerprint']
q,ports,crop=make_board_ports(b,c);assert [t['name'] for t in ports]==saved['model']['names']
for f in sorted({float(h*fs) for fs in c['frequencies_Hz'] for h in range(17)}):
 extract_cached(q,[f],p,key)
print('Field transfer cache complete',flush=True)
