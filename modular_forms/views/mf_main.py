from base import app
from flask import render_template,url_for
from modular_forms import mf,MF,mf_logger

@mf.context_processor
def body_class():
  return { 'body_class' : MF }


#@mf.route("/ModularForm/")
#@mf.route("/AutomorphicForm/")

mf_logger.debug("EN_V path: {0}".format(app.jinja_loader.searchpath ))
@mf.route("/")
def modular_form_main_page():
    info=dict()
    title = "Modular Forms"
    bread =[('Modular Forms',url_for('modular_form_toplevel'))]
    return render_template("mf_navigation.html",info=info,title=title)
