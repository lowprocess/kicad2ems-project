"""Linear-periodic ideal-switch harmonic balance coupled to actual PCB QS port admittance.
Periodic switched drive, 24 V, damped 24 uH coil with SRF capacitance, no receiver.
"""
import json,time,copy,os
from pathlib import Path
import numpy as np
from scipy.linalg import lu_factor,lu_solve
from scipy.sparse import diags
from shapely.geometry import shape
from shapely.ops import unary_union
from mom25d.mqs import MQS,Result
from mom25d.pdn.rail import parts_of,part_value
from mom25d.mqs_layout import save_layout,geometry
out=Path(__file__).resolve().parent
b=json.loads((out.parent/'wpthb-inspection-2026-11-07/board.json').read_text())
parts={p.ref:p for p in parts_of(b)};nets={'VHB','GND','/HL_SW','/HR_SW','/HL_AC'}
caps=['C19','C20','C21','C22','C23','C24','C25','C27','C30']
refs=['Q1','Q2','Q3','Q4','TP14','TP15','L3',*caps];terms={}
for ref in refs:
 for net in sorted(parts[ref].nets() & nets):
  terms[ref+':'+net]=[(l,p.geom) for p in parts[ref].on({net}) for l in p.layers]
extent=unary_union([p for pp in terms.values() for _,p in pp]);crop=extent.buffer(2).envelope
q=MQS(b,nets,terminals=terms,region=crop,dmax=3,fine=extent.buffer(.6).envelope,dmax_fine=1.6,
 fill_backend='openmp',fill_workers=8,conductor_loss='slab',conductor_faces=2,log=lambda *a:print(*a,flush=True))
for ref in caps:
 n=sorted(parts[ref].nets() & nets);q.element(ref,ref+':'+n[0],ref+':'+n[1],C=part_value(parts[ref]),part_h=0)
COIL_L=24e-6;COIL_R=.110;COIL_SRF=7.7e6
COIL_CP=1/((2*np.pi*COIL_SRF)**2*COIL_L)
def coil_z(w):
 z=COIL_R+1j*w*COIL_L
 return z/(1+1j*w*COIL_CP*z)
q.element('COIL','TP15:/HL_AC','TP14:/HR_SW',L=COIL_L,R=COIL_R,part_h=0)
ends={'Q1':('VHB','/HR_SW'),'Q2':('VHB','/HL_SW'),'Q3':('/HR_SW','GND'),'Q4':('/HL_SW','GND')}
for ref,(a,c) in ends.items():q.element(ref,ref+':'+a,ref+':'+c,R=0,part_h=0)
# Ideal local stiff bus. External feed path is excluded from plotted H.
q.element('SUPPLY','C20:GND','L3:VHB',R=0,part_h=0)
portnames=[*ends,'SUPPLY'];fullparts=copy.deepcopy(q.parts);nb=len(q.br)+len(q.parts)
fsw=110e3;N=int(os.environ.get('OP_SAMPLES','128'));nh=N//2;Y=[];response=[];quality=[]
start=time.perf_counter()
m=q._assemble()
cache=np.load(out/'port_responses_R110m_Cp17p8.npz') if (out/'port_responses_R110m_Cp17p8.npz').exists() else None
for n in range(nh+1):
 t=time.perf_counter()
 if cache is not None and n<len(cache['Y']):
  yy=cache['Y'][n];Y.append(yy);response.append(cache['response'][n]);quality.append(dict(harmonic=n,symmetry_error=float(np.linalg.norm(yy-yy.T)/np.linalg.norm(yy))));print('cached harmonic',n,flush=True);continue
 model=q
 if n==0:
  model=copy.copy(q);model.parts=[p for p in fullparts if not p.get('C')];model._mats=None
  model._copper=q._copper;mm=model._assemble()
 else:mm=m
 C=mm['C'];w=2*np.pi*fsw*n
 z=np.array([p.get('R',0)+1j*w*p.get('L',0)+(1/(1j*w*p['C']) if p.get('C') else 0) for p in model.parts])
 z[next(i for i,p in enumerate(model.parts) if p['name']=='COIL')]=coil_z(w)
 Z=mm['Rl'].astype(complex)+1j*w*mm['Ll']+(C.T@diags(np.r_[np.zeros(len(q.br)),z])@C).toarray()
 if n:
  delta=q._resistance_delta(fsw*n)
  if delta.nnz:Z+=(C.T@delta@C).toarray()
 ids=[len(q.br)+next(i for i,p in enumerate(model.parts) if p['name']==name) for name in portnames]
 B=C[ids].toarray();X=lu_solve(lu_factor(Z,overwrite_a=True),B.T)
 currents=np.asarray(C@X);yy=currents[ids]
 full=np.zeros((nb,5),complex);full[:len(q.br)]=currents[:len(q.br)]
 for k,p in enumerate(model.parts):full[len(q.br)+next(j for j,v in enumerate(fullparts) if v['name']==p['name'])]=currents[len(q.br)+k]
 sym=float(np.linalg.norm(yy-yy.T)/max(np.linalg.norm(yy),1e-30))
 quality.append(dict(harmonic=n,symmetry_error=sym));Y.append(yy);response.append(full)
 print('port harmonic',n,'seconds',time.perf_counter()-t,'symmetry',sym,flush=True)
 del X,Z,currents
 if n==0:del model,mm
Y=np.array(Y);response=np.array(response)
np.savez_compressed(out/'port_responses_R110m_Cp17p8.npz',Y=Y,response=response,fsw=fsw)
print('port extraction complete',time.perf_counter()-start,flush=True)


def hb(samples,phase):
 # Real collocation: the Nyquist bin is projected to its real component.
 hn=samples//2;yy=Y[:hn+1].copy();yy[-1]=yy[-1].real
 theta=np.arange(samples)/samples
 a=theta%1<.5;bphase=(theta-phase/360)%1<.5
 on=np.stack([bphase,a,~bphase,~a],axis=1).astype(float)
 def currents(v):
  e=np.fft.rfft(v,axis=0)/samples
  return np.fft.irfft(np.einsum('nij,nj->ni',yy,e)*samples,n=samples,axis=0)
 drive=np.zeros((samples,5));drive[:,4]=24.
 base=currents(drive)
 def op(vec):
  v=np.zeros((samples,5));v[:,:4]=vec.reshape(samples,4)
  i=currents(v)[:,:4]
  return (on*v[:,:4]+(1-on)*i).ravel()
 A=np.column_stack([op(np.eye(samples*4)[:,k]) for k in range(samples*4)])
 rhs=-((1-on)*base[:,:4]).ravel();v=drive.copy();v[:,:4]=np.linalg.solve(A,rhs).reshape(samples,4)
 ii=currents(v);ec=np.fft.rfft(v,axis=0)/samples
 bc=np.einsum('nij,nj->ni',response[:hn+1],ec);bc[-1]=bc[-1].real
 actual=ii[:,:4];res=max(float(abs(on*v[:,:4]).max()),float(abs((1-on)*actual).max()))
 return dict(E=ec,branch=bc,on=on,port_i=ii,port_emf=v,residual=res)

runs={phase:hb(N,phase) for phase in [0,45,90,135,180]};main=runs[90];coarse=hb(N//2,90)
print('HB residual',main['residual'],flush=True)
# Reconstruct real vector fields, retaining DC plus harmonics and their phases.
excluded=[len(q.br)+next(j for j,p in enumerate(fullparts) if p['name']==name) for name in ['COIL','SUPPLY']]
x=np.linspace(crop.bounds[0],crop.bounds[2],25);y=np.linspace(crop.bounds[1],crop.bounds[3],25)
heights=np.array([1.,3.]);top=q.z_of.max()*1000

def field_for(run,samples):
 coef=run['branch'].copy();coef[:,excluded]=0
 rr=Result(np.arange(len(coef))*fsw,coef,{},[p['name'] for p in fullparts])
 H,info=q.h_grid(rr,list(range(len(coef))),x*.001,y*.001,(top+heights)*.001,rtol=.02,return_info=True)
 return H,info
H,info=field_for(main,N);Hsmall,infosmall=field_for(coarse,N//2)
nt=256;tt=np.arange(nt)/(nt*fsw)
def reconstruct(coef,axis=0):
 coef=np.moveaxis(coef,axis,0);weights=np.full(len(coef),2.);weights[0]=1;weights[-1]=1
 return np.einsum('n...,nt,n->t...',coef,np.exp(2j*np.pi*np.arange(len(coef))[:,None]*fsw*tt),weights).real
Ht=reconstruct(H,axis=-1);Ht_small=reconstruct(Hsmall,axis=-1)
coilidx=len(q.br)+next(j for j,p in enumerate(fullparts) if p['name']=='COIL')
wave=reconstruct(main['branch']);coil_port=wave[:,coilidx]
il_coeff=main['branch'][:,coilidx]/(1+1j*2*np.pi*fsw*np.arange(nh+1)*COIL_CP*(COIL_R+1j*2*np.pi*fsw*np.arange(nh+1)*COIL_L))
coil=reconstruct(il_coeff)
coarse_il=coarse['branch'][:,coilidx]/(1+1j*2*np.pi*fsw*np.arange(N//4+1)*COIL_CP*(COIL_R+1j*2*np.pi*fsw*np.arange(N//4+1)*COIL_L))
edges=np.min(abs((tt[:,None]*fsw-np.array([0,.25,.5,.75,1])[None,:])),axis=1)
away=edges>2/(N//2)
errors=dict(H_away_edges_peak_relative=float(abs(Ht[away]-Ht_small[away]).max()/max(abs(Ht).max(),1e-30)),H_peak_relative=float(abs(Ht-Ht_small).max()/max(abs(Ht).max(),1e-30)),
 coil_peak_relative=float(abs(coil-reconstruct(coarse_il)).max()/max(abs(coil).max(),1e-30)))
np.savez_compressed(out/'time_fields.npz',time_s=tt,H=Ht,x=x,y=y,z=top+heights,coil_A=coil,
 coil_terminal_A=coil_port,coil_inductor_coefficients=il_coeff,port_on=main['on'],port_emf_V=main['port_emf'],port_current_A=main['port_i'],branch_currents_A=wave,part_names=np.array([p['name'] for p in fullparts]),H_coefficients=H,E=main['E'],fsw=fsw)
selected=dict(converter='Q1',capacitors=[*caps,'Q2','Q3','Q4','L3','TP14','TP15'])
layout=save_layout(out,b,q,crop,selected);geo=geometry(layout)
# Time-domain VTK files are read by the existing GUI, without pretending time samples are frequencies.
exc=out/'mqs'/'exc_bridge';exc.mkdir(parents=True,exist_ok=True)
def ascii_values(a):return ' '.join(f'{v:.8g}' for v in np.asarray(a).ravel())
for k in range(64):
 j=k*4;arr=Ht[j,:, :,0,:].transpose(1,0,2).reshape(-1,3)
 xml=f'''<VTKFile type="RectilinearGrid" version="0.1" byte_order="LittleEndian"><RectilinearGrid WholeExtent="0 24 0 24 0 0"><Piece Extent="0 24 0 24 0 0"><PointData Vectors="H"><DataArray type="Float32" Name="H" NumberOfComponents="3" format="ascii">{ascii_values(arr)}</DataArray></PointData><Coordinates><DataArray type="Float64" format="ascii">{ascii_values(x)}</DataArray><DataArray type="Float64" format="ascii">{ascii_values(y)}</DataArray><DataArray type="Float64" format="ascii">{top+heights[0]}</DataArray></Coordinates></Piece></RectilinearGrid></VTKFile>'''
 (exc/f'dump_H_operational_td_{k:04d}.vtr').write_text(xml)
meta=dict(geo,dt_ps=1e12/(64*fsw),field_scope='PCB and local branch filaments; external coil and feed wires excluded',
 dumps=[dict(name='dump_H_operational_td',field='H',spec='H@top+1mm',label='operational, top+1mm',freqs=None,normal=2,start=[x[0],y[0],top+1],stop=[x[-1],y[-1],top+1],unit='A/m')])
(exc/'dump_info.json').write_text(json.dumps(meta))
def copper_loss(run):
 total=0.
 for n,v in enumerate(run['branch']):
  R=m['R']+(q._resistance_delta(n*fsw) if n else 0)
  total+=(1 if n in (0,len(run['branch'])-1) else 2)*float(np.real(np.vdot(v,R@v)))
 return total
loss=copper_loss(main);pin=24*float(main['branch'][0,-1].real)
weights=np.full(nh+1,2.);weights[[0,-1]]=1
coil_loss=float(np.sum(weights*COIL_R*abs(il_coeff)**2))
# Independent lumped tank prediction from sampled ideal differential drive.
phase=np.arange(N)/N
vbridge=24*((phase<.5).astype(float)-(((phase-.25)%1)<.5).astype(float))
vc=np.fft.rfft(vbridge)/N
w1=2*np.pi*fsw
analytic_i1=vc[1]/(coil_z(w1)+1/(1j*w1*99e-9))
fundamental_check=float(abs(main['branch'][1,coilidx]-analytic_i1)/abs(analytic_i1))
summary=dict(input_power_W=pin,copper_loss_W=loss,coil_DCR_loss_W=coil_loss,total_loss_W=loss+coil_loss,lumped_tank_fundamental_relative= fundamental_check,power_balance_relative=abs(pin-loss-coil_loss)/max(abs(pin),1e-30),model='Ideal-switch periodic harmonic balance coupled to PCB QS, finite harmonic/collocation bandwidth',
 fsw_Hz=fsw,VHB_V=24,phase_deg=90,coil_L_H=COIL_L,coil_R_ohm=COIL_R,coil_parallel_C_F=COIL_CP,coil_SRF_Hz=COIL_SRF,receiver_load=None,
 collocation_samples=N,harmonics=nh,field_time_samples=nt,export_time_frames=64,
 triangles=len(q.tris),loop_count=m['C'].shape[1],port_extraction_s=time.perf_counter()-start,
 coil_peak_A=float(abs(coil).max()),coil_rms_A=float(np.sqrt(np.mean(coil**2))),
 peak_H_Am=float(np.linalg.norm(Ht,axis=-1).max()),boundary_residual=main['residual'],
 harmonic_comparison=dict(coarse_samples=N//2,fine_samples=N,**errors),FFT_grid=info,port_checks=quality,
 phase_sweep={str(p):dict(boundary_residual=v['residual'],coil_peak_A=float(abs(reconstruct(v['branch'])[:,coilidx]).max()),
 coil_rms_A=float(np.sqrt(np.mean(reconstruct(v['branch'])[:,coilidx]**2)))) for p,v in runs.items()},
 assumptions=['Coil: (110 mOhm + 24 uH series) in parallel with 17.801 pF; no receiver or extra AC/core loss. Ideal capacitors/channels, zero dead time, no Coss/diodes',
 '110 kHz and 90 degree phase are explicit demonstration settings, not supplied operating-point measurements',
 'Local ideal stiff VHB feed; upstream filter and bulk network excluded',
 'Slab copper and DC via loss; imported sheet stack; unverified crop/mesh',
 'Field excludes external coil and external feed geometry; local parts are filaments with no copper mutuals',
 'Spectral collocation real-projects Nyquist bin; unresolved ideal switching-edge transients are excluded'])
(out/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary),flush=True)
