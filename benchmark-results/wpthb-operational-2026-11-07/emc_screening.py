"""Screen magnetic coupling from the saved periodic PCB solution; no emission limits."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mom25d.mqs_cli import draw_layout
p=Path(__file__).resolve().parent;d=np.load(p/'time_fields.npz');board=json.loads((p/'mqs_board.json').read_text())
H=d['H_coefficients'];fs=float(d['fsw']);rows=[];maps=[]
for n in range(1,H.shape[-1]):
 # Real-vector maximum over phase of one harmonic. Nyquist is single-sided.
 a=(1 if n==H.shape[-1]-1 else 2)*H[:,:,0,:,n]
 peak=np.sqrt((np.sum(abs(a)**2,axis=-1)+abs(np.sum(a*a,axis=-1)))/2)
 k=np.unravel_index(peak.argmax(),peak.shape);maps.append(peak)
 rows.append(dict(harmonic=n,frequency_Hz=n*fs,spatial_peak_H_Am=float(peak[k]),x_mm=float(d['x'][k[0]]),y_mm=float(d['y'][k[1]])))
fig=plt.figure(figsize=(13,8),layout='constrained');gs=fig.add_gridspec(2,3,height_ratios=[3,1.2]);axs=[]
for j,n in enumerate([1,2,4]):
 ax=fig.add_subplot(gs[0,j]);axs.append(ax);draw_layout(ax,board)
 im=ax.imshow(maps[n-1].T,origin='lower',extent=[d['x'][0],d['x'][-1],d['y'][0],d['y'][-1]],cmap='inferno',vmin=0,vmax=800,alpha=.8,zorder=2)
 ax.set(xlim=(d['x'][0],d['x'][-1]),ylim=(d['y'][0],d['y'][-1]),aspect='equal',xlabel='x (mm)',ylabel='y (mm)',title=f'{n*fs/1000:g} kHz: spatial peak {rows[n-1]["spatial_peak_H_Am"]:.0f} A/m')
fig.colorbar(im,ax=axs,label='Peak |Hn(t)| at top + 1 mm (A/m)',shrink=.8)
ax=fig.add_subplot(gs[1,:]);n=np.arange(1,33);vals=np.array([r['spatial_peak_H_Am'] for r in rows[:32]])
for mask,label,col in [(n%2==1,'Odd harmonics','#4b79b4'),(n%2==0,'Even harmonics','#d66d32')]:ax.semilogy(n[mask]*fs/1e6,vals[mask],'o-',ms=4,label=label,color=col,lw=1)
ax.set(xlabel='Frequency (MHz)',ylabel='Spatial maximum H (A/m)',title='Each point is the maximum over the sampled plane; this is not a receiver spectrum');ax.grid(alpha=.25,which='both');ax.legend()
fig.suptitle('Magnetic EMC screening: PCB only · 24 V / 110 kHz / 90° · external coil and cables omitted')
fig.savefig(p/'emc-screening.png',dpi=150)
result=dict(scope='Magnetic near-field coupling screen; not a conducted/radiated compliance assessment',operating_point=dict(VHB_V=24,fsw_Hz=fs,phase_deg=90),height_above_top_mm=1,harmonics=rows,limitations=['External coil, receiver, feed harness and enclosure absent','No distributed electric-field or common-mode displacement current solution','Ideal switches, no Coss/deadtime/diode commutation or realistic rise/fall times','Harmonic comparison: 41.4% global component-peak difference including edges; 8.76% away from edges','No input filter/LISN model, detector bandwidth or applicable emission standard'])
(p/'emc-screening.json').write_text(json.dumps(result,indent=2));print('Saved EMC screening plot and harmonic data')
