"""Generate the profiling summary and CPU/GPU comparison figure from recorded runs."""
import json,re
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
p=Path(__file__).resolve().parent
load=lambda file:json.loads((p/file).read_text())
runs={name:load(f'{name}/timing.json') for name in ['klu-t1-8','klu-t4-8','klu-t8-8','sparse-t1-8','klu-solve-t1-8','full52-klu-t1']}
log=(p/'full52-klu-t1/ngspice.log').read_text();stats={}
for key,label in dict(analysis_s='Total analysis time (seconds)',load_s='Matrix load time',factor_s='Matrix factor time',solve_s='Matrix solve time',equations='Circuit Equations',iterations='Total iterations',accepted_steps='Accepted timepoints',rejected_steps='Rejected timepoints').items():
 stats[key]=float(re.findall('^'+re.escape(label)+r'\s*=\s*([+\-0-9.eE]+)',log,re.M)[0])
elapsed=[float(v) for v in re.findall(r'^Total elapsed time \(seconds\)\s*=\s*([\d.]+)',log,re.M)]
stats['output_s']=elapsed[-1]-elapsed[0];stats['factor_fraction']=stats['factor_s']/stats['analysis_s'];stats['rejected_fraction']=stats['rejected_steps']/(stats['rejected_steps']+stats['accepted_steps'])
old=p.parent/'wpthb-coupled-2026-11-07/110kHz_30W';labels=list(json.loads((old/'signals.json').read_text()));t=np.loadtxt(p/'full52-klu-t1/transient.dat',skiprows=1)
with np.load(old/'transient.npz') as original:
 checks={}
 for label in ['PRIMARY.winding_I','SECONDARY.winding_I','load.V','bus.V',*[f'PCB{i}.I' for i in range(24)]]:
  a=t[:,labels.index(label)+1];b=original[label]
  checks[label]=float(np.max(abs(a-b))/max(np.max(abs(b)),1e-30))
 checks['time_max_abs_s']=float(np.max(abs(t[:,0]-original['time_s'])))
ports=load('ports.json');batch=load('batch.json');summary=dict(hardware=dict(CPU='Intel Core i7-13700K',GPU='AMD Radeon RX 7800 XT 16 GB',RAM_GiB=32),case=dict(frequency_Hz=110000,target_W=30,phase_deg=90.81656384594943,copper_ports=24,triangles=13528,RWG_edges=18245,via_segments=267,loops=8672,free_loop_equations=8648,modal_states=66),runs=runs,transient_stats=stats,batch=batch,port_solve=ports,full52_regression_relative_waveform_errors=checks)
summary['GPU_mixed_speedup_over_best_CPU']=min(ports[f'cpu_{n}_solve_s'] for n in [1,4,8])/ports['gpu_mixed_e2e_s']
(p/'summary.json').write_text(json.dumps(summary,indent=2))
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
fig,ax=plt.subplots(1,3,figsize=(15,5.2));blue='#3479ad';green='#27876b'
def bars(a,labels,values,colors):
 a.barh(labels,values,color=colors,height=.62);a.invert_yaxis();a.set_xlabel('Wall time (seconds)');a.set_xlim(0,max(values)*1.21);a.grid(axis='x',alpha=.2);a.set_axisbelow(True)
 for i,v in enumerate(values):a.text(v+max(values)*.018,i,f'{v:.2f}',va='center',fontsize=10)
bars(ax[0],['KLU / 1 thread','KLU / 4 threads','KLU / 8 threads','Sparse / 1 thread'],[runs[n]['wall_s'] for n in ['klu-t1-8','klu-t4-8','klu-t8-8','sparse-t1-8']],[blue]*4);ax[0].set_title('Single PCB-coupled transient\n8 cycles; identical circuit/tolerances')
bars(ax[1],['Sequential','4 parallel cases'],[batch['1']['wall_s'],batch['4']['wall_s']],[blue,green]);ax[1].set_title(f'Four transient runs (8 cycles each)\n{batch["speedup"]:.2f}× speedup; identical waveforms')
bars(ax[2],['CPU / 1 BLAS thread','CPU / 4 BLAS threads','CPU / 8 BLAS threads','GPU / FP64','GPU / mixed precision'],[ports['cpu_1_solve_s'],ports['cpu_4_solve_s'],ports['cpu_8_solve_s'],ports['gpu_e2e_s'],ports['gpu_mixed_e2e_s']],[blue,blue,blue,green,green]);ax[2].set_title('PCB extraction at 110 kHz\n8,648 equations × 24 RHS\nGPU prototype')
fig.suptitle('WPT H-bridge PCB-coupled simulation profiling — i7-13700K / RX 7800 XT',fontsize=14)
fig.text(.5,.025,'Shared meshing/extraction, phase targeting and field export are excluded from transient timing bars. GPU includes transfers; library warmup excluded.',ha='center',fontsize=9)
fig.tight_layout(rect=(0,.06,1,.92));fig.savefig(p/'runtime-comparison.png',dpi=160)
print(json.dumps(dict(stats=stats,full52_wall_s=runs['full52-klu-t1']['wall_s'],max_waveform_error=max(v for k,v in checks.items() if k!='time_max_abs_s'),mixed_speedup=summary['GPU_mixed_speedup_over_best_CPU'],batch_speedup=batch['speedup']),indent=2))
