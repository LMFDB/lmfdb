from flask import render_template,url_for
import bson
import base

@base.app.route("/ModularForm/GL2/C/Maass/")
def maass_form_picard():
   info = {}
   data = range(100)
   return render_template("maass_form_picard.html", title = "maass form complex", data = data, info=info)
