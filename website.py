"""
start this via $ sage -python website.py --port <portnumber>
add --debug if you are debugging
"""
from base import *

import hilbert_modular_form
import siegel_modular_form
import modular_forms
import elliptic_curve
import quadratic_twists
import renderLfunction
#import maass_form
import plot_example
import number_field
import lfunction_db
#import maass_form_picard
#import maass_waveforms
import users 
import knowledge
import upload
import DirichletCharacter
import raw

import sys

@app.errorhandler(404)
def not_found(error):
    return "404", 404

@app.route("/")
def index():
    return render_template('index.html', title ="Homepage", bread=None)

@app.route("/about")
def about():
    return render_template("about.html", title="About")

@app.route("/acknowledgment")
def acknowledgment():
  return render_template("acknowledgment.html", title="Acknowledgment")

def root_static_file(name):
    def static_fn():
       import os
       fn = os.path.join('.', "static", name)
       if os.path.exists(fn):
         return open(fn).read()
       import logging
       logging.critical("root_static_file: file %s not found!" % fn)
       return ''
    app.add_url_rule('/%s'%name, 'static_%s'%name, static_fn)
map(root_static_file, [ 'robots.txt', 'favicon.ico' ])

@app.route("/style.css")
def css():
  from flask import make_response
  response = make_response(render_template("style.css"))
  response.headers['Content-type'] = 'text/css'
  response.headers['Cache-Control'] = 'public, max-age=600'
  return response

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
    return redirect(url_for("mf.render_modular_form_main_page"))
    #return render_template("modular_form_space.html", info = { })
    
@app.route("/calc")
def calc():
    return request.args['ep']

@app.route("/form")
def form_example():
    sidebar = [ ('topic1' , [ ("abc", "#"), ("def", "#")]), ("topic2" , [ ("ghi", "#"), ("jkl", "#") ] ) ]
    info = {'sidebar' : sidebar}
    return render_template("form.html", info=info)

@app.route("/Character/Dirichlet/")
@app.route("/Character/Dirichlet/<arg1>")
@app.route("/Character/Dirichlet/<arg1>/<arg2>")
def render_Character(arg1 = None, arg2 = None):
    return DirichletCharacter.render_webpage(request,arg1,arg2)

@app.route("/Lfunction/")
@app.route("/Lfunction/<arg1>")
@app.route("/Lfunction/<arg1>/<arg2>")
@app.route("/Lfunction/<arg1>/<arg2>/<arg3>")
@app.route("/Lfunction/<arg1>/<arg2>/<arg3>/<arg4>")
@app.route("/Lfunction/<arg1>/<arg2>/<arg3>/<arg4>/<arg5>")
@app.route("/L/")
@app.route("/L/<arg1>") # arg1 is EllipticCurve, ModularForm, Character, etc
@app.route("/L/<arg1>/<arg2>") # arg2 is field
#@app.route("/L/<arg1>/<arg2>/") # arg2 is field
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
    return renderLfunction.render_webpage(request, arg1, arg2, arg3, arg4, arg5)

@app.route("/plotLfunction")
@app.route("/plotLfunction/<arg1>")
@app.route("/plotLfunction/<arg1>/<arg2>")
@app.route("/plotLfunction/<arg1>/<arg2>/<arg3>")
@app.route("/plotLfunction/<arg1>/<arg2>/<arg3>/<arg4>")
@app.route("/plotLfunction/<arg1>/<arg2>/<arg3>/<arg4>/<arg5>")
def plotLfunction(arg1 = None, arg2 = None, arg3 = None, arg4 = None, arg5 = None):
    return renderLfunction.render_plotLfunction(request, arg1, arg2, arg3, arg4, arg5)

@app.route("/browseGraph")
def browseGraph():
    return renderLfunction.render_browseGraph(request.args)

@app.route("/browseGraphHolo")
def browseGraphHolo():
    return renderLfunction.render_browseGraphHolo(request.args)

@app.route("/browseGraphChar")
def browseGraphChar():
    return renderLfunction.render_browseGraphHolo(request.args)

@app.route("/zeroesLfunction")
@app.route("/zeroesLfunction/<arg1>")
@app.route("/zeroesLfunction/<arg1>/<arg2>")
@app.route("/zeroesLfunction/<arg1>/<arg2>/<arg3>")
@app.route("/zeroesLfunction/<arg1>/<arg2>/<arg3>/<arg4>")
@app.route("/zeroesLfunction/<arg1>/<arg2>/<arg3>/<arg4>/<arg5>")
def zeroesLfunction(arg1 = None, arg2 = None, arg3 = None, arg4 = None, arg5 = None):
    return renderLfunction.render_zeroesLfunction(request, arg1, arg2, arg3, arg4, arg5)

@app.route('/ModularForm/GSp4/Q')
def ModularForm_GSp4_Q_top_level():
    return siegel_modular_form.render_webpage(request.args)

#@app.route('/ModularForm/GL2/Q/holomorphic/')
#def render_classical_modular_form():
#    return classical_modular_form.render_webpage(request.args)

#@app.route('/ModularForm/GL2/Q/Maass/')
#def render_maass_form():
#    return maass_form.render_webpage(request.args)

@app.route('/example_plot')
def render_example_plot():
    return plot_example.render_plot(request.args)

@app.route("/not_yet_implemented")
def not_yet_implemented():
    return render_template("not_yet_implemented.html", title = "Not Yet Implemented")


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
    options = { "port": 37777, "host": "127.0.0.1" , "debug" : False}
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
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.name = "LMFDB"
    import utils
    formatter = logging.Formatter(utils.LmfdbFormatter.fmtString.split(r'[')[0])
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    root_logger.addHandler(ch)
    
    file_handler = logging.FileHandler(logfile)
    file_handler.setLevel(logging.WARNING)
    app.logger.addHandler(file_handler)
    
    import base
    base._init(dbport)
    logging.info("... done.")

    # just for debugging
    #if options["debug"]:
    #  logging.info(str(app.url_map))

    app.run(**options)


if __name__ == '__main__':
    main()
else:
    # HSY: what's this else part about? 
    import logging
    logfile = "flasklog"
    file_handler = logging.FileHandler(logfile)
    file_handler.setLevel(logging.WARNING)
    import base
    base._init(37010)
    app.logger.addHandler(file_handler)

def getDownloadsFor(path):
  return "bar"
