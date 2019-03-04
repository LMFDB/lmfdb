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
add --debug if you are developing (auto-restart, full stacktrace in browser, ...)
"""

from lmfdb.logger import info
import lmfdb.app # So that we can set it running below
from lmfdb.app import app

# Importing the following top-level modules adds blueprints
# to the app and imports further modules to make them functional
# Note that this necessarily includes everything, even code in still in an alpha state
#import logging # Needs to be done first so that other modules and gunicorn can use logging
#assert logging
#import backend
#assert backend
#import utils
#assert utils
import api
assert api
import belyi
assert belyi
import bianchi_modular_forms
assert bianchi_modular_forms
import hilbert_modular_forms
assert hilbert_modular_forms
import half_integral_weight_forms
assert half_integral_weight_forms
import siegel_modular_forms
assert siegel_modular_forms
import modular_forms
assert modular_forms
import elliptic_curves
assert elliptic_curves
import ecnf
assert ecnf
import number_fields
assert number_fields
import lfunctions
assert lfunctions
import genus2_curves
assert genus2_curves
import sato_tate_groups
assert sato_tate_groups
import users
assert users
import knowledge
assert knowledge
import characters
assert characters
import local_fields
assert local_fields
import galois_groups
assert galois_groups
import artin_representations
assert artin_representations
import tensor_products
assert tensor_products
import zeros
assert zeros
import crystals
assert crystals
import permutations
assert permutations
import hypergm
assert hypergm
import motives
assert motives
import riemann
assert riemann
import lattice
assert lattice
import higher_genus_w_automorphisms
assert higher_genus_w_automorphisms
import abvar
assert abvar
import abvar.fq
assert abvar.fq
import modlmf
assert modlmf
import rep_galois_modl
assert rep_galois_modl
import hecke_algebras
assert hecke_algebras
from inventory_app.inventory_app import inventory_app
assert inventory_app

from lmfdb.backend.database import db
if db.is_verifying:
    raise RuntimeError("Cannot start website while verifying (SQL injection vulnerabilities)")

def main():
    info("main: ...done.")
    from lmfdb.utils.config import Configuration
    flask_options = Configuration().get_flask();

    if "profiler" in flask_options and flask_options["profiler"]:
        print "Profiling!"
        from werkzeug.contrib.profiler import ProfilerMiddleware
        app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions = [30], sort_by=('cumulative','time','calls'))
        del flask_options["profiler"]

    lmfdb.app.set_running()
    app.run(**flask_options)




