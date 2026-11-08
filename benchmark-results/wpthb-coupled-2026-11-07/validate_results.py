"""Acceptance checks on real coupled bridge, reduced copper and field artifacts."""
import json
from pathlib import Path
import numpy as np
from mom25d.power_spice import periodic_samples
from kicad2ems.fields.frames import read_vtr,find_dumps
p=Path(__file__).resolve().parent;s=json.loads((p/'power-circuit.json').read_text());cfg=json.loads((p/'model.json').read_text())
assert cfg['primary_C_F']==99e-9 and cfg['coupling']==.4
assert len(s['cases'])==8
rows=[]
for c in s['cases']:
 folder=Path(c['folder']);power_error=abs(c['load_power_W']/c['target_W']-1)
 assert power_error<.005
 assert max(c['periodic_error'].values())<.005
 assert c['terminal_power_balance_relative']<1e-4
 assert 0<c['efficiency']<1 and c['input_power_W']>0
 with np.load(folder/'port-spectrum.npz') as z:
  adaptive=z['coefficients_A'][:17];energy=z['AC_mean_square_A2'].sum()
  assert np.all(np.isfinite(adaptive)) and energy>0
 with np.load(folder/'transient.npz') as z:raw={k:z[k] for k in z.files}
 _,v,_=periodic_samples(raw,c['frequency_Hz'],samples=1024)
 uniform=np.fft.rfft(np.stack([v[f'PCB{i}.I'][-1] for i in range(24)],axis=1),axis=0)/1024
 # A diagnostic, not an acceptance test: the display samples may alias switching pulses.
 sampled_error=float(np.linalg.norm(adaptive-uniform[:17])/np.linalg.norm(adaptive))
 with np.load(folder/'time_fields.npz') as z:
  H=z['H'];coef=z['H_coefficients'];assert H.shape==(64,25,25,2,3)
  assert np.isfinite(H).all()
  np.testing.assert_allclose(H.mean(axis=0),coef[...,0].real,atol=1e-10)
  for k in [0,17,63]:
   mesh,field=read_vtr(folder/'mqs/exc_bridge'/f'dump_H_operational_td_{k:04d}.vtr')
   np.testing.assert_allclose(field,H[k,:,:,0:1,:],rtol=1e-6,atol=1e-6)
   for ax in ['x','y']:np.testing.assert_allclose(mesh[ax],z[ax],rtol=1e-6)
 assert len(find_dumps(str(folder))[0])==64
 info=json.loads((folder/'field-inference.json').read_text());assert info['FFT_grid']['converged']
 assert max(info['copper_model_error_per_harmonic'])<.04
 rows.append(dict(frequency_Hz=c['frequency_Hz'],target_W=c['target_W'],power_error=power_error,display_sample_spectrum_relative_error=sampled_error,
                  field_peak_Am=info['peak_H_Am'],omitted_AC_current_energy_fraction=info['discarded_port_current_AC_energy_fraction']))
for A in [s['copper']['R_ohm'],s['copper']['L_H'],*[v['R_ohm'] for v in s['copper']['foster']]]:
 e=np.linalg.eigvalsh(A);assert e.min()>-1e-10*max(abs(e).max(),1e-20)-1e-18
refine=s['validation']['numerical_refinement'];assert refine['half_maximum_timestep'];assert max(refine['relative_measure_changes'].values())<1e-3
result=dict(status='passed',checks=['8 power targets within 0.5%','final-cycle repeatability below 0.5%','terminal power balance below 0.01%','positive-semidefinite passive copper realization','independent harmonic equivalent error below 4%','adaptive-spectrum finite data','FFT field-grid convergence','64-frame real-vector reconstruction and VTK round-trip','half-timestep electrical sensitivity below 0.1%'],cases=rows)
(p/'validation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
