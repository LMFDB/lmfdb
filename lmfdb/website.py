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
from .lmfdb_database import db
from .homepage import random
from . import modular_curves
from . import maass_forms
from .groups import glnC
from .groups import glnQ
from .groups import abstract
from . import groups
from . import cluster_pictures
from . import hecke_algebras
from . import modl_galois_representations
from . import modlmf
from .abvar import fq
from . import abvar
from . import higher_genus_w_automorphisms
from . import lattice
from . import riemann
from . import motives
from . import hypergm
from . import permutations
from . import crystals
from . import zeros
from . import tensor_products
from . import artin_representations
from . import galois_groups
from . import local_fields
from . import characters
from . import knowledge
from . import users
from . import sato_tate_groups
from . import genus2_curves
from . import lfunctions
from . import number_fields
from . import ecnf
from . import elliptic_curves
from . import siegel_modular_forms
from . import half_integral_weight_forms
from . import hilbert_modular_forms
from . import bianchi_modular_forms
from . import belyi
from .logger import info
from .app import app, set_running  # So that we can set it running below

# Importing the following top-level modules adds blueprints
# to the app and imports further modules to make them functional
# Note that this necessarily includes everything, even code in still in an
# alpha state
from . import api
assert api
#from . import api2
#assert api2
assert belyi
assert bianchi_modular_forms
assert hilbert_modular_forms
assert half_integral_weight_forms
assert siegel_modular_forms
# from . import modular_forms
# assert modular_forms
assert elliptic_curves
assert ecnf
assert number_fields
assert lfunctions
assert genus2_curves
assert sato_tate_groups
assert users
assert knowledge
assert characters
assert local_fields
assert galois_groups
assert artin_representations
assert tensor_products
assert zeros
assert crystals
assert permutations
assert hypergm
assert motives
assert riemann
assert lattice
assert higher_genus_w_automorphisms
assert abvar
assert fq
assert modlmf
assert modl_galois_representations
assert hecke_algebras
assert cluster_pictures
assert groups
assert abstract
assert glnQ
assert glnC
assert maass_forms
assert modular_curves
assert random

if db.is_verifying:
    raise RuntimeError(
        "Cannot start website while verifying (SQL injection vulnerabilities)")


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
