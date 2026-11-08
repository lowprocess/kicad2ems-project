"""CPU/ROCm double precision solves of the actual PCB MQS port matrix."""
import gc,json,time
from pathlib import Path
import numpy as np
from scipy.linalg import solve
from threadpoolctl import threadpool_limits
from mom25d.power_bridge import make_board_ports,load_config
from mom25d.mqs_cli import load_board
root=Path(__file__).resolve().parent;out=root/'ports.json';rows={}
def stamp(label,fn):
 t=time.perf_counter();r=fn();rows[label]=time.perf_counter()-t;print(label,rows[label],flush=True);out.write_text(json.dumps(rows,indent=2));return r
cfg=load_config(root.parent/'wpthb-coupled-2026-11-07/model.json');board=load_board(root.parent/'wpthb-inspection-2026-11-07/board.json')
q,ports,crop=stamp('mesh_s',lambda:make_board_ports(board,cfg,log=lambda s:print(s,flush=True)))
with threadpool_limits(limits=8,user_api='blas'):m=stamp('assembly_s',q._assemble)
C=m['C'];offset=len(q.br);sc=np.array([m['src'][offset+i] for i in range(len(q.parts))]);free=np.setdiff1d(np.arange(C.shape[1]),sc);f=110000
Z=m['Rl'].astype(complex)+2j*np.pi*f*m['Ll'];delta=q._resistance_delta(f)
if delta is not None and delta.nnz:Z+=(C.T@delta@C).toarray()
A=np.asfortranarray(Z[np.ix_(free,free)]);B=-Z[np.ix_(free,sc)];D=Z[np.ix_(sc,sc)];E=Z[np.ix_(sc,free)]
rows.update(matrix_shape=list(A.shape),rhs_shape=list(B.shape),dtype=str(A.dtype));del Z,q,m,delta,board;gc.collect()
answers={}
for threads in [1,4,8]:
 with threadpool_limits(limits=threads,user_api='blas'):
  answers[threads]=stamp(f'cpu_{threads}_solve_s',lambda:solve(A.copy(order='F'),B,assume_a='sym',overwrite_a=True,check_finite=False))
X=answers[8];zp=D+E@X;del answers;gc.collect()
import cupy as cp
import cupyx
cp.cuda.Stream.null.synchronize()
rows['GPU']=cp.cuda.runtime.getDeviceProperties(0)['name'].decode();rows['HIP']=cp.cuda.runtime.is_hip
# Warm library initialization on a tiny matrix, separate from actual full matrix transfer/solve.
stamp('gpu_library_warmup_s',lambda:cp.linalg.solve(cp.eye(32,dtype=complex),cp.ones((32,2),dtype=complex)).get())
t=time.perf_counter();a=cp.asarray(A);b=cp.asarray(B);cp.cuda.Stream.null.synchronize();rows['gpu_upload_s']=time.perf_counter()-t
for rep in range(2):
 t=time.perf_counter()
 with cupyx.errstate(linalg='raise'):x=cp.linalg.solve(a,b)
 cp.cuda.Stream.null.synchronize();rows[f'gpu_solve_{rep}_s']=time.perf_counter()-t;print('GPU solve',rep,rows[f'gpu_solve_{rep}_s'],flush=True)
t=time.perf_counter();x=x.get();rows['gpu_download_s']=time.perf_counter()-t
with threadpool_limits(limits=8,user_api='blas'):
 rows['relative_solution_error']=float(np.linalg.norm(x-X)/np.linalg.norm(X));rows['relative_impedance_error']=float(np.linalg.norm((D+E@x)-zp)/np.linalg.norm(zp))
 rows['cpu_residual']=float(np.linalg.norm(A@X-B)/np.linalg.norm(B));rows['gpu_residual']=float(np.linalg.norm(A@x-B)/np.linalg.norm(B))
rows['gpu_e2e_s']=rows['gpu_upload_s']+rows['gpu_solve_0_s']+rows['gpu_download_s'];out.write_text(json.dumps(rows,indent=2));print(json.dumps(rows,indent=2),flush=True)
# FP32 GPU LU with checked FP64 residual/corrections: benchmark only, never silently accept low precision.
import cupyx.scipy.linalg as cla
t=time.perf_counter();lu,piv=cla.lu_factor(a.astype(cp.complex64),overwrite_a=True,check_finite=False);cp.cuda.Stream.null.synchronize();rows['gpu_mixed_factor_s']=time.perf_counter()-t
start=time.perf_counter();xm=cla.lu_solve((lu,piv),b.astype(cp.complex64),check_finite=False).astype(cp.complex128);residuals=[]
for it in range(10):
 residual=b-a@xm;rel=float((cp.linalg.norm(residual)/cp.linalg.norm(b)).get());residuals.append(rel)
 if rel<1e-12:break
 xm+=cla.lu_solve((lu,piv),residual.astype(cp.complex64),check_finite=False)
cp.cuda.Stream.null.synchronize();rows['gpu_mixed_refine_s']=time.perf_counter()-start
xm=xm.get();rows['gpu_mixed_residuals']=residuals;rows['gpu_mixed_relative_solution_error']=float(np.linalg.norm(xm-X)/np.linalg.norm(X));rows['gpu_mixed_relative_impedance_error']=float(np.linalg.norm((D+E@xm)-zp)/np.linalg.norm(zp));rows['gpu_mixed_e2e_s']=rows['gpu_upload_s']+rows['gpu_mixed_factor_s']+rows['gpu_mixed_refine_s'];out.write_text(json.dumps(rows,indent=2));print('MIXED',json.dumps({k:v for k,v in rows.items() if 'mixed' in k}),flush=True)
