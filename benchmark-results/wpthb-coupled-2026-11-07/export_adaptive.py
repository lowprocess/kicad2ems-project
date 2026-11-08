"""Replay the identical settled netlists to export their adaptive current vectors.
The first electrical cases predate the adaptive exporter; no phase/model is changed.
The 110 kHz/30 W replay additionally halves maximum integration/output step.
"""
import json,re,subprocess,time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
from mom25d.power_waveforms import save_port_spectrum
p=Path(__file__).resolve().parent

def export(f,power):
 folder=p/f'{f/1000:g}kHz_{power:g}W'
 while not (folder/'case.json').exists():time.sleep(1)
 case=json.loads((folder/'case.json').read_text());labels=list(json.loads((folder/'signals.json').read_text()))
 text=(folder/'circuit.cir').read_text();selected=['out'+str(i) for i,label in enumerate(labels) if re.fullmatch(r'PCB\d+\.I',label)]
 if not (folder/'port-spectrum.npz').exists():
  text=text.replace('linearize ','set filetype=binary\nwrite adaptive-ports.raw '+' '.join(selected)+'\nset filetype=ascii\nlinearize ',1)
  fine=(f==110000 and power==30)
  if fine:
   lines=text.splitlines()
   for i,line in enumerate(lines):
    if line.startswith('tran '):
     words=line.split();words[1]=str(float(words[1])/2);words[4]=str(float(words[4])/2);lines[i]=' '.join(words)
   text='\n'.join(lines)+'\n'
  (folder/'adaptive-replay.cir').write_text(text)
  print('Adaptive replay',f,power,'fine',fine,flush=True);t=time.monotonic()
  proc=subprocess.run(['ngspice','-b','adaptive-replay.cir'],cwd=folder,capture_output=True,text=True,timeout=900)
  (folder/'adaptive-replay.log').write_text(proc.stdout+'\n'+proc.stderr)
  if proc.returncode or 'simulation(s) aborted' in proc.stderr:raise RuntimeError('adaptive export failed: '+str(folder))
  prior=json.loads((folder/'measurements.json').read_text());updated={}
  for i,key in enumerate(prior):
   match=re.search(rf'^m{i}\s*=\s*([+\-0-9.eE]+)',proc.stdout,re.M)
   if not match:raise RuntimeError('missing replay measure '+key)
   updated[key]=float(match[1])
  delta={key:abs(updated[key]-prior[key])/max(abs(prior[key]),1e-12) for key in ['load_power_W','input_power_W','primary_rms_A','secondary_rms_A']}
  assert max(delta.values())<.005,delta
  check=dict(physical_netlist_unchanged=True,half_maximum_timestep=fine,relative_measure_changes=delta,seconds=time.monotonic()-t)
  (folder/'adaptive-replay-validation.json').write_text(json.dumps(check,indent=2))
  save_port_spectrum(folder,labels,f)
  (folder/'transient.dat').unlink(missing_ok=True)
  print('Adaptive DONE',f,power,check,flush=True)
 return str(folder)
with ThreadPoolExecutor(max_workers=4) as pool:
 for job in as_completed([pool.submit(export,f,w) for f in [90000,110000] for w in [5,10,20,30]]):print('Ready:',job.result(),flush=True)
