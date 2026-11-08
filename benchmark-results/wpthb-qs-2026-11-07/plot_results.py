import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
from mom25d.mqs_cli import draw_layout
out=Path(__file__).resolve().parent;r=json.loads((out/'summary.json').read_text());f=np.array(r['frequencies_Hz']);idx=int(np.argmin(abs(f-100e3)))
fig,axes=plt.subplots(2,2,figsize=(12,10));names=list(r['states']);data=[np.load(out/n/'currents_fields.npz') for n in names]
hi=max(np.linalg.norm(d['H'][:,:,0,:,idx],axis=2).max() for d in data);norm=LogNorm(hi/100,hi)
for ax,name,d in zip(axes.flat,names,data):
 mag=np.linalg.norm(d['H'][:,:,0,:,idx],axis=2)
 im=ax.pcolormesh(d['x'],d['y'],mag.T,norm=norm,cmap='inferno',shading='auto',alpha=.75)
 draw_layout(ax,json.loads((out/name/'mqs_board.json').read_text()))
 ax.set(xlabel='model x (mm)',ylabel='model y (mm)',aspect='equal',title=name.replace('_',' '))
fig.suptitle('wpthb QS board contribution at 100 kHz, 1 mm above top copper\n1 A peak coil-port excitation; external coil and leads excluded')
fig.subplots_adjust(right=.87,wspace=.25,hspace=.25)
fig.colorbar(im,cax=fig.add_axes([.90,.15,.018,.68]),label='|H|, A/m per A (peak)')
fig.savefig(out/'state-field-overlays.png',dpi=160)
fig,ax=plt.subplots(1,3,figsize=(14,4))
for name,s in r['states'].items():
 label=name.replace('diagonal_','diag ').replace('freewheel_','free ').replace('_',' ')
 ax[0].plot(f/1000,np.array(s['copper_R_ohm'])*1e3,'o-',label=label)
 ax[1].plot(f/1000,np.array(s['copper_L_H'])*1e9,'o-',label=label)
 ax[2].plot(f/1000,s['board_plus_coil_Z_ohm']['imag'],'o-',label=label)
for a in ax:a.set_xlabel('Frequency (kHz)');a.grid(alpha=.2)
ax[0].set_ylabel('Copper contribution R (mΩ)');ax[1].set_ylabel('Copper contribution L (nH)');ax[2].set_ylabel('Board + nominal coil reactance (Ω)')
ax[2].axhline(0,color='grey',lw=.7);ax[0].legend(fontsize=8)
fig.suptitle('Fixed-conduction-state characterization; no receiver load, ideal on-channels/capacitors')
fig.tight_layout();fig.savefig(out/'impedance-sweep.png',dpi=160)
