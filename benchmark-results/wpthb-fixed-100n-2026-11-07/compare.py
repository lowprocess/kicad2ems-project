"""Fixed 100 nF compensation and fixed receiver load: frequency/phase comparisons."""
import json,copy,time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
import numpy as np
from scipy.optimize import brentq
from scipy.signal import find_peaks
from mom25d.power_bridge import load_config,matching,build,metrics
from mom25d.power_circuit import run_case
from mom25d.wpt import link,match_receiver
out=Path(__file__).resolve().parent
c=load_config('mom25d/src/mom25d/data/wpthb-power.json');c['name']='Fixed 100 nF / 100 nF, k=0.4';c['primary_C_F']=c['secondary_C_F']=100e-9
for part in c['components']:
 if part['ref'] in ['C25','C27','C30']:part['value']=100e-9/3
f0=1/(2*np.pi*np.sqrt(c['primary']['L_H']*100e-9))
c['load_ohm']=match_receiver(f0,c['primary'],c['secondary'],.4,100e-9,.005,.015,C2=100e-9)['load_ohm']
c['assumptions']=[*c['assumptions'][:1], 'Both compensation capacitors fixed at 100 nF; primary bank hypothetically scaled to 3 x 33.333 nF. Original 99 nF KiCad bank is unchanged.',
 'Receiver load fixed at the once-selected maximum-link-efficiency resistance near the uncoupled resonance; no capacitor or load retuning during frequency sweeps.',
 '24 V, k=0.4 and the previous generic transistor/part/core-loss parameters retained.',
 'Detailed circuit cases include input filter/parasitics and ideal PCB interconnects. No copper feedback or field extraction in this comparison.',
 'Frequency-only power control uses full bipolar bridge command (180-degree phase) on the specified 70-90 kHz rising-power branch; phase-control comparison uses 90/110 kHz.']
(out/'model.json').write_text(json.dumps(c,indent=2))
def fundamental(f,phase=180):
 z=link(f,c['primary'],c['secondary'],.4,100e-9,100e-9,c['load_ohm'],.005,.015)
 vrms=2*np.sqrt(2)*24/np.pi*np.sin(np.deg2rad(phase)/2)
 ip=vrms/abs(z['input_Z_ohm']);isec=abs(z['secondary_per_primary'])*ip
 return dict(power_W=isec**2*c['load_ohm'],primary_rms_A=ip,secondary_rms_A=isec,link_efficiency=z['efficiency'],input_X_ohm=z['input_Z_ohm'].imag,input_phase_deg=float(np.angle(z['input_Z_ohm'],deg=True)))
freqs=np.linspace(60e3,160e3,2001);curve={key:[] for key in fundamental(100e3)}
for f in freqs:
 for key,value in fundamental(f).items():curve[key].append(value)
peaks=find_peaks(curve['power_W'])[0]
roots={str(p):float(brentq(lambda f:fundamental(f)['power_W']-p,70e3,90e3)) for p in c['powers_W']}
analytical=dict(frequencies_Hz=freqs.tolist(),full_bridge_phase_deg=180,**curve,
 f0_Hz=float(f0),undamped_mode_Hz=[float(f0/np.sqrt(1+.4)),float(f0/np.sqrt(1-.4))],
 loaded_power_peak_Hz=freqs[peaks].tolist(),frequency_only_fundamental_targets_Hz=roots,
 fixed_load_ohm=c['load_ohm'],points={str(int(f)):fundamental(f) for f in [90e3,110e3]})
(out/'linear-sweep.json').write_text(json.dumps(analytical,indent=2))
def frequency_case(power):
 folder=out/f'frequency_only_{power:g}W';folder.mkdir(exist_ok=True)
 if (folder/'case.json').exists():return 'frequency',json.loads((folder/'case.json').read_text())
 cc=copy.deepcopy(c);f=roots[str(power)];cycles=32;history=[]
 if power==10:
  cc['transient'].update(initialization='ramp',linear_solver='klu',samples_per_cycle=256,method='gear');f=77450.;cycles=84
 for it in range(10):
  m=matching(cc,f);trial=folder/f'trial-{it:02d}'
  print(f'[frequency/{power}W] {f/1000:.4f} kHz, {cycles} cycles',flush=True)
  try:result=build(cc,f,180,m).run(trial,f,cycles=cycles,samples_per_cycle=cc['transient'].get('samples_per_cycle',256),ramp_s=cc['supply'].get('ramp_s',100e-6),linear_solver=cc['transient'].get('linear_solver','klu'),method=cc['transient'].get('method','gear'))
  except RuntimeError:
   if cc['transient']['initialization']=='precharged':
    cc['transient']['initialization']='ramp';print('Retry with zero-energy supply ramp',power,flush=True);continue
   if cc['transient'].get('linear_solver','klu')=='klu':
    cc['transient']['linear_solver']='sparse';print('Retry with sparse linear solver',power,flush=True);continue
   raise
  met=metrics(result,f,m);err=met['load_power_W']/power-1;per=max(met['periodic_error'].values())
  history.append(dict(frequency_Hz=f,cycles=cycles,relative_power_error=err,**met))
  (trial/'metrics.json').write_text(json.dumps(history[-1],indent=2));(trial/'transient.dat').unlink(missing_ok=True)
  physical=max(v for k,v in met['periodic_error'].items() if k!='supply.I')
  if physical>.005 or (abs(err)<.005 and per>.005):cycles=int(cycles*1.6)+1;continue
  assert met['terminal_power_balance_relative']<1e-4 and met['input_power_W']>0
  if abs(err)<.005:
   row=dict(target_W=power,frequency_Hz=f,phase_deg=180,C1_F=100e-9,C2_F=100e-9,load_ohm=c['load_ohm'],**met,history=history)
   (folder/'case.json').write_text(json.dumps(row,indent=2));return 'frequency',row
  df=10.;slope=(fundamental(f+df)['power_W']-fundamental(f-df)['power_W'])/(2*df)
  newf=f+(power-met['load_power_W'])/(slope*met['load_power_W']/fundamental(f)['power_W'])
  f=float(np.clip(newf,70e3,90e3));cc['transient']['initial_input_A']=power*met['input_power_W']/met['load_power_W']/24
 raise RuntimeError('frequency control did not converge')
def phase_case(f,power):
 folder=out/f'{f/1000:g}kHz_{power:g}W';folder.mkdir(exist_ok=True)
 if (folder/'case.json').exists():return 'phase',json.loads((folder/'case.json').read_text())
 row,_=run_case(c,f,power,folder,log=lambda msg:print('[phase] '+msg,flush=True));return 'phase',row
rows={'phase':[],'frequency':[]}
with ThreadPoolExecutor(max_workers=4) as pool:
 jobs=[pool.submit(phase_case,f,p) for f in c['frequencies_Hz'] for p in c['powers_W']]+[pool.submit(frequency_case,p) for p in c['powers_W']]
 for job in as_completed(jobs):
  kind,row=job.result();rows[kind].append(row);print('DONE',kind,row['target_W'],row['frequency_Hz'],row['load_power_W'],flush=True)
  (out/'circuit-results.json').write_text(json.dumps(rows,indent=2))
print('All fixed-capacitor cases complete',flush=True)
