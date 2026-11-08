"""Independent physical and output consistency checks for this demonstration."""
import json
from pathlib import Path
import numpy as np
from kicad2ems.fields.frames import read_vtr,find_dumps
out=Path(__file__).resolve().parent
s=json.loads((out/'summary.json').read_text());d=np.load(out/'time_fields.npz')
R=s['coil_R_ohm'];L=s['coil_L_H'];C=s['coil_parallel_C_F'];f=s['coil_SRF_Hz']
def z(f):
 w=2*np.pi*f;zz=R+1j*w*L;return zz/(1+1j*w*C*zz)
assert np.isclose(1/(2*np.pi*np.sqrt(L*C)),f)
assert z(0)==R
assert np.all(np.real(z(np.geomspace(1,100e6,10000)))>0)
assert np.all(np.isfinite(d['H']))
assert s['boundary_residual']<1e-7
assert max(p['symmetry_error'] for p in s['port_checks'])<1e-7
assert s['power_balance_relative']<.02,s['power_balance_relative']
assert s['phase_sweep']['0']['coil_peak_A']<1e-8
assert s['lumped_tank_fundamental_relative']<.02,s['lumped_tank_fundamental_relative']
assert np.all(np.diff([s['phase_sweep'][p]['coil_rms_A'] for p in ['0','45','90','135','180']])>0)
# Ensure exported GUI files have the correct axes, units, field ordering and physical time.
for k in [0,13,63]:
 mesh,H=read_vtr(out/'mqs'/'exc_bridge'/f'dump_H_operational_td_{k:04d}.vtr')
 for ax in ['x','y']:np.testing.assert_allclose(mesh[ax],d[ax],rtol=1e-6)
 np.testing.assert_allclose(mesh['z'],d['z'][:1],rtol=1e-6)
 np.testing.assert_allclose(H,d['H'][k*4,:,:,0:1,:],rtol=2e-6,atol=1e-5)
src=find_dumps(str(out));assert len(src)==1,len(src)
assert len(src[0].frames)==64
result=dict(status='passed',checks=['SRF and DCR endpoints','positive-real coil impedance','finite vector fields','switch boundary residual','port reciprocity','input power versus copper + coil loss (<2%)','zero output at zero phase','monotonic phase current','independent lumped tank fundamental (<2%)','GUI VTK axis/units/field round-trip','64 time-domain GUI frames'],power_balance_relative=s['power_balance_relative'],tank_fundamental_relative=s['lumped_tank_fundamental_relative'],coil_Q_125k_from_DCR=float(abs(z(125e3).imag)/z(125e3).real))
(out/'validation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
