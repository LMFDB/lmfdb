import flask
from flask import render_template,url_for,request
import bson
import base
from  modular_forms.maass_forms.picard import MWFP,mwfp,mwfp_logger
logger = mwfp_logger
#from  modular_forms.maass_forms.maass_waveform import MWFTable
import modular_forms.maass_forms
from modular_forms.maass_forms.picard.backend.mwf_picard_utils import *


#mwfp = flask.Blueprint('mwfp', __name__, template_folder="templates")
mwfp_dbname = 'HTPicard'
# see main mwf blueprint for details
@mwfp.context_processor
def body_class():
    return { 'body_class' : 'mwfp' }

#@base.app.route("/ModularForm/GL2/C/Maass/")
@mwfp.route("/",methods=['GET','POST'])
def render_picard_maass_forms():
    htp = base.getDBConnection().HTPicard.picard
    docid = request.args.get('id', None)   
    test =  request.args.get('test', None)   
    if test:
        return render_picard_test()
    if docid<>None:
        return render_picard_maass_forms_get_one(docid)
    ds = [ (_['_id'], _['ev']) for _ in htp.find(fields=['ev'], sort=[('ev', 1)]) ]
    data = None
    TT= MaassformsPicardDisplay(mwfp_dbname,collection='all',skip=[0],limit=[10],keys=['Eigenvalue'])
    TT.set_table_browsing()
    #TT.get_metadata()
    if docid:
        data = htp.find_one({'_id' : docid })
    return render_template("maass_form_picard.html", title = "Maass cusp forms on \(\mathrm{PSL}(2,\mathbb{Z}[i])\)", data = data, id=docid, ds=ds)

@mwfp.route("/<id>",methods=['GET','POST'])
def render_picard_maass_forms_get_one(id):
    htp = base.getDBConnection().HTPicard.picard
    docid = request.args.get('id', None)   
    ds = [ (_['_id'], _['ev']) for _ in htp.find(fields=['ev'], sort=[('ev', 1)]) ]
    data = None
    if docid:
        data = htp.find_one({'_id' : docid })
    return render_template("/maass_form_picard.html", title = "Maass cusp forms on \(\mathrm{PSL}(2,\mathbb{Z}[i])\)", data = data, id=docid, ds=ds)


def render_picard_test():
    htp = base.getDBConnection().HTPicard.picard
    docid = request.args.get('id', None)   
    test =  request.args.get('test', None)   
    if test:
        return render_picard_test()
    if docid<>None:
        return render_picard_maass_forms_get_one(docid)
    ds = [ (_['_id'], _['ev']) for _ in htp.find(fields=['ev'], sort=[('ev', 1)]) ]
    data = None
    TT= MaassformsPicardDisplay(mwfp_dbname,collection='all',skip=[0],limit=[10],keys=['Eigenvalue'])
    TT.set_table()
    TT.get_metadata()
    if docid:
        data = htp.find_one({'_id' : docid })
    return render_template("maass_form_picard_test.html", title = "Maass cusp forms on \(\mathrm{PSL}(2,\mathbb{Z}[i])\)", data = data, id=docid, ds=ds)
