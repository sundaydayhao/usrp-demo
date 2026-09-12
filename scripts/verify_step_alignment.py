"""Compare the delivered EasyEDA STEP/WRL geometry bounds after normalization."""
from pathlib import Path
import sys,re,json
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tmp/tools/occ'))
from OCP.STEPControl import STEPControl_Reader
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
files=[ROOT/'projects/BasicRX/3dmodels/EasyEDA_XFMR-SMD_6P-L7.9-W5.6-P2.54-LS7.0-BL.step',ROOT/'projects/WBX/3dmodels/EasyEDA_XFMR-SMD_TC1-1TX.step',ROOT/'projects/WBX/3dmodels/EasyEDA_CONN-SMD_QTE-020-01-F-D.step']
report=[]
for p in files:
 r=STEPControl_Reader();r.ReadFile(str(p));r.TransferRoots();b=Bnd_Box();BRepBndLib.AddOptimal_s(r.OneShape(),b);a=p.with_suffix('.wrl').read_text();pts=[]
 for block in re.findall(r'point\s*\[([^]]+)\]',a,re.S):
  nums=list(map(float,re.findall(r'-?\d*\.?\d+(?:[eE][-+]?\d+)?',block)));pts.extend([nums[i:i+3] for i in range(0,len(nums),3)])
 step=[(t.X(),t.Y(),t.Z()) for t in [b.CornerMin(),b.CornerMax()]];wrl=[[fn(a[k] for a in pts)*2.54 for k in range(3)] for fn in [min,max]];err=max(abs(step[i][j]-wrl[i][j]) for i in range(2) for j in range(3));assert err<=.0011,(p,err)
 report.append({'file':p.relative_to(ROOT).as_posix(),'STEP_bounds_mm':step,'WRL_bounds_mm':wrl,'maximum_bound_difference_mm':err,'pass':True});print(p.name,round(err,6),'mm',flush=True)
(ROOT/'verification/3d-import-alignment.json').write_text(json.dumps({'units':'mm','tolerance_mm':.0011,'models':report},indent=2))
