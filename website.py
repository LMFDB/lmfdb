"""
start this via $ sage -python website.py --port <portnumber>
add --debug if you are debugging
"""
from base import *

import hilbert_modular_form
import siegel_modular_form
import classical_modular_forms
import elliptic_curve
import Lfunction
import maass_form
import plot_example
import number_field
import lfunction_db
import maass_form_picard

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
    return redirect(url_for("render_classical_modular_forms"))
    #return render_template("modular_form_space.html", info = { })
    
@app.route("/calc")
def calc():
    return request.args['ep']

@app.route("/form")
def form_example():
    sidebar = [ ('topic1' , [ ("abc", "#"), ("def", "#")]), ("topic2" , [ ("ghi", "#"), ("jkl", "#") ] ) ]
    info = {'sidebar' : sidebar}
    return render_template("form.html", info=info)

@app.route("/Lfunction/")
@app.route("/Lfunction/<arg1>")
@app.route("/Lfunction/<arg1>/<arg2>")
@app.route("/Lfunction/<arg1>/<arg2>/<arg3>")
@app.route("/Lfunction/<arg1>/<arg2>/<arg3>/<arg4>")
@app.route("/Lfunction/<arg1>/<arg2>/<arg3>/<arg4>/<arg5>")
@app.route("/L/")
@app.route("/L/<arg1>") # arg1 is EllipticCurve, ModularForm, Character, etc
@app.route("/L/<arg1>/<arg2>") # arg2 is field
@app.route("/L/<arg1>/<arg2>/<arg3>") #arg3 is label
@app.route("/L/<arg1>/<arg2>/<arg3>/<arg4>")
@app.route("/L/<arg1>/<arg2>/<arg3>/<arg4>/<arg5>")
@app.route("/L-function/")
@app.route("/L-function/<arg1>")
@app.route("/L-function/<arg1>/<arg2>")
@app.route("/L-function/<arg1>/<arg2>/<arg3>")
@app.route("/L-function/<arg1>/<arg2>/<arg3>/<arg4>")
@app.route("/L-function/<arg1>/<arg2>/<arg3>/<arg4>/<arg5>")
def render_Lfunction(arg1 = None, arg2 = None, arg3 = None, arg4 = None, arg5 = None):
    return Lfunction.render_webpage(request, arg1, arg2, arg3, arg4, arg5)

@app.route("/plotLfunction")
def plotLfunction():
    return Lfunction.render_plotLfunction(request.args)

@app.route("/browseGraph")
def browseGraph():
    return Lfunction.render_browseGraph(request.args)

@app.route("/zeroesLfunction")
def zeroesLfunction():
    return Lfunction.render_zeroesLfunction(request.args)

@app.route('/ModularForm/GSp4/Q')
def ModularForm_GSp4_Q_top_level():
    return siegel_modular_form.render_webpage(request.args)

#@app.route('/ModularForm/GL2/Q/holomorphic/')
#def render_classical_modular_form():
#    return classical_modular_form.render_webpage(request.args)

@app.route('/ModularForm/GL2/Q/Maass/')
def render_maass_form():
    return maass_form.render_webpage(request.args)

@app.route('/example_plot')
def render_example_plot():
    return plot_example.render_plot(request.args)

@app.route("/not_yet_implemented")
def not_yet_implemented():
    return render_template("not_yet_implemented.html")


def usage():
    print """
Usage: %s [OPTION]...

  -p, --port=NUM    bind to port NUM (default 37777)
  -h, --host=HOST   bind to host HOST (default "127.0.0.1")
  -l, --log=FILE    log to FILE (default "flasklog")
      --dbport=NUM  bind the MongoDB to the given port (default 37010)
      --debug       enable debug mode
      --help        show this help
""" % sys.argv[0]

def main():

    import getopt
    try:
        opts, args = getopt.getopt(sys.argv[1:],
                "p:h:l:",
                [ "port=", "host=", "dbport=", "log=", "debug", "help",
                # undocumented, see below
                "enable-reloader", "disable-reloader",
                "enable-debugger", "disable-debugger",
                ])
    except getopt.GetoptError, err:
        sys.stderr.write("%s: %s\n" % (sys.argv[0], err))
        sys.stderr.write("Try '%s --help' for usage\n" % sys.argv[0])
        sys.exit(2)

    # default options to pass to the app.run()
    options = { "port": 37777, "host": "127.0.0.1" }
    logfile = "flasklog"
    dbport = 37010

    for opt, arg in opts:
        if opt == "--help":
            usage()
            sys.exit()
        elif opt in ("-p", "--port"):
            options["port"] = int(arg)
        elif opt in ("-h", "--host"):
            options["host"] = arg
        elif opt in ("-l", "--log"):
            logfile = arg
        elif opt in ("--dbport"):
            dbport = int(arg)
        elif opt == "--debug":
            options["debug"] = True
        # undocumented: the following allow changing the defaults for
        # these options to werkzeug (they both default to False unless
        # --debug is set, in which case they default to True but can
        # be turned off)
        elif opt == "--enable-reloader":
            options["use_reloader"] = True
        elif opt == "--disable-reloader":
            options["use_reloader"] = False
        elif opt == "--enable-debugger":
            options["use_debugger"] = True
        elif opt == "--disable-debugger":
            options["use_debugger"] = False

    import logging
    file_handler = logging.FileHandler(logfile)
    file_handler.setLevel(logging.WARNING)
    
    import base
    base._init(dbport)
   
    app.logger.addHandler(file_handler)
    app.run(**options)


if __name__ == '__main__':

    main()

