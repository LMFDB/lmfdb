import flask
from flask import render_template,url_for,request
import bson
import base
from  modular_forms.maass_forms.picard import MWFP,mwfp,mwfp_logger
logger = mwfp_logger

import modular_forms.maass_forms
#mwfp = flask.Blueprint('mwfp', __name__, template_folder="templates")

# see main mwf blueprint for details
@mwfp.context_processor
def body_class():
  return { 'body_class' : 'mwfp' }


#@base.app.route("/ModularForm/GL2/C/Maass/")
@mwfp.route("/",methods=['GET','POST'])
def render_picard_maass_forms():
   htp = base.getDBConnection().HTPicard.picard
   docid = request.args.get('id', None)   
   ds = [ (_['_id'], _['ev']) for _ in htp.find(fields=['ev'], sort=[('ev', 1)]) ]
   data = None
   if docid:
     data = htp.find_one({'_id' : docid })
   return render_template("mwfp.maass_form_picard.html", title = "Maass cusp forms on PSL(2,Z[i])", data = data, id=docid, ds=ds)
