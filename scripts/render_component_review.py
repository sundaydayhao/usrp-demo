"""Create before/after EEPROM crops and page pixel diffs from KiCad PDFs."""
from pathlib import Path
import io, json, subprocess
import pymupdf as fitz
from PIL import Image, ImageChops
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

ROOT=Path(__file__).resolve().parents[1]
BASE='bf6d371'
TMP=ROOT/'tmp/pdfs/at24-review'; TMP.mkdir(parents=True,exist_ok=True)
targets={'BasicRX':[(0,'U1')],'BasicTX':[(0,'U52')],'LFRX':[(0,'U1')],'LFTX':[(0,'U52')],'TVRX':[(0,'U1')],'TVRX2':[(1,'U1')],'WBX':[(2,'U202'),(4,'U403')]}
out=ROOT/'deliverables/AT24C02-review.pdf'
c=canvas.Canvas(str(out),pagesize=(842,595))
c.setTitle('USRP1 AT24C02 replacement - schematic review')
reports=[]; page_number=0
for name,parts in targets.items():
    path=ROOT/'projects'/name/'preview'/(name+'-schematic.pdf')
    old=fitz.open(stream=subprocess.check_output(['git','show',BASE+':'+path.relative_to(ROOT).as_posix()],cwd=ROOT),filetype='pdf')
    new=fitz.open(path)
    assert len(old)==len(new)
    for page_index,(a,b) in enumerate(zip(old,new)):
        assert a.rect==b.rect
        pa=a.get_pixmap(matrix=fitz.Matrix(2,2),alpha=False);pb=b.get_pixmap(matrix=fitz.Matrix(2,2),alpha=False)
        ia=Image.frombytes('RGB',(pa.width,pa.height),pa.samples);ib=Image.frombytes('RGB',(pb.width,pb.height),pb.samples)
        diff=ImageChops.difference(ia,ib).convert('L');mask=diff.point(lambda x:255 if x>0 else 0)
        bbox=mask.getbbox(); changed=mask.histogram()[255]
        reports.append({'project':name,'sheet':page_index+1,'changed_pixels_at_144_dpi':changed,'difference_bbox_points':[v/2 for v in bbox] if bbox else None})
        if not any(page_index==i for i,_ in parts): assert changed==0,(name,page_index,'unexpected visible change')
    for page_index,ref in parts:
        a,b=old[page_index],new[page_index]
        hits=sorted(b.search_for('AT24C02'),key=lambda r:r.x0)
        assert len(hits)==2,(name,page_index,hits)
        signal,power=(hits[0],hits[1]) if name not in ('WBX','TVRX2') else (hits[1],hits[0])
        roi_signal=fitz.Rect(signal.x0-116,signal.y0-20,signal.x1+135,signal.y1+75) & b.rect
        roi_power=fitz.Rect(power.x0-112,power.y0-15,power.x1+60,power.y1+65) & b.rect
        page_number+=1
        c.setFillColorRGB(.08,.15,.23);c.setFont('Helvetica-Bold',18)
        c.drawString(28,562,f'{name} / {ref} - AT24C02')
        c.setFont('Helvetica',10);c.drawString(28,544,f'Schematic sheet {page_index+1} | Microchip AT24C02C-SSHM-T | LCSC C6203')
        for x,label,color in [(28,'BEFORE / '+BASE,(.55,.25,.2)),(435,'AFTER / AT24C02',(.07,.4,.33))]:
            c.setFillColorRGB(*color);c.setFont('Helvetica-Bold',11);c.drawString(x,517,label)
        for col,page in enumerate((a,b)):
            x=28+407*col
            for row,(label,roi,y,height) in enumerate([('Signal unit',roi_signal,250,252),('Power unit',roi_power,66,170)]):
                pix=page.get_pixmap(matrix=fitz.Matrix(4,4),clip=roi,alpha=False)
                img=Image.frombytes('RGB',(pix.width,pix.height),pix.samples)
                target=TMP/f'{name}-{ref}-{col}-{row}.png';img.save(target)
                c.setStrokeColorRGB(.80,.84,.87);c.rect(x,y,379,height)
                c.drawImage(ImageReader(img),x+4,y+4,371,height-21,preserveAspectRatio=True,anchor='c')
                c.setFont('Helvetica',9);c.setFillColorRGB(.25,.3,.35);c.drawString(x+8,y+height-12,label)
        c.setFillColorRGB(.12,.2,.28);c.setFont('Helvetica',9)
        c.drawString(28,45,'SOIC-8 pads and routing preserved. Pin 7 = WP (grounded). Page writes: 8 bytes, respect page boundaries.')
        c.drawString(28,30,'Full schematic and PCB remain editable in the individual KiCad projects. Hardware programming has not been tested.')
        c.drawRightString(814,16,f'{page_number} / 8')
        c.showPage()
c.save()
(ROOT/'verification/component-update-visual.json').write_text(json.dumps({'baseline_commit':BASE,'source':'KiCad schematic PDF raster comparison','render_DPI':144,'pages':reports,'EEPROM_review_pages':page_number,'review_pdf':out.relative_to(ROOT).as_posix()},indent=2),encoding='utf-8')
print(out,page_number,'pages')
