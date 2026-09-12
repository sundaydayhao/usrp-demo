"""Make explicitly approximate display envelopes for two obsolete/mezzanine parts.

These are NOT vendor CAD and are NOT mechanical clearance certification.
XY and terminal locations follow the existing project footprint. Tuner height
is a 15 mm illustration assumption; its external F connector is not modelled.
PMC socket uses a representative 5.3 mm housing height (71439-0 family).
Run with Python + cadquery-ocp (installed in tmp/tools/occ for this migration).
"""
from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tmp/tools/occ'))
sys.path.insert(0,str(ROOT/'scripts'))
from add_project_3d_models import sexp,children,one,pads,Q
from OCP.gp import gp_Pnt,gp_Ax2,gp_Dir
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox,BRepPrimAPI_MakeCylinder
from OCP.TDocStd import TDocStd_Document
from OCP.TCollection import TCollection_ExtendedString,TCollection_HAsciiString
from OCP.TDataStd import TDataStd_Name
from OCP.XCAFDoc import XCAFDoc_DocumentTool,XCAFDoc_ColorType
from OCP.Quantity import Quantity_Color,Quantity_TypeOfColor
from OCP.STEPCAFControl import STEPCAFControl_Writer
from OCP.STEPControl import STEPControl_AsIs
OUT=ROOT/'tmp/3d-source/envelopes';OUT.mkdir(exist_ok=True)
class Model:
 def __init__(self,name):
  self.name=name;self.doc=TDocStd_Document(TCollection_ExtendedString(name));self.st=XCAFDoc_DocumentTool.ShapeTool_s(self.doc.Main());self.ct=XCAFDoc_DocumentTool.ColorTool_s(self.doc.Main());self.w=['#VRML V2.0 utf8','# Approximate display envelope; see 3D_MODELS.md. Units: 1 = 2.54 mm.'];self.parts=0
 def add(self,shape,color,label,vrml):
  l=self.st.AddShape(shape,False);TDataStd_Name.Set_s(l,TCollection_ExtendedString(label));self.ct.SetColor(l,Quantity_Color(*color,Quantity_TypeOfColor.Quantity_TOC_RGB),XCAFDoc_ColorType.XCAFDoc_ColorGen);self.parts+=1;self.w.append(vrml)
 def box(self,x,y,z,w,d,h,color,label):
  mat=' '.join(map(str,color));xyz=' '.join(f'{t/2.54:.8f}' for t in (x+w/2,y+d/2,z+h/2));size=' '.join(f'{t/2.54:.8f}' for t in (w,d,h))
  vr=f'Transform {{ translation {xyz} children [ Shape {{ appearance Appearance {{ material Material {{ diffuseColor {mat} }} }} geometry Box {{ size {size} }} }} ] }}'
  self.add(BRepPrimAPI_MakeBox(gp_Pnt(x,y,z),w,d,h).Shape(),color,label,vr)
 def cylinder(self,x,y,z,r,h,color,label):
  mat=' '.join(map(str,color));xyz=' '.join(f'{t/2.54:.8f}' for t in (x,y,z+h/2));vr=f'Transform {{ translation {xyz} rotation 1 0 0 1.570796327 children [ Shape {{ appearance Appearance {{ material Material {{ diffuseColor {mat} }} }} geometry Cylinder {{ radius {r/2.54:.8f} height {h/2.54:.8f} }} }} ] }}'
  self.add(BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(x,y,z),gp_Dir(0,0,1)),r,h).Shape(),color,label,vr)
 def save(self,fp,description):
  writer=STEPCAFControl_Writer();writer.SetColorMode(True);writer.SetNameMode(True);assert writer.Transfer(self.doc,STEPControl_AsIs);writer.Write(str(OUT/(self.name+'.step')))
  (OUT/(self.name+'.wrl')).write_text('\n'.join(self.w)+'\n')
  f=sexp.load_file(fp);f[:]=[n for n in f if not(isinstance(n,list) and str(n[0])=='model')];f.append(sexp.parse('(model "" (offset (xyz 0 0 0)) (scale (xyz 1 1 1)) (rotate (xyz 0 0 0)))'));children(f,'model')[-1][1]=Q((OUT/(self.name+'.wrl')).relative_to(ROOT).as_posix());sexp.save_file(OUT/(self.name+'.kicad_mod'),f)
  (OUT/(self.name+'.json')).write_text(json.dumps(description,indent=2));print(self.name,self.parts,flush=True)

ivory=(.86,.84,.71);gold=(.80,.63,.25);metal=(.62,.64,.67);dark=(.24,.25,.27)
fp=ROOT/'projects/BasicRX/USRP.pretty/J2.kicad_mod';f=sexp.load_file(fp);p=pads(f)
m=Model('PMC64_APPROX_DISPLAY');xmin,xmax=-2.794,34.036;ymin,ymax=-2.286,6.096
# Hollow socket envelope with 64 internal contact strips and two locating pegs.
m.box(xmin,ymin,.15,xmax-xmin,ymax-ymin,.7,ivory,'approx socket base')
for yy in (ymin,ymax-.7):m.box(xmin,yy,.85,xmax-xmin,.7,4.45,ivory,'approx housing side')
for xx in (xmin,xmax-.8):m.box(xx,ymin,.85,.8,ymax-ymin,4.45,ivory,'approx housing end')
for num,(x,y) in p.items():
 m.box(x-.18,-y-.55,0,.36,1.1,.18,gold,'contact '+num)
 m.box(x-.18,-y-.15,.18,.36,.3,4.5,gold,'socket contact '+num)
for q in children(f,'pad'):
 if not str(q[1]):
  x,y=map(float,one(q,'at')[1:3]);m.cylinder(x,-y,-1.0,.5,1.2,ivory,'approx locating peg')
m.save(fp,{'kind':'APPROXIMATE display envelope, NOT vendor CAD','xy_source':'existing PMC-REVERSE F.Fab outline; pin and peg centers from project','housing_height_mm':5.3,'height_basis':'representative Molex 71439-0 family; actual daughterboard socket suffix not confirmed','body_width_mm':xmax-xmin,'body_depth_mm':ymax-ymin,'not_verified':['housing wall profile','contact spring geometry','mating interference','chosen suffix/stack height'],'official_family_url':'https://www.molex.com/en-us/products/part-detail/714390164'})

fp=ROOT/'projects/TVRX/USRP.pretty/U2.kicad_mod';f=sexp.load_file(fp);p=pads(f);m=Model('MT4937DI5_APPROX_DISPLAY')
xmin,xmax=-79.2988,3.6576;ymin,ymax=-2.8702,39.9288;h=15.0
m.box(xmin,ymin,.6,xmax-xmin,ymax-ymin,.4,metal,'approx shield bottom')
m.box(xmin,ymin,h-.4,xmax-xmin,ymax-ymin,.4,metal,'approx shield lid')
for yy in (ymin,ymax-.4):m.box(xmin,yy,1,xmax-xmin,.4,h-1.4,metal,'approx shield wall')
for xx in (xmin,xmax-.4):m.box(xx,ymin,1,.4,ymax-ymin,h-1.4,metal,'approx shield wall')
for num,(x,y) in p.items():
 if int(num)<20:m.cylinder(x,-y,-3.0,.24,4.0,metal,'signal pin '+num)
 else:m.box(x-.5,-y-.3,-3.0,1,.6,4.0,metal,'ground tab '+num)
# A dark label patch distinguishes this envelope from a detailed vendor model.
m.box(xmin+20,ymin+12,h,42,14,.015,dark,'display envelope label patch')
m.save(fp,{'kind':'APPROXIMATE display envelope, NOT vendor CAD','xy_source':'existing MT4937DI5 F.Fab outline; pin and ground-tab centers from project','assumed_height_mm':h,'height_basis':'illustration assumption; no verified mechanical drawing available','body_width_mm':xmax-xmin,'body_depth_mm':ymax-ymin,'not_modelled':['external F connector and its mounting/cable clearance','internal circuit','exact shield profile'],'not_verified':['module height','signal pin length','ground tab dimensions'],'historical_datasheet_reference':'4937-DI5-3x8899-2.pdf, Microtune rev 02 (Sep 2001)'})
