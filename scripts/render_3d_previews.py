"""Render both sides with KiCad's actual 3D renderer; package a contact PDF."""
from pathlib import Path
import subprocess,concurrent.futures
from PIL import Image,ImageDraw,ImageFont
import pymupdf
ROOT=Path(__file__).resolve().parents[1];CLI=r'C:\Program Files\KiCad\10.0\bin\kicad-cli.exe'
NAMES=['BasicRX','BasicTX','LFRX','LFTX','TVRX','TVRX2','WBX']
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',26)
small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18)
def render(job):
 name,side=job;d=ROOT/'projects'/name;p=d/'preview';p.mkdir(exist_ok=True)
 r=subprocess.run([CLI,'pcb','render','--width','1600','--height','1200','--side',side,'--zoom','0.75','--rotate','25,0,20','--quality','high','--output',str(p/('3d-'+side+'.png')),str(d/(name+'.kicad_pcb'))],capture_output=True)
 (ROOT/'tmp'/('render-3d-'+name+'-'+side+'.log')).write_bytes(r.stdout+r.stderr);assert r.returncode==0,(name,side,r.stderr);print(name,side,flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(render,[(n,s) for n in NAMES for s in ['top','bottom']]))
montage=Image.new('RGB',(1600,7*560),'#eef1f4');dr=ImageDraw.Draw(montage)
for row,n in enumerate(NAMES):
 sheet=Image.new('RGB',(1600,650),'white');sd=ImageDraw.Draw(sheet);sd.text((30,14),n+' | KiCad 3D preview',font=font,fill='#172b3b')
 for i,s in enumerate(['top','bottom']):
  im=Image.open(ROOT/'projects'/n/'preview'/('3d-'+s+'.png')).convert('RGBA');bounds=im.getbbox();im=im.crop(bounds);im.thumbnail((740,540));sheet.paste(im,(i*800+(800-im.width)//2,56+(540-im.height)//2),im)
  sd.text((i*800+30,595),s.upper(),font=small,fill='#35495e')
 sd.text((30,625),'PMC socket: approximate envelope'+(' | TV tuner: approximate envelope, height 15 mm assumed, F connector omitted' if n=='TVRX' else ''),font=small,fill='#684b32')
 out=ROOT/'projects'/n/'preview';sheet.save(out/'3d-views.png');sheet.save(out/'3d-views.pdf',resolution=120)
 overview=sheet.copy();overview.thumbnail((1600,550));montage.paste(overview,(0,row*560))
montage.save(ROOT/'deliverables/3D-overview.png')
pdf=pymupdf.open()
for n in NAMES:
 with pymupdf.open(ROOT/'projects'/n/'preview/3d-views.pdf') as p:pdf.insert_pdf(p)
pdf.save(ROOT/'deliverables/3D-previews.pdf');print('Preview PDF written',flush=True)
