"""Bake exactly the easyeda2kicad WRL translation into companion STEP files.

easyeda2kicad 1.0.1 copies raw STEP but translates WRL. Use the cached original
models to avoid accumulating transforms. XCAF retains assembly colours/names.
"""
from pathlib import Path
import sys,json,hashlib
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tmp/tools/occ'),str(ROOT/'tmp/tools/eda3d')]
from easyeda2kicad.easyeda.easyeda_importer import Easyeda3dModelImporter
from easyeda2kicad.kicad.export_kicad_3d_model import _get_obj_bbox
from OCP.STEPCAFControl import STEPCAFControl_Reader,STEPCAFControl_Writer
from OCP.STEPControl import STEPControl_AsIs
from OCP.TDocStd import TDocStd_Document
from OCP.TCollection import TCollection_ExtendedString
from OCP.TDF import TDF_Label
from OCP.collections import Sequence_TDF_Label as TDF_LabelSequence
from OCP.XCAFDoc import XCAFDoc_DocumentTool
from OCP.TopLoc import TopLoc_Location
from OCP.gp import gp_Trsf,gp_Vec
from OCP.IFSelect import IFSelect_RetDone
cache=ROOT/'.easyeda_cache';out=ROOT/'tmp/3d-source/easyeda.3dshapes'
for lcsc in ['C879854','C6835853','C3640849']:
 m=Easyeda3dModelImporter(json.loads((cache/(lcsc+'.json')).read_text())['result'],False).output
 b=_get_obj_bbox((cache/(m.uuid+'.obj')).read_text());delta=[-(b[0][0]+b[0][1])/2+m.translation.x,-(b[1][0]+b[1][1])/2+m.translation.y,-b[2][0]+m.translation.z]
 original=cache/(m.uuid+'.step');target=out/(m.name+'.step')
 doc=TDocStd_Document(TCollection_ExtendedString(m.name));r=STEPCAFControl_Reader();assert r.ReadFile(str(original))==IFSelect_RetDone;assert r.Transfer(doc)
 st=XCAFDoc_DocumentTool.ShapeTool_s(doc.Main());labels=TDF_LabelSequence();st.GetFreeShapes(labels);tr=gp_Trsf();tr.SetTranslation(gp_Vec(*delta))
 for i in range(1,labels.Length()+1):assert st.SetLocation(labels.Value(i),TopLoc_Location(tr),TDF_Label())
 st.UpdateAssemblies();w=STEPCAFControl_Writer();w.SetColorMode(True);w.SetNameMode(True);assert w.Transfer(doc,STEPControl_AsIs);assert w.Write(str(target))==IFSelect_RetDone
 info={'source':'EasyEDA/LCSC community/manufacturer package model','lcsc':lcsc,'easyeda_uuid':m.uuid,'api_url':'https://easyeda.com/api/products/'+lcsc+'/components','original_step_sha256':hashlib.sha256(original.read_bytes()).hexdigest(),'normalized_step_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'STEP_translation_mm':delta,'reason':'Match translation baked into WRL by easyeda2kicad 1.0.1; rotation remains in footprint model transform','rights':'Original model rights retained by its author/provider; no new license asserted.'}
 (out/(m.name+'.json')).write_text(json.dumps(info,indent=2));print(lcsc,delta,flush=True)
