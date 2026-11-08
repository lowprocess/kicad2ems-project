"""Render the computed periodic QS fields, rather than animating one phasor."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation,PillowWriter,FFMpegWriter
from matplotlib.patches import Polygon
from shapely.geometry import shape
from mom25d.mqs_cli import draw_layout
out=Path(__file__).resolve().parent
s=json.loads((out/'summary.json').read_text());d=np.load(out/'time_fields.npz');layout=json.loads((out/'mqs_board.json').read_text())
t=d['time_s']*1e6;T=1e6/float(d['fsw']);theta=d['time_s']*float(d['fsw']);H=d['H'];mag=np.linalg.norm(H,axis=-1)
a=theta<.5;b=((theta-.25)%1)<.5;vb=24*(a.astype(float)-b.astype(float));on=np.stack([b,a,~b,~a],axis=1)
names=list(d['part_names']);nb=d['branch_currents_A'].shape[1]-len(names)
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
fig=plt.figure(figsize=(12,9),layout='constrained');fig.set_layout_engine('constrained',rect=(0,.035,1,.965));gs=fig.add_gridspec(3,2,height_ratios=[4,1.25,1.5])
axes=[fig.add_subplot(gs[0,j]) for j in range(2)];ims=[];patches=[]
for j,ax in enumerate(axes):
 draw_layout(ax,layout)
 im=ax.imshow(mag[0,:,:,j].T,origin='lower',extent=[d['x'][0],d['x'][-1],d['y'][0],d['y'][-1]],vmin=0,vmax=mag[:,:,:,j].max(),cmap='inferno',alpha=.77,zorder=2,interpolation='bilinear');ims.append(im)
 ax.set(xlabel='x (mm)',ylabel='y (mm)',title=f'PCB |H(t)|, {j*2+1} mm above top copper',aspect='equal',xlim=(d['x'][0],d['x'][-1]),ylim=(d['y'][0],d['y'][-1]))
 pp=[]
 for ref in ['Q1','Q2','Q3','Q4']:
  c=next(c for c in layout['components'] if c['ref']==ref);poly=shape(c['polygon']);p=Polygon(poly.exterior.coords,fill=False,ec='#28ed88',lw=2.4,zorder=7);ax.add_patch(p);pp.append(p)
 patches.append(pp)
for ax,im in zip(axes,ims):fig.colorbar(im,ax=ax,label='H (A/m); fixed per height through cycle',shrink=.85)
axv=fig.add_subplot(gs[1,:]);axv.step(np.r_[t,T],np.r_[vb,vb[0]],where='post',color='#315ca8',lw=1.8,label='Ideal bridge differential command')
axv.set(ylabel='Bridge (V)',ylim=(-29,29),xlim=(0,T));axv.set_xticklabels([]);axv.grid(alpha=.2);axv.legend(loc='upper right')
axi=fig.add_subplot(gs[2,:]);axi.plot(np.r_[t,T],np.r_[d['coil_A'],d['coil_A'][0]],color='#c4422b',lw=2,label='Coil winding current')
for ref,col in [('Q2','#337aa3'),('Q3','#3d8c49')]:
 wave=d['branch_currents_A'][:,nb+names.index(ref)]
 axi.plot(np.r_[t,T],np.r_[wave,wave[0]],color=col,lw=1,alpha=.7,label=f'{ref} channel current')
axi.set(xlabel='Time in switching period (µs)',ylabel='Current (A)',xlim=(0,T));axi.grid(alpha=.2);axi.legend(loc='upper right',ncol=3)
lines=[axv.axvline(0,color='#101010',lw=1),axi.axvline(0,color='#101010',lw=1)]
header=fig.suptitle('')
fig.text(.5,.003,'24 µH + 110 mΩ series, shunted by 17.8 pF · 99 nF series bank · No receiver · External coil/feed fields excluded',ha='center',fontsize=9)
def update(k):
 for j,im in enumerate(ims):
  im.set_data(mag[k,:,:,j].T)
  for n,p in enumerate(patches[j]):p.set_edgecolor('#1deb77' if on[k,n] else '#858585');p.set_linewidth(3 if on[k,n] else 1)
 for line in lines:line.set_xdata([t[k],t[k]])
 state='/'.join(np.array(['Q1','Q2','Q3','Q4'])[on[k]])
 header.set_text(f'wpthb: 24 V · 110 kHz · 90° phase shift   |   t = {t[k]:.3f} µs   |   ON: {state}')
 return [*ims,*lines,header]
update(80);fig.savefig(out/'operating-fields.png',dpi=160)
an=FuncAnimation(fig,update,frames=np.arange(0,len(t),4),interval=75,blit=False)
an.save(out/'operating-fields.gif',writer=PillowWriter(fps=12),dpi=85)
an.save(out/'operating-fields.mp4',writer=FFMpegWriter(fps=12,bitrate=1800),dpi=100)
plt.close(fig)
# A signed component makes direction reversals explicit, using a common symmetric scale.
fig,axs=plt.subplots(2,4,figsize=(14,8),layout='constrained');hz=H[:,:,:,0,2];hm=abs(hz).max()
for ax,k in zip(axs.flat,np.arange(16,256,32)):
 draw_layout(ax,layout);im=ax.imshow(hz[k].T,origin='lower',extent=[d['x'][0],d['x'][-1],d['y'][0],d['y'][-1]],cmap='RdBu_r',vmin=-hm,vmax=hm,alpha=.75,zorder=2)
 ax.set(xlim=(d['x'][0],d['x'][-1]),ylim=(d['y'][0],d['y'][-1]),title=f't/T = {k/256:.3f}',aspect='equal',xlabel='x (mm)',ylabel='y (mm)')
fig.colorbar(im,ax=axs,label='Signed Hz (A/m), top + 1 mm',shrink=.8)
fig.suptitle('Direction of the computed PCB magnetic field through one switching period')
fig.savefig(out/'signed-field-phases.png',dpi=140);plt.close(fig)
# Document what was actually simulated; a periodic solution has no startup transient.
ph=[int(p) for p in s['phase_sweep']];ir=[s['phase_sweep'][str(p)]['coil_rms_A'] for p in ph]
fig,ax=plt.subplots(figsize=(7,4),layout='constrained');ax.plot(ph,ir,'o-');ax.set(xlabel='Bridge phase shift (degrees)',ylabel='Coil terminal RMS current (A)',title='Unloaded resonant tank at 24 V, 110 kHz');ax.grid(alpha=.3)
fig.savefig(out/'phase-sweep.png',dpi=150);plt.close(fig)
print('Rendered computed time-domain fields:',out,flush=True)
