"""Exercise real CLI SIGTERM with concurrent ngspice children and queued cases."""
import json,os,signal,subprocess,sys,time
from pathlib import Path
p=Path(__file__).resolve().parent
cfg=json.loads((p/'smoke-model.json').read_text());cfg['powers_W']=[5,10,20,30];(p/'cancel-model.json').write_text(json.dumps(cfg))
env=dict(os.environ,OPENBLAS_NUM_THREADS='1');found=set()
with (p/'cancel-cli.log').open('w') as log:
 child=subprocess.Popen([sys.executable,'-u','-m','mom25d.power_circuit',str(p/'cancel-model.json'),'--out',str(p/'cancel-cli'),'--jobs','2'],stdout=log,stderr=subprocess.STDOUT,env=env)
 try:
  deadline=time.monotonic()+10
  while time.monotonic()<deadline and child.poll() is None:
   for file in Path(f'/proc/{child.pid}/task').glob('*/children'):
    try:found.update(map(int,file.read_text().split()))
    except FileNotFoundError:pass
   if len(found)>=2:break
   time.sleep(.02)
  assert len(found)>=2,found
  child.send_signal(signal.SIGTERM);returncode=child.wait(timeout=5)
  orphaned=[pid for pid in found if Path(f'/proc/{pid}').exists()]
  assert not orphaned,orphaned
  result=dict(status='passed',children_seen=sorted(found),parent_returncode=returncode,orphaned=orphaned)
  (p/'cancellation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
 finally:
  if child.poll() is None:child.kill();child.wait()
