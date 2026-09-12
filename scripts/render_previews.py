from pathlib import Path
import subprocess,concurrent.futures
import pymupdf as fitz
ROOT=Path(__file__).resolve().parents[1]
CLI='C:/Program Files/KiCad/10.0/bin/kicad-cli.exe'
def render(name):
    d=ROOT/'projects'/name;out=d/'preview';out.mkdir(exist_ok=True)
    subprocess.run([CLI,'sch','export','svg','--output',str(out),str(d/(name+'.kicad_sch'))],check=True,capture_output=True)
    layer_views=[('F.Cu,F.Silkscreen,Edge.Cuts','front'),('B.Cu,B.Silkscreen,Edge.Cuts','back'),('In1.Cu,Edge.Cuts','inner1'),('In2.Cu,Edge.Cuts','inner2')]
    if name=='WBX':layer_views += [('In3.Cu,Edge.Cuts','inner3'),('In4.Cu,Edge.Cuts','inner4')]
    for layers,label in layer_views:
        subprocess.run([CLI,'pcb','export','svg','--layers',layers,'--mode-single','--fit-page-to-board','--exclude-drawing-sheet','--output',str(out/(label+'.svg')),str(d/(name+'.kicad_pcb'))],check=True,capture_output=True)
    for svg in out.glob('*.svg'):
        s=fitz.open(svg);pdf=fitz.open('pdf',s.convert_to_pdf());pg=pdf[0];scale=1800/max(pg.rect.width,pg.rect.height);pg.get_pixmap(matrix=fitz.Matrix(scale,scale)).save(svg.with_suffix('.png'))
    print(name,'previews rendered')
if __name__=='__main__':
    import sys
    with concurrent.futures.ThreadPoolExecutor(5) as pool:list(pool.map(render,sys.argv[1:] or ['BasicRX','BasicTX','LFRX','LFTX','TVRX','TVRX2','WBX']))
