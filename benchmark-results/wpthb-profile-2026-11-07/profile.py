"""Reproducible frozen PCB-coupled netlist profiler; no physics/tolerance changes."""
import argparse,json,os,re,subprocess,time,resource
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--name',required=True);p.add_argument('--threads',type=int,default=1);p.add_argument('--solver',choices=['klu','sparse'],default='klu');p.add_argument('--cycles',type=int,default=8);p.add_argument('--output',choices=['full','solve'],default='full');p.add_argument('--perf',action='store_true');p.add_argument('--cpu',default='');args=p.parse_args()
root=Path(__file__).resolve().parent;out=root/args.name;out.mkdir(exist_ok=True)
source=root.parent/'wpthb-coupled-2026-11-07/110kHz_30W/circuit.cir';s=source.read_text();stop=args.cycles/110000
s=s.replace('set klu',('set klu' if args.solver=='klu' else 'unset klu')+f'\nset num_threads={args.threads}')
s=re.sub(r'^tran (\S+) \S+ (.*)$',rf'tran \1 {stop:.17g} \2',s,flags=re.M)
s=re.sub(r'from=\S+ to=\S+',f'from={stop-1/110000:.17g} to={stop:.17g}',s)
s=s.replace('\nlet out0=', '\necho PROFILE_AFTER_TRAN\nrusage all\nlet out0=')
if args.output=='solve':s=s[:s.index('\nlet out0=')]+'\nquit\n.endc\n.end\n'
else:s=s.replace('\nlinearize ', '\nset filetype=binary\nwrite adaptive-ports.raw '+' '.join(f'out{i}' for i in range(1,48,2))+'\nset filetype=ascii\nlinearize ')
s=s.replace('\nquit\n','\necho PROFILE_AFTER_OUTPUT\nrusage all\nquit\n');(out/'circuit.cir').write_text(s)
cmd=['ngspice','-b','circuit.cir']
if args.cpu:cmd=['taskset','-c',args.cpu,*cmd]
if args.perf:cmd=['perf','record','-F','199','-e','cycles:u','--call-graph','dwarf,8192','-o','perf.data','--',*cmd]
env=dict(os.environ,OMP_NUM_THREADS=str(args.threads),OPENBLAS_NUM_THREADS='1');start=time.perf_counter()
with (out/'ngspice.log').open('w') as log:r=subprocess.run(cmd,cwd=out,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=900)
elapsed=time.perf_counter()-start;ru=resource.getrusage(resource.RUSAGE_CHILDREN);log=(out/'ngspice.log').read_text()
row=dict(vars(args),wall_s=elapsed,user_s=ru.ru_utime,system_s=ru.ru_stime,max_rss_KiB=ru.ru_maxrss,returncode=r.returncode,aborted='simulation(s) aborted' in log,measurements={k:float(v) for k,v in re.findall(r'^(m\d+)\s*=\s*([-+\deE.]+)',log,re.M)},source=str(source));(out/'timing.json').write_text(json.dumps(row,indent=2));print(json.dumps(row),flush=True)
