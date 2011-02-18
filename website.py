from base import *

import hilbert_modular_form
import siegel_modular_form
import classical_modular_form
import elliptic_curve
import Lfunction
import maass_form
import plot_example
import number_field
import zero_search

import raw

import sys

@app.errorhandler(404)
def not_found(error):
    return "404", 404

@app.route("/")
def index():
    return render_template('index.html', title ="Template Title")

@app.route("/robots.txt")
def robots():
   import os
   return open(os.path.join('.', "static","robots.txt")).read()

@app.route('/a/<int:a>')
def a(a):
    a = Integer(a)
    return r'\(' + str(a / (1+a)) + r'\)'

@app.route("/example/")
@app.route("/example/<blah>")
def example(blah = None):
    return render_template("example.html", blah=blah)

@app.route("/modular/")
@app.route("/ModularForm/")
@app.route("/AutomorphicForm/")
def modular_form_toplevel():
    return render_template("modular_form_space.html", info = { })
    
@app.route("/calc")
def calc():
    return request.args['ep']

@app.route("/form")
def form_example():
    sidebar = [ ('topic1' , [ ("abc", "#"), ("def", "#")]), ("topic2" , [ ("ghi", "#"), ("jkl", "#") ] ) ]
    info = {'sidebar' : sidebar}
    return render_template("form.html", info=info)

@app.route("/Lfunction/")
@app.route("/Lfunction/<family>")
@app.route("/Lfunction/<family>/<group>")
@app.route("/Lfunction/<family>/<group>/<field>")
@app.route("/Lfunction/<family>/<group>/<field>/<objectName>")
@app.route("/Lfunction/<family>/<group>/<field>/<objectName>/<level>")
@app.route("/L/")
@app.route("/L/<family>")
@app.route("/L/<family>/<group>")
@app.route("/L/<family>/<group>/<field>")
@app.route("/L/<family>/<group>/<field>/<objectName>")
@app.route("/L/<family>/<group>/<field>/<objectName>/<level>")
@app.route("/L-function/")
@app.route("/L-function/<family>")
@app.route("/L-function/<family>/<group>")
@app.route("/L-function/<family>/<group>/<field>")
@app.route("/L-function/<family>/<group>/<field>/<objectName>")
@app.route("/L-function/<family>/<group>/<field>/<objectName>/<level>")
def render_Lfunction(family = None, group = None, field = None, objectName = None, level = None):
    return Lfunction.render_webpage(request.args, family, group, field, objectName, level)

@app.route("/plotLfunction")
def plotLfunction():
    return Lfunction.render_plotLfunction(request.args)

@app.route("/zeroesLfunction")
def zeroesLfunction():
    return Lfunction.render_zeroesLfunction(request.args)

@app.route('/ModularForm/GSp4/Q')
def ModularForm_GSp4_Q_top_level():
    return siegel_modular_form.render_webpage(request.args)

@app.route('/ModularForm/GL2/Q/holomorphic/')
def render_classical_modular_form():
    return classical_modular_form.render_webpage(request.args)

@app.route('/ModularForm/GL2/Q/Maass/')
def render_maass_form():
    return maass_form.render_webpage(request.args)

@app.route('/example_plot')
def render_example_plot():
    return plot_example.render_plot(request.args)

@app.route("/not_yet_implemented")
def not_yet_implemented():
    return render_template("not_yet_implemented.html")

if __name__ == '__main__':

    if '--debug' in sys.argv:
        debug = True
        sys.argv.remove('--debug')
    else:
        debug = False

    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    else:
        port = 37777

    import logging
    file_handler = logging.FileHandler("flasklog")
    file_handler.setLevel(logging.WARNING)
   
    app.logger.addHandler(file_handler)
    app.run(debug= debug, host="0.0.0.0", port=port)

