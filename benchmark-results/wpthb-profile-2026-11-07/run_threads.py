import subprocess,sys
from pathlib import Path
p=Path(__file__).with_name('profile.py')
for name,options in [('klu-t4-8',['--threads','4']),('klu-t8-8',['--threads','8']),('sparse-t1-8',['--solver','sparse']),('klu-solve-t1-8',['--output','solve'])]:
 r=subprocess.run([sys.executable,str(p),'--name',name,'--cpu','2,4,6,8,10,12,14,0',*options],check=True,stdout=subprocess.PIPE,text=True)
 print(r.stdout,flush=True)
