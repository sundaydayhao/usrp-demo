"""Export portable schematic, copper and assembly PDFs for all seven projects."""
from pathlib import Path
import subprocess,sys
root=Path(__file__).resolve().parents[1];cli=r'C:\Program Files\KiCad\10.0\bin\kicad-cli.exe'
for name in sys.argv[1:] or ['BasicRX','BasicTX','LFRX','LFTX','TVRX','TVRX2','WBX']:
 d=root/'projects'/name;o=d/'preview';o.mkdir(exist_ok=True);board=str(d/(name+'.kicad_pcb'))
 jobs=[['sch','export','pdf','--output',str(o/(name+'-schematic.pdf')),str(d/(name+'.kicad_sch'))]]
 for layer,label in [('F.Fab','assembly-front'),('B.Fab','assembly-back')]:
  jobs.append(['pcb','export','pdf','--layers',layer+',Edge.Cuts','--sketch-pads-on-fab-layers','--exclude-value','--mode-single','--scale','0','--black-and-white',*(['--mirror'] if layer=='B.Fab' else []),'--output',str(o/(name+'-'+label+'.pdf')),board])
 layers='F.Cu,In1.Cu,In2.Cu,In3.Cu,In4.Cu,B.Cu' if name=='WBX' else 'F.Cu,In1.Cu,In2.Cu,B.Cu'
 jobs.append(['pcb','export','pdf','--layers',layers,'--common-layers','Edge.Cuts','--mode-multipage','--scale','0','--output',str(o/(name+'-copper-layers.pdf')),board])
 for args in jobs:
  r=subprocess.run([cli,*args],capture_output=True);assert r.returncode==0,(args,r.stderr)
 print(name,'PDF previews exported',flush=True)
