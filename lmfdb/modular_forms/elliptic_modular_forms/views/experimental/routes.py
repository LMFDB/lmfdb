r"""

Include all experimental routes here for clarity so that we see all routes which are defined.

"""
from lmfdb.modular_forms.elliptic_modular_forms import  emf_logger, emf
from flask import request,render_template
import json
from lmfdb.modular_forms.elliptic_modular_forms.backend.emf_draw_dots import paintSvgHolomorphic

met = ["GET","POST"]
@emf.route("/DataTables/",methods=met)
def test(**kwds):
    return render_template("data_table.html")


@emf.route("/Dots/<min_level>/<max_level>/<min_weight>/<max_weight>/",methods=met)
def show_dots(min_level, max_level, min_weight, max_weight):
    info = {}
    info['contents'] = [paintSvgHolomorphic(min_level, max_level, min_weight, max_weight)]
    info['min_level'] = min_level
    info['max_level'] = max_level
    info['min_weight'] = min_weight
    info['max_weight'] = max_weight
    return render_template("emf_browse_graph.html", title='Browsing dimensions of modular forms in the database', **info)

      


      
