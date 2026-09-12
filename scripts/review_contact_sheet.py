from pathlib import Path
from PIL import Image,ImageDraw
import pymupdf as fitz
ROOT=Path(__file__).resolve().parents[1]
names=['BasicRX','BasicTX','LFRX','LFTX','TVRX','TVRX2','WBX']
out=Image.new('RGB',(2100,1800),'white');draw=ImageDraw.Draw(out)
for i,name in enumerate(names):
 doc=fitz.open(ROOT/'projects'/name/'preview'/(name+'-schematic.pdf'));pg=doc[0];scale=650/max(pg.rect.width,pg.rect.height);pix=pg.get_pixmap(matrix=fitz.Matrix(scale,scale));im=Image.frombytes('RGB',(pix.width,pix.height),pix.samples)
 x=700*(i%3);y=600*(i//3);out.paste(im,(x,y+30));draw.text((x+10,y+10),name,fill='black')
out.save(ROOT/'tmp/schematic-overview.png')
