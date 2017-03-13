# -*- coding: utf-8 -*-

from flask import render_template, url_for
from lmfdb.modular_forms.maass_forms import maassf, MAASSF

@maassf.context_processor
def body_class():
    return {'body_class': MAASSF}

@maassf.route("/")
def maass_forms_main_page():
    info = dict()
    title = "Maass Forms"
    bread = [('Modular Forms', url_for('modular_form_toplevel'))]
    return render_template("maass_forms_navigation.html", info=info, title=title, bread=bread)
