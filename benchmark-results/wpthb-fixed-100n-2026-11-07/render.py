import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
p=Path(__file__).resolve().parent;s=json.loads((p/'linear-sweep.json').read_text());r=json.loads((p/'circuit-results.json').read_text())
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
f=np.array(s['frequencies_Hz'])/1000;power=np.array(s['power_W']);freq=sorted(r['frequency'],key=lambda c:c['target_W'])
fig,ax=plt.subplots(3,1,figsize=(10,9),layout='constrained',sharex=True)
ax[0].plot(f,power,label='Fundamental estimate, full bipolar drive (180°)',color='#2879af');ax[0].plot(f,power/2,'--',label='Fundamental estimate, 90° phase',color='#888888')
ax[0].scatter([c['frequency_Hz']/1000 for c in freq],[c['load_power_W'] for c in freq],color='#db6826',label='Detailed transient: frequency-only operating points',zorder=5)
provisional=next(c for c in freq if c['target_W']==10)
ax[0].scatter([provisional['frequency_Hz']/1000],[provisional['load_power_W']],facecolors='white',edgecolors='#db6826',zorder=6,label='Open marker: 10 W timestep-sensitive')
ax[0].set(ylabel='Delivered AC power (W)',title='Fixed 100 nF on both sides · 24 µH coils · k=0.4 · fixed 6.45 Ω receiver')
for peak in s['loaded_power_peak_Hz']:
 i=np.argmin(abs(f-peak/1000));ax[0].annotate(f'{peak/1000:.1f} kHz',(f[i],power[i]),xytext=(0,-18),textcoords='offset points',ha='center')
ax[1].plot(f,np.array(s['link_efficiency'])*100,label='Sinusoidal link efficiency',color='#39874a')
ax[1].scatter([c['frequency_Hz']/1000 for c in freq],[100*c['efficiency'] for c in freq],color='#db6826',label='Full-circuit electrical efficiency, frequency-only cases',zorder=5);ax[1].set(ylabel='Efficiency (%)',ylim=(65,100))
ax[1].scatter([provisional['frequency_Hz']/1000],[100*provisional['efficiency']],facecolors='white',edgecolors='#db6826',zorder=6)
ax[2].plot(f,s['input_X_ohm'],color='#a14b8e');ax[2].axhline(0,color='grey',lw=.8);ax[2].set(ylabel='Link input reactance (Ω)',xlabel='Drive frequency (kHz)',ylim=(-20,20))
for a in ax:
 a.axvspan(70,110,color='#e5edf4',alpha=.35,zorder=-2);a.axvline(90,color='#777777',ls=':',lw=.8);a.axvline(110,color='#777777',ls=':',lw=.8);a.grid(alpha=.2)
ax[0].legend(fontsize=8);ax[1].legend(fontsize=8)
fig.savefig(p/'fixed-cap-frequency-sweep.png',dpi=150);plt.close(fig)
fig,ax=plt.subplots(1,2,figsize=(11,4),layout='constrained')
for rows,label,col in [(freq,'Frequency only, full bipolar drive','#db6826'),(sorted([c for c in r['phase'] if c['frequency_Hz']==90000],key=lambda c:c['target_W']),'90 kHz, phase controlled','#2879af'),(sorted([c for c in r['phase'] if c['frequency_Hz']==110000],key=lambda c:c['target_W']),'110 kHz, phase controlled','#39874a')]:
 x=[c['load_power_W'] for c in rows];ax[0].plot(x,[c['primary_rms_A'] for c in rows],'o-',label=label,color=col);ax[1].plot(x,[100*c['efficiency'] for c in rows],'o-',label=label,color=col)
ax[0].set(ylabel='Primary winding RMS current (A)',xlabel='Delivered AC power (W)');ax[1].set(ylabel='Electrical efficiency (%)',xlabel='Delivered AC power (W)')
for a in ax:a.grid(alpha=.2);a.legend(fontsize=8)
fig.suptitle('Same fixed capacitors and receiver load: frequency control versus phase control')
ax[0].scatter([provisional['load_power_W']],[provisional['primary_rms_A']],facecolors='white',edgecolors='#db6826',zorder=6)
ax[1].scatter([provisional['load_power_W']],[100*provisional['efficiency']],facecolors='white',edgecolors='#db6826',zorder=6)
fig.set_layout_engine('constrained',rect=(0,.1,1,.9));fig.text(.5,.035,'Open frequency-control marker: 10 W point has unresolved timestep convergence',ha='center',fontsize=8);fig.text(.5,.004,'24 V, k=0.4, fixed 6.45 Ω AC load · Generic part models · Ideal PCB interconnects · No rectifier/logic losses',ha='center',fontsize=8)
fig.savefig(p/'control-comparison.png',dpi=150);plt.close(fig)
print('Rendered fixed-compensation comparison')
