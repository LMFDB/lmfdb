#-*- coding: utf-8 -*-
# LMFDB - L-function and Modular Forms Database web-site - www.lmfdb.org
# Copyright (C) 2010-2012 by the LMFDB authors
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Library General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
"""
start this via $ sage -python website.py --port <portnumber>
add --debug if you are developing (full stacktrace in browser, ...)
"""

# Needs to be done first so that other modules and gunicorn can use logging
from .logger import info
from .app import app, set_running  # So that we can set it running below

# Importing the following top-level modules adds blueprints
# to the app and imports further modules to make them functional
# Note that this necessarily includes everything, even code in still in an alpha state
from . import api
assert api
#from . import api2
#assert api2
from . import belyi
assert belyi
from . import bianchi_modular_forms
assert bianchi_modular_forms
from . import hilbert_modular_forms
assert hilbert_modular_forms
from . import half_integral_weight_forms
assert half_integral_weight_forms
from . import siegel_modular_forms
assert siegel_modular_forms
# from . import modular_forms
# assert modular_forms
from . import elliptic_curves
assert elliptic_curves
from . import ecnf
assert ecnf
from . import number_fields
assert number_fields
from . import lfunctions
assert lfunctions
from . import genus2_curves
assert genus2_curves
from . import sato_tate_groups
assert sato_tate_groups
from . import users
assert users
from . import knowledge
assert knowledge
from . import characters
assert characters
from . import local_fields
assert local_fields
from . import galois_groups
assert galois_groups
from . import artin_representations
assert artin_representations
from . import tensor_products
assert tensor_products
from . import zeros
assert zeros
from . import crystals
assert crystals
from . import permutations
assert permutations
from . import hypergm
assert hypergm
from . import motives
assert motives
from . import riemann
assert riemann
from . import lattice
assert lattice
from . import higher_genus_w_automorphisms
assert higher_genus_w_automorphisms
from . import abvar
assert abvar
from .abvar import fq
assert fq
from . import modlmf
assert modlmf
from . import modl_galois_representations
assert modl_galois_representations
from . import hecke_algebras
assert hecke_algebras
from . import cluster_pictures
assert cluster_pictures
from . import groups
assert groups
from .groups import abstract
assert abstract
from .groups import glnQ
assert glnQ
from .groups import glnC
assert glnC
from . import maass_forms
assert maass_forms
from .homepage import random
assert random

from .lmfdb_database import db
if db.is_verifying:
    raise RuntimeError("Cannot start website while verifying (SQL injection vulnerabilities)")

def main():
    info("main: ...done.")
    from .utils.config import Configuration

    C = Configuration()
    flask_options = C.get_flask()
    flask_options['threaded'] = False
    cocalc_options = C.get_cocalc()

    if "profiler" in flask_options and flask_options["profiler"]:
        info("Profiling!")
        from werkzeug.middleware.profiler import ProfilerMiddleware

        app.wsgi_app = ProfilerMiddleware(
            app.wsgi_app, restrictions=[30], sort_by=("cumulative", "time", "calls")
        )
        del flask_options["profiler"]

    if cocalc_options:
        from .utils.cocalcwrap import CocalcWrap
        app.wsgi_app = CocalcWrap(app.wsgi_app)
        info(cocalc_options["message"])

    set_running()
    app.run(**flask_options)
