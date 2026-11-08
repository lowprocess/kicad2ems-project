"""QS characterizations of wpthb switching-state current paths, normalized to 1 A coil-port current.
No bus voltage, phase shift, receiver loading or external coil spatial field is assumed.
"""
import json,time,hashlib,copy,os
from pathlib import Path
import numpy as np
from shapely.geometry import shape
from shapely.ops import unary_union
from mom25d.mqs import MQS
from mom25d.pdn.rail import parts_of,part_value
from mom25d.mqs_layout import save_layout,geometry,mesh_stats

work=Path(__file__).resolve().parent
out=work/os.environ.get('QS_OUT','');out.mkdir(parents=True,exist_ok=True)
board_path=work.parent/'wpthb-inspection-2026-11-07/board.json'
b=json.loads(board_path.read_text());parts={p.ref:p for p in parts_of(b)}
N={'VHB','GND','/HL_SW','/HR_SW','/HL_AC'}
caprefs=['C19','C20','C21','C22','C23','C24','C25','C27','C30']
refs=['Q1','Q2','Q3','Q4','TP14','TP15',*caprefs]
terms={}
for ref in refs:
 for net in sorted(parts[ref].nets() & N):
  terms[f'{ref}:{net}']=[(l,p.geom) for p in parts[ref].on({net}) for l in p.layers]
extent=unary_union([p for pp in terms.values() for _,p in pp]);crop=extent.buffer(2).envelope
start=time.perf_counter()
dmax=float(os.environ.get('QS_DMAX','3'));fine=float(os.environ.get('QS_FINE','1.6'))
q=MQS(b,N,terminals=terms,region=crop,dmax=dmax,fine=extent.buffer(.6).envelope,dmax_fine=fine,
      fill_backend='openmp',fill_workers=8,conductor_loss='slab',conductor_faces=2,log=lambda *a:print(*a,flush=True))
nt,ne=len(q.tris),q.ne
estimate=32*nt*nt+24*ne*ne
pre=dict(triangles=nt,edges=ne,vias=q.nv,crop_mm=list(crop.bounds),mesh_s=time.perf_counter()-start,
         dmax_mm=dmax,fine_mm=fine,dense_work_estimate_GB=estimate/1e9,layers=mesh_stats(q))
(out/'preflight.json').write_text(json.dumps(pre,indent=2));print('preflight',json.dumps(pre),flush=True)
if os.environ.get('QS_PREFLIGHT'):raise SystemExit(0)
if estimate>17e9:raise RuntimeError('Estimated dense work exceeds this run budget; use a coarser preflight mesh')
# Explicit nominal capacitor values; zero ESR/ESL and ideal conducting channels.
for ref in caprefs:
 nets=sorted(parts[ref].nets() & N)
 if len(nets)!=2:raise ValueError((ref,nets))
 q.element(ref,ref+':'+nets[0],ref+':'+nets[1],C=part_value(parts[ref]),part_h=0)
baseparts=copy.deepcopy(q.parts)
states={'diagonal_Q2_Q3':['Q2','Q3'],'diagonal_Q1_Q4':['Q1','Q4'],
        'freewheel_low_Q3_Q4':['Q3','Q4'],'freewheel_high_Q1_Q2':['Q1','Q2']}
ends={'Q1':('VHB','/HR_SW'),'Q2':('VHB','/HL_SW'),'Q3':('/HR_SW','GND'),'Q4':('/HL_SW','GND')}
if os.environ.get('QS_CASES'):states={k:v for k,v in states.items() if k in os.environ['QS_CASES'].split(',')}
freqs=np.array([float(x) for x in os.environ.get('QS_FREQS','70000,80000,90000,100000,103251.62929593983,110000').split(',')]);primary=int(np.argmin(abs(freqs-100e3)))
x=np.linspace(crop.bounds[0],crop.bounds[2],25);y=np.linspace(crop.bounds[1],crop.bounds[3],25)
top=max(c['z'] for c in b['stack']['copper']);heights=np.array([1.,3.,5.])
coilR=2*np.pi*125e3*24e-6/155
report=dict(kind='Normalized switching-state QS characterization, not phase-shift steady-state simulation',
    source_sha256=hashlib.sha256(board_path.read_bytes()).hexdigest(),frequencies_Hz=freqs.tolist(),mesh=pre,
    drive='1 A peak phasor through external coil port TP15 (A) -> TP14 (B) in every state',
    assumptions=dict(on_channel_R_ohm=0,off_channels='open; no Coss or diode conduction',
        capacitor_ESR_ohm=0,capacitor_ESL_H=0,L3_DCR_ohm=0,part_filament_height_mm=0,
        conductor_loss='two-face slab; vias DC',coil_L_H=24e-6,coil_R_ohm=coilR,
        coil_R_model='constant small-signal total series loss anchored by Q=155 at 125 kHz; receiver absent',
        field_scope='PCB sheets/vias and local lumped-part filaments; external coil/source filament excluded',
        bus_voltage_V=24.,phase_shift_deg=None,receiver_reflected_impedance=None,
        copper_model='imported sheet-plane stack z; nominal foil 35 um',input_boundary='local VHB capacitor bank; upstream L3/VBUS/bulk network excluded from crop'),states={})
for case,on in states.items():
 q.parts=copy.deepcopy(baseparts);q._mats=None;q._peec=None
 for ref in on:
  a,c=ends[ref];q.element(ref,ref+':'+a,ref+':'+c,R=0,part_h=0)
 q.source('COIL_PORT','TP15:/HL_AC','TP14:/HR_SW',part_h=0)
 t=time.perf_counter();r=q.solve(freqs);solve_s=time.perf_counter()-t
 print(case,'solved',solve_s,flush=True)
 # Continuity at every physical terminal/triangle node, including all branches.
 from scipy.sparse import coo_matrix
 e=q.br+[(q.term_node[p['a']],q.term_node[p['b']]) for p in q.parts]
 a,c=np.array(e).T;k=np.arange(len(e))
 A=coo_matrix((np.r_[np.ones(len(e)),-np.ones(len(e))],(np.r_[a,c],np.r_[k,k])),shape=(q.n_nodes,len(e))).tocsr()
 residual=float(abs(A@r.i.T).max())
 if residual>1e-7:raise RuntimeError('KCL failed')
 # Source is an external port, not a straight physical wire between the coil pads.
 field=copy.copy(r);field.i=r.i.copy();field.i[:,-1]=0
 t=time.perf_counter()
 H,info=q.h_grid(field,list(range(len(freqs))),x*.001,y*.001,(top+heights)*.001,rtol=.02,return_info=True)
 field_s=time.perf_counter()-t
 X,Y,Z=np.meshgrid(x[::6]*.001,y[::6]*.001,(top+heights)*.001,indexing='ij')
 points=np.stack([X,Y,Z],axis=-1).reshape(-1,3)
 direct=q.h_field(field,primary,points).reshape(5,5,3,3)
 error=float(abs(H[::6,::6,:,: ,primary]-direct).max()/abs(direct).max())
 print(case,'field',field_s,'KCL',residual,'direct error',error,flush=True)
 dest=out/case;dest.mkdir(exist_ok=True)
 selected=dict(converter=case,capacitors=[*caprefs,*on,'TP14','TP15'])
 layout=save_layout(dest,b,q,crop,selected)
 # Only actual conducting channels/selected passives highlighted, not the state label.
 for c in layout['components']:c['active']=c['ref'] in {*caprefs,*on,'TP14','TP15'}
 (dest/'mqs_board.json').write_text(json.dumps(layout));g=geometry(layout)
 from kicad2ems.api.solver import Dump,write_npz
 exc=dest/'mqs'/'exc_coil';exc.mkdir(parents=True,exist_ok=True);dumps=[]
 for hi,h in enumerate(heights):
  z=top+h;dm=Dump('H@top+'+str(h)+'mm','H',(x[0],y[0],z),(x[-1],y[-1],z),freqs.tolist(),2,f'top+{h:g}mm')
  write_npz(exc/(dm.name+'.npz'),dict(x=x,y=y,z=[z]),freqs,np.moveaxis(H[:,:,hi:hi+1],-1,0))
  dumps.append(dict(name=dm.name,spec=dm.spec,field='H',label=dm.label,normal=2,freqs=freqs.tolist(),
                    start=dm.start.tolist(),stop=dm.stop.tolist(),unit='A/m per A'))
 dm=Dump('H@volume','H',(x[0],y[0],top+heights[0]),(x[-1],y[-1],top+heights[-1]),freqs.tolist(),None,'volume')
 write_npz(exc/(dm.name+'.npz'),dict(x=x,y=y,z=top+heights),freqs,np.moveaxis(H,-1,0))
 dumps.append(dict(name=dm.name,spec=dm.spec,field='H',label='volume',normal=None,freqs=freqs.tolist(),
                   start=dm.start.tolist(),stop=dm.stop.tolist(),unit='A/m per A'))
 (exc/'dump_info.json').write_text(json.dumps(dict(g,dumps=dumps)))
 J=np.array([q.current_density(r,i)['F.Cu'][1] for i in range(len(freqs))])
 np.savez_compressed(dest/'currents_fields.npz',freqs=freqs,I=r.i,J_top=J,H=H,x=x,y=y,heights=heights,
                     nodes=q.nodes,tris=q.tris,layer_of=q.layer_of,part_names=np.array([p['name'] for p in q.parts]))
 z=r.z['COIL_PORT'];zc=r.zc['COIL_PORT'];zt=z+coilR+1j*2*np.pi*freqs*24e-6
 partI={p['name']:dict(real=r.i[:,len(q.br)+k].real.tolist(),imag=r.i[:,len(q.br)+k].imag.tolist()) for k,p in enumerate(q.parts)}
 record=dict(on_channels=on,loop_count=q._mats['C'].shape[1],solve_s=solve_s,field_s=field_s,
    copper_R_ohm=zc.real.tolist(),copper_L_H=(zc.imag/(2*np.pi*freqs)).tolist(),
    board_network_Z_ohm=dict(real=z.real.tolist(),imag=z.imag.tolist()),
    board_plus_coil_Z_ohm=dict(real=zt.real.tolist(),imag=zt.imag.tolist()),
    peak_H_Am_per_A=np.linalg.norm(H,axis=3).max(axis=(0,1)).T.tolist(),
    KCL_max_A=residual,FFT_grid=info,direct_peak_relative_error=error,part_currents_per_A=partI)
 report['states'][case]=record
 (out/'summary.json').write_text(json.dumps(report,indent=2))
print('done',flush=True)
