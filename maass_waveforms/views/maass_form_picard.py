from flask import render_template,url_for,request
import bson
import base

@base.app.route("/ModularForm/GL2/C/Maass/")
def maass_form_picard():
   htp = base.getDBConnection().HTPicard.picard
   docid = request.args.get('id', None)   
   info = {}
   ds = [ (_['_id'], _['ev']) for _ in htp.find(fields=['ev'], sort=[('ev', 1)]) ]
   data = None
   if docid:
     data = htp.find_one({'_id' : docid })
   return render_template("maass_form_picard.html", title = "Maass cusp forms on PSL(2,Z[i])", data = data, id=docid, info=info, ds=ds)
